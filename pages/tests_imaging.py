"""Rasmlarni avtomatik kichraytirish testlari."""

import io
import shutil
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from decimal import Decimal

from catalog.models import Category, Product
from pages.imaging import MAX_SIDE, shrink
from pages.models import Work


def jpeg_bytes(width, height, quality=95):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), (180, 150, 120)).save(buffer, format='JPEG', quality=quality)
    return buffer.getvalue()


def png_bytes(width, height):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), (100, 140, 160)).save(buffer, format='PNG')
    return buffer.getvalue()


class ShrinkTests(TestCase):
    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.settings_ctx = override_settings(MEDIA_ROOT=self.media, AUTO_TRANSLATE=False)
        self.settings_ctx.enable()
        self.addCleanup(self.settings_ctx.disable)

    def make_work(self, data, name='surat.jpg', slug='sinov'):
        work = Work(title='Sinov', slug=slug, category='Parda')
        work.image.save(name, ContentFile(data), save=False)
        work.save()
        return work

    # ------------------------------------------------------------------
    def test_katta_rasm_kichrayadi(self):
        """Telefon surati (2560px) saytga mos o'lchamga keladi."""
        work = self.make_work(jpeg_bytes(2560, 1920))
        self.assertEqual(max(work.image.width, work.image.height), MAX_SIDE)

    def test_nisbat_saqlanadi(self):
        work = self.make_work(jpeg_bytes(2400, 1800))
        self.assertAlmostEqual(work.image.width / work.image.height, 2400 / 1800, places=2)

    def test_hajm_kamayadi(self):
        data = jpeg_bytes(2560, 1920)
        work = self.make_work(data)
        self.assertLess(work.image.size, len(data))

    def test_kichik_jpeg_tegilmaydi(self):
        """Allaqachon mos rasm qayta siqilmasin — sifati yo‘qolmasin."""
        work = self.make_work(jpeg_bytes(800, 600), name='kichik.jpg')
        self.assertEqual(work.image.name, 'works/kichik.jpg')
        self.assertEqual((work.image.width, work.image.height), (800, 600))

    def test_png_jpegga_otadi(self):
        """PNG surat JPEG'ga o‘tsa hajm sezilarli kamayadi."""
        work = self.make_work(png_bytes(2000, 1500), name='surat.png')
        self.assertTrue(work.image.name.endswith('.jpg'), work.image.name)

    def test_fayl_nomi_barqaror(self):
        """Qayta saqlanganda `_a1b2c3` qo‘shilib nom o‘zgarib ketmasin."""
        work = self.make_work(jpeg_bytes(2560, 1920), name='barqaror.jpg')
        first = work.image.name
        for _ in range(3):
            work.save()
        self.assertEqual(work.image.name, first)
        self.assertEqual(len(list((self.media / 'works').glob('*'))), 1)

    def test_eski_fayl_qoldirilmaydi(self):
        self.make_work(jpeg_bytes(2560, 1920))
        files = list((self.media / 'works').glob('*'))
        self.assertEqual(len(files), 1, [f.name for f in files])

    def test_rasmsiz_yozuv_yiqilmaydi(self):
        work = Work(title='Rasmsiz', slug='rasmsiz', category='Parda')
        self.assertFalse(shrink(work))

    def test_buzuq_rasm_saqlashni_toxtatmaydi(self):
        """Fayl rasm bo‘lmasa ham yozuv saqlanishi kerak."""
        work = Work(title='Buzuq', slug='buzuq', category='Parda')
        work.image.save('buzuq.jpg', ContentFile(b'bu rasm emas'), save=False)
        work.save()
        self.assertTrue(Work.objects.filter(slug='buzuq').exists())

    def test_update_fields_bilan_rasm_tegilmaydi(self):
        """`save(update_fields=['sort_order'])` da rasm qayta yozilmasin."""
        work = self.make_work(jpeg_bytes(2560, 1920))
        name = work.image.name
        work.sort_order = 5
        work.save(update_fields=['sort_order'])
        work.refresh_from_db()
        self.assertEqual(work.image.name, name)


