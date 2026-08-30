"""Ko'rinish: bo'sh sahifalar va uslublar butunligi.

Katalog bo'sh bo'lganda sahifada yolg'iz kulrang qator turardi
(«Mahsulot topilmadi») — sayt buzilgandek ko'rinardi va mijozga nima
qilishni aytmasdi. Endi tushunarli blok va qo'ng'iroq tugmasi bor.
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from catalog.models import Category, Product
from pages.models import SiteSettings, Work

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)
LANGS = ('uz', 'ru')


def css(name):
    for root in settings.STATICFILES_DIRS:
        path = Path(root) / 'css' / name
        if path.exists():
            return path.read_text(encoding='utf-8')
    raise AssertionError('%s topilmadi' % name)


@NO_NETWORK
class EmptyCatalogTests(TestCase):
    """Katalog bo'sh bo'lsa mijoz nima qilishini bilsin."""

    def setUp(self):
        settings_obj = SiteSettings.load()
        settings_obj.phone_primary = '+998 99 986 71 99'
        settings_obj.save()

    def test_katalogda_tushunarli_blok(self):
        html = self.client.get('/uz/katalog/').content.decode()
        self.assertIn('empty-state', html)
        self.assertIn('Katalog to‘ldirilmoqda', html)

    def test_qongiroq_tugmasi_bor(self):
        html = self.client.get('/uz/katalog/').content.decode()
        self.assertIn('data-modal-open="callback"', html)

    def test_telefon_raqami_korinadi(self):
        html = self.client.get('/uz/katalog/').content.decode()
        self.assertIn('tel:+998 99 986 71 99', html)

    def test_ruscha_ham_ishlaydi(self):
        html = self.client.get('/ru/katalog/').content.decode()
        self.assertIn('empty-state', html)
        self.assertIn('Каталог наполняется', html)

    def test_qidiruvda_boshqa_matn(self):
        """Qidiruv natijasiz bo‘lsa — boshqacha maslahat kerak."""
        html = self.client.get('/uz/qidiruv/?q=bunday-narsa-yoq').content.decode()
        self.assertIn('empty-state', html)
        self.assertIn('topilmadi', html.lower())

    def test_portfolio_boshligi(self):
        html = self.client.get('/uz/ishlarimiz/').content.decode()
        self.assertIn('empty-state', html)

    def test_kategoriya_sahifasida_ham(self):
        Category.objects.create(name='Zebra', slug='zebra')
        html = self.client.get('/uz/katalog/zebra/').content.decode()
        self.assertIn('empty-state', html)

    def test_mahsulot_bolsa_blok_chiqmaydi(self):
        category = Category.objects.create(name='Zebra', slug='zebra')
        Product.objects.create(
            category=category, name='Zebra parda', slug='zebra-parda',
            short_description='q', description='t', price=Decimal('100000'), stock=3)
        html = self.client.get('/uz/katalog/').content.decode()
        self.assertNotIn('empty-state', html)
        self.assertIn('Zebra parda', html)

    def test_ish_bolsa_blok_chiqmaydi(self):
        Work.objects.create(title='Mehmonxona', slug='mehmonxona',
                            category='Baxmal', excerpt='e', description='d')
        html = self.client.get('/uz/ishlarimiz/').content.decode()
        self.assertNotIn('empty-state', html)

    def test_telefonsiz_ham_yiqilmaydi(self):
        """Sozlamalarda telefon bo‘lmasa sahifa baribir ochilsin."""
        settings_obj = SiteSettings.load()
        settings_obj.phone_primary = ''
        settings_obj.save()
        self.assertEqual(self.client.get('/uz/katalog/').status_code, 200)


class StyleIntegrityTests(TestCase):
    """Uslub fayllari kutilgan qoidalarni saqlab qolsin."""

    def test_bosh_holat_uslubi_bor(self):
        self.assertIn('.empty-state', css('style.css'))

    def test_fokus_halqasi_bor(self):
        """Klaviatura bilan yurganlar uchun — hamda qulaylik talabi."""
        for name in ('style.css', 'dashboard.css'):
            with self.subTest(css=name):
                self.assertIn(':focus-visible', css(name))

    def test_harakatni_kamaytirish_hurmat_qilinadi(self):
        """Animatsiya bosh og‘rig‘i keltiradiganlar uchun tizim sozlamasi."""
        for name in ('style.css', 'dashboard.css'):
            with self.subTest(css=name):
                self.assertIn('prefers-reduced-motion', css(name))

    def test_panelda_tungi_rejim_bor(self):
        """Ommaviy saytda tungi rejim bor edi, panelda — yo‘q."""
        self.assertIn('[data-theme="dark"]', css('dashboard.css'))

    def test_panel_mobil_qoidalari_saqlanib_qolgan(self):
        """Yangi uslublar eski mobil yechimni bosib ketmasin."""
        text = css('dashboard.css')
        self.assertIn('.dash-nav, .dash-side-foot { display: none; }', text)
        self.assertIn('min-height: 44px', text)

    def test_joriy_bolim_belgisi_saqlanib_qolgan(self):
        self.assertIn('.dash-nav a.is-current', css('dashboard.css'))


@NO_NETWORK
class PagesStillRenderTests(TestCase):
    """Uslub o'zgarishi hech bir sahifani buzmasligi kerak."""

    def test_ommaviy_sahifalar(self):
        paths = ['/uz/', '/ru/', '/uz/katalog/', '/uz/ishlarimiz/',
                 '/uz/aloqa/', '/uz/biz-haqimizda/', '/uz/savat/']
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_panel_sahifalari(self):
        user = User.objects.create_superuser('boss', 'b@example.com', 'Parol12345!')
        self.client.force_login(user)
        paths = ['/uz/boshqaruv/', '/uz/boshqaruv/mahsulotlar/',
                 '/uz/boshqaruv/mahsulotlar/yangi/', '/uz/boshqaruv/profil/',
                 '/uz/boshqaruv/yordamchi/']
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
