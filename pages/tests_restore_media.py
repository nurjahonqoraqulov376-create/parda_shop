"""`restore_media` buyrug'i testlari.

Bu bo'lim aniq bir ishlab chiqarish nosozligidan keyin yozildi: Railway'da
pre-deploy buyruqlari **disk ulanmagan** konteynerda ishlaydi. `import_works`
o'sha yerda bajarilgach bazada 8 ta ish paydo bo'ldi, saytdagi barcha
`/media/...` manzillari esa 404 qaytardi — fayllar vaqtinchalik konteyner
bilan birga o'chib ketgandi.
"""

import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from catalog.models import Category
from pages.management.commands.import_works import WORKS
from pages.management.commands.restore_media import SEED_DIR, WORK_FILES, find_seed_file
from pages.models import Work


class SeedNusxalariTests(TestCase):
    """Har bir yozuv uchun `seed/` da nusxa turishi kerak."""

    def test_har_bir_ish_uchun_nusxa_bor(self):
        for item in WORKS:
            with self.subTest(slug=item['slug']):
                self.assertIsNotNone(find_seed_file('works', WORK_FILES[item['slug']]))

    def test_har_bir_kategoriya_uchun_nusxa_bor(self):
        from catalog.management.commands.seed_demo import CATEGORIES
        for slug in (item[0] for item in CATEGORIES):
            with self.subTest(slug=slug):
                self.assertIsNotNone(find_seed_file('categories', slug))

    def test_notogri_nomga_none_qaytadi(self):
        self.assertIsNone(find_seed_file('works', 'bunday-fayl-yoq'))

    def test_seed_papkasi_joyida(self):
        self.assertTrue((SEED_DIR / 'works').is_dir())
        self.assertTrue((SEED_DIR / 'categories').is_dir())


@override_settings(AUTO_TRANSLATE=False)
class RestoreMediaTests(TestCase):
    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, True)
        self.override = override_settings(MEDIA_ROOT=str(self.media))
        self.override.enable()
        self.addCleanup(self.override.disable)

        item = WORKS[0]
        self.work = Work.objects.create(
            title=item['title'], slug=item['slug'], category=item['category'],
            excerpt=item['excerpt'], description=item['description'],
            image='works/%s.jpg' % item['file'],
        )
        self.target = self.media / self.work.image.name

    def run_cmd(self, *args):
        out = StringIO()
        call_command('restore_media', *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_yoq_fayl_tiklanadi(self):
        self.assertFalse(self.target.exists())
        self.run_cmd()
        self.assertTrue(self.target.exists(), 'fayl tiklanmadi')
        self.assertGreater(self.target.stat().st_size, 0)

    def test_mavjud_fayl_ustidan_yozilmaydi(self):
        """Paneldan yuklangan yangi rasm eski nusxa bilan almashmasligi kerak."""
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_bytes(b'qolda-yuklangan')
        self.run_cmd()
        self.assertEqual(self.target.read_bytes(), b'qolda-yuklangan')

    def test_dry_run_hech_narsa_yozmaydi(self):
        self.run_cmd('--dry-run')
        self.assertFalse(self.target.exists())

    def test_rasmsiz_yozuv_otkazib_yuboriladi(self):
        Work.objects.create(title='Rasmsiz', slug='rasmsiz', category='x',
                            excerpt='e', description='d')
        self.run_cmd()  # xato bermasligi kerak

    def test_notanish_slug_yiqitmaydi(self):
        """`seed/` da nusxasi yo‘q yozuv buyruqni to‘xtatmasligi kerak."""
        Work.objects.create(title='Yangi', slug='paneldan-qoshilgan', category='x',
                            excerpt='e', description='d', image='works/yoq.jpg')
        out = self.run_cmd()
        self.assertIn('nusxa topilmadi', out)
        self.assertTrue(self.target.exists(), 'boshqa fayllar baribir tiklanishi kerak')

    def test_kategoriya_rasmi_ham_tiklanadi(self):
        category = Category.objects.create(
            name='Plisse jalyuzi', slug='plisse-jalyuzi',
            image='categories/plisse-jalyuzi.jpg')
        self.run_cmd()
        self.assertTrue((self.media / category.image.name).exists())

    def test_hammasi_joyida_bolsa_jim(self):
        self.run_cmd()
        self.assertIn('joyida', self.run_cmd())
