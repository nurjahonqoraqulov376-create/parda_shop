"""`import_works` buyrug'i testlari."""

import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from pages.management.commands.import_works import WORKS
from pages.models import Work


def make_image(path):
    """Kichik haqiqiy JPEG yaratadi (Pillow loyihada allaqachon bor)."""
    from PIL import Image
    Image.new('RGB', (60, 40), (200, 180, 160)).save(path)


class ImportWorksTests(TestCase):
    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.source, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        for item in WORKS:
            make_image(self.source / ('%s.jpg' % item['file']))

    def run_import(self, **kwargs):
        with override_settings(MEDIA_ROOT=self.media, AUTO_TRANSLATE=False):
            call_command('import_works', dir=str(self.source), **kwargs)

    # ------------------------------------------------------------------
    def test_barcha_ishlar_yaratiladi(self):
        self.run_import()
        self.assertEqual(Work.objects.count(), len(WORKS))

    def test_maydonlar_toldiriladi(self):
        """Bo'sh sarlavha yoki tavsif bilan yozuv qolmasin."""
        self.run_import()
        for work in Work.objects.all():
            with self.subTest(work=work.slug):
                self.assertTrue(work.title.strip())
                self.assertTrue(work.category.strip())
                self.assertTrue(work.excerpt.strip())
                self.assertTrue(work.description.strip())
                self.assertTrue(work.image.name)
                self.assertTrue(work.is_active)

    def test_qayta_ishga_tushirsa_takrorlanmaydi(self):
        self.run_import()
        self.run_import()
        self.assertEqual(Work.objects.count(), len(WORKS))

    def test_qayta_ishga_tushirsa_rasm_nusxalanmaydi(self):
        """Django bir xil nomda `_a1b2c3` qo‘shib nusxa yaratardi."""
        for _ in range(3):
            self.run_import()
        files = list((self.media / 'works').glob('*'))
        self.assertEqual(len(files), len(WORKS), [f.name for f in files])

    def test_slug_va_tartib_noyob(self):
        slugs = [item['slug'] for item in WORKS]
        self.assertEqual(len(slugs), len(set(slugs)), 'slug takrorlangan')
        orders = [item['sort_order'] for item in WORKS]
        self.assertEqual(len(orders), len(set(orders)), 'tartib raqami takrorlangan')

    def test_rasm_yoq_bolsa_otkazib_yuboradi(self):
        (self.source / ('%s.jpg' % WORKS[0]['file'])).unlink()
        self.run_import()
        self.assertEqual(Work.objects.count(), len(WORKS) - 1)
        self.assertFalse(Work.objects.filter(slug=WORKS[0]['slug']).exists())

    def test_dry_run_hech_narsa_saqlamaydi(self):
        self.run_import(dry_run=True)
        self.assertEqual(Work.objects.count(), 0)

    def test_yoq_papka_tushunarli_xato_beradi(self):
        with self.assertRaises(CommandError):
            call_command('import_works', dir=str(self.source / 'bunday-papka-yoq'))

    def test_saytda_korinadi(self):
        self.run_import()
        with override_settings(MEDIA_ROOT=self.media):
            response = self.client.get('/uz/ishlarimiz/')
            self.assertEqual(response.status_code, 200)
            html = response.content.decode('utf-8')
            for item in WORKS:
                with self.subTest(work=item['slug']):
                    self.assertIn(item['title'], html)
                    detail = self.client.get('/uz/ishlarimiz/%s/' % item['slug'])
                    self.assertEqual(detail.status_code, 200)
