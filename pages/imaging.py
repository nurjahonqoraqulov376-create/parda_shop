"""Yuklangan rasmlarni saytga mos o'lchamga keltirish.

Telefon surati odatda 2500px+ va 0.5–2 MB bo'ladi. Uni o'zgarishsiz berish
mobil internetda sekin: rasm yuklanmay qolishi va brauzer «buzuq rasm»
belgisini ko'rsatishi mumkin. Shuning uchun saqlashda rasm bir marta
kichraytiriladi.
"""

import io
import logging

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Saytda rasm hech qachon bundan kattaroq ko'rsatilmaydi (retina ekran ham
# hisobga olingan).
MAX_SIDE = 1600
QUALITY = 82


def _rewind(field):
    """Faylni saqlashga tayyor holatga qaytaradi.

    `Image.open()` faylni o'qib qo'yadi va biz uni yopamiz. Agar rasmni
    almashtirmasak (allaqachon kichik yoki buzuq bo'lsa), Django o'sha
    faylni diskka yozmoqchi bo'ladi va yopiq fayldan o'qib
    `ValueError: I/O operation on closed file` beradi — natijada
    paneldan mahsulot yoki portfolio ishi QO'SHIB BO'LMAYDI.

    Aynan shu sabab 1600px dan kichik har qanday JPEG yuklashda
    500 xatosi chiqardi.
    """
    # Diskdagi (allaqachon saqlangan) faylni Django qayta yozmaydi, ochiq
    # qoldirish esa Windows'da uni band qilib qo'yadi — keyin o'chirib
    # bo'lmaydi. Shuning uchun faqat YANGI yuklangan faylni tiklaymiz.
    if getattr(field, '_committed', True):
        try:
            field.close()
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        if getattr(field, 'closed', False):
            field.open()
        else:
            field.seek(0)
    except Exception:  # noqa: BLE001 — tiklab bo'lmasa saqlash o'zi xato beradi
        pass


def shrink(instance, field_name='image', max_side=MAX_SIDE, quality=QUALITY):
    """Maydondagi rasmni kichraytirib, JPEG sifatida qayta yozadi.

    Fayl diskka yoziladi, lekin model saqlanmaydi — chaqiruvchi `save()`
    qiladi. Rasm allaqachon kichik bo'lsa yoki xatolik chiqsa `False`
    qaytadi va maydon tegilmaydi.
    """
    field = getattr(instance, field_name, None)
    if not field:
        return False

    try:
        from PIL import Image, ImageOps
    except ImportError:  # Pillow yo'q — rasm o'zgarishsiz qoladi
        return False

    buffer = None
    try:
        field.open()
        picture = Image.open(field)
        # `format` ni transpose'DAN OLDIN olamiz: `exif_transpose()` yangi
        # obyekt qaytaradi va uning `format` i `None` bo'ladi. Keyin o'qilsa
        # allaqachon JPEG bo'lgan rasm ham qayta siqilib, sifati yo'qoladi.
        source_format = (picture.format or '').upper()
        already_small = max(picture.size) <= max_side
        if not (already_small and source_format in ('JPEG', 'JPG')):
            # Telefon suratlari EXIF'da burilish bilan saqlanadi;
            # kichraytirishdan oldin uni qo'llamasak, rasm yonboshlab qoladi.
            picture = ImageOps.exif_transpose(picture)

            picture.thumbnail((max_side, max_side), Image.LANCZOS)
            if picture.mode not in ('RGB', 'L'):
                picture = picture.convert('RGB')

            buffer = io.BytesIO()
            picture.save(buffer, format='JPEG', quality=quality,
                         optimize=True, progressive=True)
    except Exception as exc:  # noqa: BLE001 — buzuq rasm saqlashni to'xtatmasin
        logger.warning('Rasmni kichraytirib bo‘lmadi (%s): %s', getattr(field, 'name', '?'), exc)
        buffer = None

    if buffer is None:
        # Rasmga tegmadik — faylni Django yoza oladigan holatga qaytaramiz.
        _rewind(field)
        return False

    try:
        field.close()
    except Exception:  # noqa: BLE001
        pass

    name = field.name.rsplit('/', 1)[-1]
    stem = name.rsplit('.', 1)[0]
    new_name = '%s.jpg' % stem

    # Eski faylni saqlashdan OLDIN o'chiramiz: aks holda Django nom band
    # deb hisoblab `_a1b2c3` qo'shadi va fayl nomi har safar o'zgarib ketadi.
    # Baytlar allaqachon `buffer` da, shuning uchun ma'lumot yo'qolmaydi.
    storage, old_name = field.storage, field.name
    for stale in {old_name, field.field.upload_to + new_name}:
        if stale and storage.exists(stale):
            try:
                storage.delete(stale)
            except Exception:  # noqa: BLE001
                pass
    field.save(new_name, ContentFile(buffer.getvalue()), save=False)
    return True


class ShrinkImageOnSaveMixin:
    """Saqlashda `shrink_fields` dagi rasmlarni avtomatik kichraytiradi.

    Panel orqali yuklangan telefon surati ham, buyruq orqali qo'shilgani ham
    bir xil o'lchamga keladi — alohida qadam eslab qolish shart emas.
    """

    shrink_fields = ('image',)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        for field_name in self.shrink_fields:
            # `update_fields` berilgan bo'lsa va rasm unda yo'q bo'lsa,
            # tegmaymiz — aks holda o'zgarish saqlanmay yo'qoladi.
            if update_fields is not None and field_name not in update_fields:
                continue
            shrink(self, field_name)
        super().save(*args, **kwargs)
