"""Rasmlarni avtomatik kichraytirish testlari."""

import io
import shutil
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

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