class MissingImageTests(TestCase):
    """Rasm fayli diskda yo'q bo'lsa sahifa yiqilmasligi kerak."""

    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        ctx = override_settings(MEDIA_ROOT=self.media, AUTO_TRANSLATE=False)
        ctx.enable()
        self.addCleanup(ctx.disable)

    def test_yoq_fayl_bilan_sahifalar_ochiladi(self):
        """`.width` faylni diskdan ochadi — fayl yo'q bo'lsa 500 berardi."""
        Work.objects.create(
            title='Fayli yo‘q', slug='fayli-yoq', category='Parda',
            excerpt='q', description='t', image='works/yoq.jpg',
        )
        for url in ('/uz/ishlarimiz/', '/uz/ishlarimiz/fayli-yoq/', '/uz/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_img_size_yoq_faylda_bosh_qaytaradi(self):
        from pages.templatetags.site_extras import img_size
        work = Work(title='x', slug='x', image='works/yoq.jpg')
        self.assertEqual(img_size(work.image), '')

    def test_img_size_bor_faylda_olchamni_beradi(self):
        from pages.templatetags.site_extras import img_size
        work = Work(title='y', slug='y', category='Parda')
        work.image.save('bor.jpg', ContentFile(jpeg_bytes(800, 600)), save=False)
        work.save()
        self.assertEqual(img_size(work.image), 'width="800" height="600"')


class SmallImageUploadTests(TestCase):
    """1600px dan KICHIK rasm yuklash — panelning eng oddiy amali.

    Ishlab chiqarishda topilgan xato: `shrink()` rasmni kichraytirish
    shart emas deb qaror qilganda faylni YOPIB qo'yardi, Django esa
    keyin o'sha yopiq fayldan o'qib diskka yozmoqchi bo'lardi:

        ValueError: I/O operation on closed file

    Natijada paneldan tayyor (kichraytirilgan) rasm bilan mahsulot yoki
    portfolio ishi qo'shib bo'lmasdi — 500 xatosi chiqardi.
    """

    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, True)
        self.override = override_settings(MEDIA_ROOT=str(self.media), AUTO_TRANSLATE=False)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.category = Category.objects.create(name='Zebra', slug='zebra')

    def upload(self, size=(40, 30), fmt='JPEG', name='kichik.jpg'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', size, (200, 180, 160)).save(buffer, fmt)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/%s' % fmt.lower())

    def make_product(self, upload):
        product = Product(
            category=self.category, name='Kichik rasm', slug='kichik',
            short_description='q', description='t', price=Decimal('1'), stock=1)
        product.image = upload
        product.save()
        return product

    def test_kichik_jpeg_saqlanadi(self):
        """Aynan yiqilgan holat."""
        product = self.make_product(self.upload())
        self.assertTrue(product.image.name)
        self.assertTrue((self.media / product.image.name).exists())

    def test_fayl_bosh_qolmaydi(self):
        product = self.make_product(self.upload())
        self.assertGreater((self.media / product.image.name).stat().st_size, 0)

    def test_kichik_rasm_qayta_siqilmaydi(self):
        """Tayyor JPEG sifatini yo‘qotmasligi kerak."""
        upload = self.upload()
        original = len(upload.read())
        upload.seek(0)
        product = self.make_product(upload)
        saved = (self.media / product.image.name).stat().st_size
        self.assertEqual(saved, original)

    def test_katta_rasm_kichrayadi(self):
        from PIL import Image
        product = self.make_product(self.upload(size=(2400, 1800)))
        with Image.open(self.media / product.image.name) as picture:
            self.assertLessEqual(max(picture.size), 1600)

    def test_png_jpegga_aylanadi(self):
        product = self.make_product(self.upload(fmt='PNG', name='kichik.png'))
        self.assertTrue(product.image.name.endswith('.jpg'))
        self.assertTrue((self.media / product.image.name).exists())

    def test_buzuq_fayl_saqlashni_toxtatmaydi(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        broken = SimpleUploadedFile('buzuq.jpg', b'bu rasm emas', content_type='image/jpeg')
        product = self.make_product(broken)
        self.assertTrue((self.media / product.image.name).exists())

    def test_ish_uchun_ham_ishlaydi(self):
        work = Work(title='Kichik', slug='kichik-ish', category='Baxmal',
                    excerpt='e', description='d')
        work.image = self.upload()
        work.save()
        self.assertTrue((self.media / work.image.name).exists())
