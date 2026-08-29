"""Panelning telefondagi ko'rinishi.

Muammo: yon menyu telefonda bir ustunga tushib, o'nlab havolasi bilan
ekranning butun tepasini egallardi. Xodim «Buyurtmalar» ga bosganda
sahifa o'rniga yana o'sha menyuni ko'rar, kerakli kontent esa ancha
pastda qolib ketardi.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


def dashboard_css():
    for root in settings.STATICFILES_DIRS:
        path = Path(root) / 'css' / 'dashboard.css'
        if path.exists():
            return path.read_text(encoding='utf-8')
    raise AssertionError('dashboard.css topilmadi')


@NO_NETWORK
class CollapsibleMenuMarkupTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=user, role=Profile.ROLE_MANAGER)
        self.client.force_login(user)
        self.html = self.client.get(reverse('dashboard:overview')).content.decode()

    def test_menyu_tugmasi_bor(self):
        self.assertIn('data-dash-menu-toggle', self.html)

    def test_tugma_menyuga_boglangan(self):
        """Ekran o‘quvchi uchun: tugma qaysi bo‘limni ochishini bilsin."""
        self.assertIn('aria-controls="dash-nav"', self.html)
        self.assertIn('id="dash-nav"', self.html)

    def test_boshida_yopiq(self):
        self.assertIn('aria-expanded="false"', self.html)

    def test_yon_panel_belgilangan(self):
        self.assertIn('data-dash-side', self.html)

    def test_kontent_menyudan_keyin_keladi(self):
        """HTML tartibi muhim: `dash-main` `dash-side` dan keyin tursa,
        menyu yig‘ilganda kontent darhol ekranning tepasiga chiqadi."""
        self.assertLess(self.html.index('dash-side'), self.html.index('dash-main'))

    def test_menyu_havolalari_joyida(self):
        """Yig‘ish havolalarni yo‘qotmasligi kerak."""
        for name in ('dashboard:order_list', 'dashboard:lead_list', 'dashboard:agent'):
            with self.subTest(name=name):
                self.assertIn(reverse(name), self.html)


class CollapsibleMenuStyleTests(TestCase):
    """Uslublar telefonda menyuni yashirishi kerak."""

    def setUp(self):
        self.css = dashboard_css()

    def test_telefonda_menyu_yashiriladi(self):
        self.assertIn('.dash-nav, .dash-side-foot { display: none; }', self.css)

    def test_ochilganda_korinadi(self):
        self.assertIn('.dash-side.is-open .dash-nav', self.css)

    def test_tugma_kompyuterda_korinmaydi(self):
        """`.dash-burger` sukut bo‘yicha yashirin, faqat tor ekranda chiqadi."""
        block = self.css.split('.dash-burger {', 1)[1].split('}', 1)[0]
        self.assertIn('display: none', block)

    def test_yon_panel_tepada_yopishib_turadi(self):
        self.assertIn('position: sticky', self.css)

    def test_joriy_bolim_belgilanadi(self):
        self.assertIn('.dash-nav a.is-current', self.css)

    def test_bosish_maydoni_yetarli(self):
        """Telefon uchun 44px — eng kichik qulay o‘lcham."""
        self.assertIn('min-height: 44px', self.css)


@NO_NETWORK
class MenuScriptTests(TestCase):
    def setUp(self):
        user = User.objects.create_superuser('boss', 'b@example.com', 'Parol12345!')
        self.client.force_login(user)
        self.html = self.client.get(reverse('dashboard:overview')).content.decode()

    def test_tugma_holatni_almashtiradi(self):
        self.assertIn("classList.toggle('is-open')", self.html)

    def test_havolaga_bosilganda_yopiladi(self):
        """Aks holda yangi sahifada menyu yana ochiq turardi."""
        self.assertIn("classList.remove('is-open')", self.html)

    def test_joriy_bolim_belgilanadi(self):
        self.assertIn("is-current", self.html)
