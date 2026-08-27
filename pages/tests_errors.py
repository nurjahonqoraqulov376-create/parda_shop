"""Xato sahifalari (403 / 404 / 500) va shablon sog'lig'i testlari."""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()
TEMPLATES_DIR = Path(settings.BASE_DIR) / 'templates'


@override_settings(AUTO_TRANSLATE=False)
class ForbiddenPageTests(TestCase):
    """403 yalang'och oq sahifa bo'lmasin — sabab va orqaga yo'l ko'rsatilsin."""

    def setUp(self):
        self.support = User.objects.create_user('support_test', password='Parol12345!')
        Profile.objects.create(user=self.support, role=Profile.ROLE_SUPPORT)

    def test_403_maxsus_sahifa_bilan_qaytadi(self):
        self.client.force_login(self.support)
        response = self.client.get(reverse('dashboard:user_list'))
        self.assertEqual(response.status_code, 403)
        html = response.content.decode('utf-8')
        # Django'ning standart javobi shunchaki "<h1>403 Forbidden</h1>" bo'lardi.
        self.assertNotEqual(html.strip(), '<h1>403 Forbidden</h1>')
        self.assertIn('403', html)

    def test_403_sababni_tushuntiradi(self):
        self.client.force_login(self.support)
        html = self.client.get(reverse('dashboard:user_list')).content.decode('utf-8')
        self.assertIn('ruxsat yo‘q', html)

    def test_403_kim_kirganini_korsatadi(self):
        """Foydalanuvchi qaysi hisob bilan kirganini bilsin — asosiy chalkashlik shu."""
        self.client.force_login(self.support)
        html = self.client.get(reverse('dashboard:user_list')).content.decode('utf-8')
        self.assertIn('support_test', html)

    def test_403_orqaga_qaytish_yoli_bor(self):
        self.client.force_login(self.support)
        html = self.client.get(reverse('dashboard:user_list')).content.decode('utf-8')
        # Support uchun — suhbatlar, va har doim bosh sahifa.
        self.assertIn(reverse('dashboard:chat_list'), html)
        self.assertIn(reverse('pages:home'), html)

    def test_403_hisobni_almashtirish_tugmasi(self):
        self.client.force_login(self.support)
        html = self.client.get(reverse('dashboard:user_list')).content.decode('utf-8')
        self.assertIn(reverse('dashboard:logout'), html)

    def test_menejerga_panel_havolasi_korsatiladi(self):
        manager = User.objects.create_user('menejer_403', password='Parol12345!')
        Profile.objects.create(user=manager, role=Profile.ROLE_MANAGER)
        self.client.force_login(manager)
        html = self.client.get(reverse('dashboard:user_list')).content.decode('utf-8')
        self.assertIn(reverse('dashboard:overview'), html)


@override_settings(AUTO_TRANSLATE=False, DEBUG=False)
class NotFoundPageTests(TestCase):
    """404 ham foydali bo'lsin — qidiruv va havolalar bilan."""

    def test_404_maxsus_sahifa(self):
        response = self.client.get('/uz/bunday-sahifa-yoq/')
        self.assertEqual(response.status_code, 404)
        html = response.content.decode('utf-8')
        self.assertIn('404', html)
        self.assertIn(reverse('catalog:search'), html)
        self.assertIn(reverse('pages:home'), html)


class ServerErrorPageTests(TestCase):
    """500 sahifasi kontekst protsessorlarisiz ham to'g'ri chiqishi kerak."""

    def test_bosh_kontekst_bilan_render_boladi(self):
        """Django 500 ni `template.render()` bilan, kontekstsiz chaqiradi."""
        html = get_template('500.html').render()
        self.assertIn('500', html)
        self.assertIn('<html', html)

    def test_base_html_ga_tayanmaydi(self):
        """`base.html` yiqilsa 500 sahifasi ham yiqilib qolmasin."""
        source = (TEMPLATES_DIR / '500.html').read_text(encoding='utf-8')
        self.assertNotIn('{% extends', source)

    def test_izoh_sahifaga_sizib_chiqmaydi(self):
        html = get_template('500.html').render()
        self.assertNotIn('{#', html)
        self.assertNotIn('{%', html)


class TemplateHealthTests(TestCase):
    """Barcha shablonlar uchun umumiy sog'liq tekshiruvi."""

    def all_templates(self):
        return sorted(TEMPLATES_DIR.rglob('*.html'))

    def test_hammasi_kompilyatsiya_boladi(self):
        for path in self.all_templates():
            name = path.relative_to(TEMPLATES_DIR).as_posix()
            with self.subTest(template=name):
                get_template(name)

    def test_kop_qatorli_izoh_yoq(self):
        """Django `{# ... #}` ni faqat BIR qatorda izoh deb biladi.

        Ko'p qatorli bo'lsa izoh matni sahifaga chiqib ketadi. Ko'p qatorli
        izoh uchun `{% comment %}` ishlatiladi.
        """
        self.assertEqual(Template('A{# izoh #}B').render(Context({})), 'AB')
        self.assertIn('{#', Template('A{# izoh\nyana #}B').render(Context({})))

        buzuq = []
        for path in self.all_templates():
            for number, line in enumerate(path.read_text(encoding='utf-8').split('\n'), 1):
                if '{#' in line and '#}' not in line:
                    buzuq.append('%s:%d' % (path.relative_to(TEMPLATES_DIR).as_posix(), number))
        self.assertEqual(buzuq, [], 'ko‘p qatorli {# #} izoh sahifaga chiqadi')
