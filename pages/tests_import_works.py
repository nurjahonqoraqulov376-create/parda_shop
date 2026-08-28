"""`import_works` buyrug'i testlari."""

import shutil
import tempfile
from io import StringIO
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


class InOrderModeTests(TestCase):
    """`--in-order`: fayl nomlari muhim emas, tartib muhim."""

    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.source, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        # Telefondan kelganidek begona nomlar.
        self.names = ['IMG_%04d.jpg' % (2001 + i) for i in range(len(WORKS))]
        for name in self.names:
            make_image(self.source / name)

    def run_import(self, **kwargs):
        with override_settings(MEDIA_ROOT=self.media, AUTO_TRANSLATE=False):
            call_command('import_works', dir=str(self.source), in_order=True, **kwargs)

    def test_begona_nomlar_bilan_ishlaydi(self):
        self.run_import()
        self.assertEqual(Work.objects.count(), len(WORKS))

    def test_tartib_nomi_boyicha_saralanadi(self):
        self.run_import()
        for index, item in enumerate(WORKS):
            with self.subTest(work=item['slug']):
                work = Work.objects.get(slug=item['slug'])
                self.assertIn(self.names[index].rsplit('.', 1)[0], work.image.name)

    def test_rasm_kam_bolsa_qolgani_otkazib_yuboriladi(self):
        for name in self.names[3:]:
            (self.source / name).unlink()
        self.run_import()
        self.assertEqual(Work.objects.count(), 3)

    def test_bosh_papka_tushunarli_xato(self):
        for name in self.names:
            (self.source / name).unlink()
        with self.assertRaises(CommandError):
            self.run_import()

    def test_qayta_ishga_tushirsa_nusxalanmaydi(self):
        for _ in range(3):
            self.run_import()
        files = list((self.media / 'works').glob('*'))
        self.assertEqual(len(files), len(WORKS), [f.name for f in files])


class SeedFolderTests(TestCase):
    """`seed/works/` — portfolio rasmlarining doimiy manbasi.

    Serverdagi `media/` diski tozalanishi mumkin (Railway'da u alohida
    ulanadigan disk). Rasmlar kod bilan birga kelsa, `import_works` ni
    ishga tushirish kifoya — portfolio qaytadan tiklanadi. Shu sababli
    bu papkaning to‘liqligini test qo‘riqlaydi.
    """

    def setUp(self):
        from pages.management.commands.import_works import DEFAULT_DIR
        self.folder = DEFAULT_DIR

    def test_papka_mavjud(self):
        self.assertTrue(self.folder.is_dir(), 'seed/works/ papkasi yo‘q: %s' % self.folder)

    def test_har_bir_ish_uchun_rasm_bor(self):
        """Yangi ish qo‘shilib, rasmi commit qilinmasa shu test ushlaydi."""
        from pages.management.commands.import_works import Command
        command = Command()
        for item in WORKS:
            with self.subTest(work=item['slug']):
                self.assertIsNotNone(
                    command.find_image(self.folder, item['file']),
                    'rasm topilmadi: %s' % item['file'],
                )

    def test_dir_korsatilmasa_seed_ishlatiladi(self):
        out = StringIO()
        call_command('import_works', '--dry-run', stdout=out, stderr=StringIO())
        self.assertIn('Rasmi topilmadi: 0', out.getvalue())


class StemVariantsTests(TestCase):
    """Brauzer «photo (2).jpg» deydi, Django «photo_2.jpg» deb saqlaydi."""

    def variants(self, stem):
        from pages.management.commands.import_works import Command
        return Command().stem_variants(stem)

    def test_qavsli_raqam_pastki_chiziqqa_aylanadi(self):
        self.assertEqual(self.variants('photo (2)'), ['photo (2)', 'photo_2'])

    def test_probelsiz_qavs_ham_tanildi(self):
        self.assertIn('rasm_3', self.variants('rasm(3)'))

    def test_oddiy_nom_ozgarmaydi(self):
        self.assertEqual(self.variants('photo_2026-08-14'), ['photo_2026-08-14'])

    def test_ortasidagi_qavsga_tegilmaydi(self):
        """Faqat nom oxiridagi «(N)» almashtiriladi."""
        self.assertEqual(self.variants('a (2) b'), ['a (2) b'])
