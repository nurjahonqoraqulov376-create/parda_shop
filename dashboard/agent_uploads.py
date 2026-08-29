"""Yordamchiga yuborilgan rasmni vaqtincha saqlaydi.

Nima uchun kerak
----------------
Yordamchi yozuvni darhol yozmaydi: avval TAKLIF qiladi, xodim
tasdiqlaydi. Ikkala qadam orasida rasm biror joyda turishi kerak —
sessiyaga fayl sig'maydi.

Shuning uchun rasm `media/agent_tmp/` ga qo'yiladi, sessiyada esa faqat
uning nomi saqlanadi. Tasdiqlangach fayl yozuvga biriktiriladi va
vaqtinchalik nusxa o'chiriladi.

Tashlab ketilgan fayllar (xodim taklifni tasdiqlamay chiqib ketsa) bir
kundan keyin o'zi tozalanadi.
"""

import logging
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger(__name__)

FOLDER = 'agent_tmp'
MAX_BYTES = 8 * 1024 * 1024          # 8 MB — telefon surati bemalol sig'adi
MAX_AGE = timedelta(days=1)
ALLOWED_FORMATS = ('JPEG', 'PNG', 'WEBP')


class UploadError(Exception):
    """Rasmni qabul qilib bo'lmadi (turi yoki hajmi yaramaydi)."""


def read_image(uploaded):
    """Yuklangan faylni tekshirib, baytlarini qaytaradi.

    Fayl turini sarlavhaga ishonib emas, ochib ko'rib aniqlaymiz:
    `Content-Type` ni yuboruvchi o'zi yozadi, ya'ni unga ishonib bo'lmaydi.
    """
    if uploaded.size > MAX_BYTES:
        raise UploadError('Rasm juda katta (%d MB dan oshmasin).' % (MAX_BYTES // 1024 // 1024))

    data = uploaded.read()
    try:
        from PIL import Image
        with Image.open(ContentFile(data)) as picture:
            picture.verify()
            image_format = (picture.format or '').upper()
    except Exception:
        raise UploadError('Bu fayl rasm emas yoki buzilgan.')

    if image_format not in ALLOWED_FORMATS:
        raise UploadError('Faqat JPG, PNG yoki WEBP rasm yuborish mumkin.')
    return data, image_format


def stash(uploaded):
    """Rasmni vaqtinchalik joyga qo'yadi va `(nom, baytlar)` qaytaradi."""
    data, image_format = read_image(uploaded)
    purge_old()

    suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[image_format]
    name = '%s/%s%s' % (FOLDER, uuid.uuid4().hex, suffix)
    default_storage.save(name, ContentFile(data))
    return name, data


def load(name):
    """Saqlangan rasmni ochadi; topilmasa `None`."""
    if not name or not str(name).startswith(FOLDER + '/'):
        return None
    try:
        if not default_storage.exists(name):
            return None
        return default_storage.open(name, 'rb')
    except Exception:  # noqa: BLE001 - fayl yo'q bo'lsa taklif rasmsiz bajariladi
        logger.warning('Yordamchi rasmini ochib bo‘lmadi: %s', name)
        return None


def discard(name):
    """Vaqtinchalik nusxani o'chiradi (tasdiqlangach yoki bekor qilinganda)."""
    if not name or not str(name).startswith(FOLDER + '/'):
        return
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:  # noqa: BLE001
        logger.warning('Yordamchi rasmini o‘chirib bo‘lmadi: %s', name)


def purge_old():
    """Tashlab ketilgan eski fayllarni tozalaydi.

    Yangi rasm yuklanganda chaqiriladi — alohida vazifa qo'shish shart emas.
    """
    folder = Path(settings.MEDIA_ROOT) / FOLDER
    if not folder.is_dir():
        return
    deadline = timezone.now() - MAX_AGE
    for path in folder.iterdir():
        try:
            if not path.is_file():
                continue
            changed = timezone.datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.get_current_timezone())
            if changed < deadline:
                path.unlink()
        except Exception:  # noqa: BLE001 - tozalash asosiy ishni to'xtatmasin
            continue


def public_url(name):
    """Vaqtinchalik rasmning ko'rish manzili; fayl yo'q bo'lsa `''`."""
    if not name or not str(name).startswith(FOLDER + '/'):
        return ''
    try:
        if not default_storage.exists(name):
            return ''
        return default_storage.url(name)
    except Exception:  # noqa: BLE001
        return ''
