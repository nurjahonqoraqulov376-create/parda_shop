"""Serverga joylashtirish sozlamalari testlari.

Bu yerdagi tekshiruvlar «serverda ishga tushmay qoladi» turidagi xatolarni
oldindan ushlaydi: kutubxona unutilgan, middleware noto'g'ri tartibda,
statik fayllar sozlanmagan va h.k.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)


def read(name):
    return (ROOT / name).read_text(encoding='utf-8')


class RequirementsTests(SimpleTestCase):
    def setUp(self):
        self.text = read('requirements.txt').lower()

    def test_ishlab_chiqarish_kutubxonalari_bor(self):
        for package in ('gunicorn', 'whitenoise', 'psycopg'):
            with self.subTest(package=package):
                self.assertIn(package, self.text)

    def test_django_versiyasi_qotirilgan(self):
        """Django o‘zi 6.0 ga sakrab, saytni buzib qo‘ymasin."""
        self.assertIn('django>=5.0,<6.0', self.text.replace(' ', ''))


class ProcfileTests(SimpleTestCase):
    def setUp(self):
        self.text = read('Procfile')

    def test_web_jarayoni_wsgi_ni_chaqiradi(self):
        self.assertIn('gunicorn parda_shop.wsgi', self.text)

    def test_port_muhitdan_olinadi(self):
        """Railway portni o‘zi beradi — qotirib yozilsa ilova ochilmaydi."""
        self.assertIn('$PORT', self.text)

    def test_release_qatori_yoq(self):
        """`release:` Nixpacks tomonidan QURISH bosqichiga qo‘shiladi.

        U yerda Railway'ning ichki tarmog‘i hali yo‘q, shuning uchun
        `postgres.railway.internal` topilmaydi va qurish
        «failed to resolve host» bilan to‘xtaydi. Migratsiyalar Railway'ning
        Pre-deploy Command sozlamasi orqali, ishlash paytida bajariladi.
        """
        for line in self.text.splitlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            self.assertFalse(
                line.startswith('release:'),
                'Procfile da `release:` bo‘lmasligi kerak — qurish paytida baza yo‘q',
            )


class StaticFilesTests(SimpleTestCase):
    def test_whitenoise_togri_tartibda(self):
        """WhiteNoise SecurityMiddleware'dan keyin turishi SHART."""
        middleware = list(settings.MIDDLEWARE)
        security = middleware.index('django.middleware.security.SecurityMiddleware')
        white = middleware.index('whitenoise.middleware.WhiteNoiseMiddleware')
        self.assertEqual(white, security + 1)

    def test_statik_saqlash_sozlangan(self):
        backend = settings.STORAGES['staticfiles']['BACKEND']
        self.assertIn('whitenoise', backend)

    def test_static_root_belgilangan(self):
        """`collectstatic` shu papkaga yig‘adi."""
        self.assertTrue(settings.STATIC_ROOT)


class LoggingTests(SimpleTestCase):
    def test_xatolar_konsolga_chiqadi(self):
        """DEBUG=False da Django xatolarni faqat emailga yuborardi — server
        loglarida hech narsa ko‘rinmasdi."""
        self.assertIn('console', settings.LOGGING['handlers'])
        self.assertIn('console', settings.LOGGING['root']['handlers'])
        request_logger = settings.LOGGING['loggers']['django.request']
        self.assertIn('console', request_logger['handlers'])


class SecretsTests(SimpleTestCase):
    def test_settings_da_qattiq_yozilgan_sir_yoq(self):
        text = read('parda_shop/settings.py')
        for name in ('SECRET_KEY', 'GEMINI_API_KEY', 'EMAIL_HOST_PASSWORD'):
            with self.subTest(name=name):
                # Har biri `env(...)` orqali olinishi kerak.
                self.assertRegex(text, r'%s\s*=\s*env' % name)

    def test_ishlab_chiqarishda_secret_key_majburiy(self):
        """DEBUG=False bo‘lsa zaxira qiymat ishlatilmasligi kerak."""
        text = read('parda_shop/settings.py')
        production_branch = text.split('else:', 1)[1].split('\n\n', 1)[0]
        self.assertIn("env('SECRET_KEY')", production_branch)
        self.assertNotIn('default=', production_branch)

    def test_env_example_da_haqiqiy_qiymat_yoq(self):
        for line in read('.env.example').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, _, value = line.partition('=')
            with self.subTest(name=name):
                self.assertNotIn('AIza', value)
                self.assertNotIn('AQ.', value)


class DatabaseTests(SimpleTestCase):
    def test_database_url_qollab_quvvatlanadi(self):
        """Railway `DATABASE_URL` beradi; SQLite u yerda yaramaydi."""
        text = read('parda_shop/settings.py')
        self.assertIn('DATABASE_URL', text)
        self.assertIn('env.db_url', text)
