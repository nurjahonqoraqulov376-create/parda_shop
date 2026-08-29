"""CSRF xatosining sabablari va ko'rinishi.

Ishlab chiqarish jurnalidan olingan dalil:

    403 POST /uz/boshqaruv/yordamchi/soragan/
    403 POST /uz/boshqaruv/yordamchi/tozalash/
    403 POST /uz/boshqaruv/suhbatlar/2/

Sababi: JavaScript CSRF tokenini sahifa ochilganda BIR MARTA o'qib olardi.
Django esa kirish va chiqishda tokenni almashtiradi (`rotate_token`) —
ochiq turgan sahifadagi token eskirib, har bir yuborish 403 bilan qaytardi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.middleware.csrf import rotate_token
from django.test import Client, RequestFactory, TestCase, override_settings

from accounts.models import Profile

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


def js_source(name):
    for root in settings.STATICFILES_DIRS:
        path = Path(root) / 'js' / name
        if path.exists():
            return path.read_text(encoding='utf-8')
    raise AssertionError('%s topilmadi' % name)


class TokenSourceTests(TestCase):
    """JS token qayerdan olishini qo'riqlaydi.

    Sahifa ochilganda o'qib qo'yilgan token vaqt o'tib eskiradi;
    cookie'dagi qiymat esa doim joriy.
    """

    def test_support_cookiedan_oladi(self):
        self.assertIn('csrftoken=', js_source('support.js'))

    def test_agent_cookiedan_oladi(self):
        self.assertIn('csrftoken=', js_source('agent.js'))

    def test_support_tokenni_saqlab_qolmaydi(self):
        """`const csrf = ...` — aynan shu qator 403 larga sabab bo‘lgandi."""
        source = js_source('support.js')
        self.assertNotIn("const csrf = form.querySelector", source)

    def test_agent_tokenni_har_safar_oladi(self):
        source = js_source('agent.js')
        # `token()` funksiya bo'lib qolishi kerak, o'zgarmas emas.
        self.assertIn('function token()', source)

    def test_cookie_js_uchun_ochiq(self):
        """`CSRF_COOKIE_HTTPONLY=True` bo‘lsa JS uni o‘qiy olmaydi."""
        self.assertFalse(getattr(settings, 'CSRF_COOKIE_HTTPONLY', False))


@NO_NETWORK
class TokenRotationTests(TestCase):
    """Kirishdan keyin eski token yaroqsiz bo'lib qoladi — shuni ko'rsatamiz."""

    def test_kirish_tokenni_almashtiradi(self):
        factory = RequestFactory()
        request = factory.get('/uz/')
        request.META['CSRF_COOKIE'] = 'eski-token'
        rotate_token(request)
        self.assertNotEqual(request.META['CSRF_COOKIE'], 'eski-token')

    def test_eski_token_bilan_yuborish_403(self):
        """Aynan foydalanuvchi duch kelgan holat."""
        client = Client(enforce_csrf_checks=True)
        client.get('/uz/')
        response = client.post('/uz/sorov/', {
            'csrfmiddlewaretoken': 'eskirgan-qiymat',
            'name': 'Ali', 'phone': '+998901234567', 'lead_type': 'callback',
        })
        self.assertEqual(response.status_code, 403)

    def test_joriy_token_bilan_yuborish_ishlaydi(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get('/uz/')
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode()).group(1)
        response = client.post('/uz/sorov/', {
            'csrfmiddlewaretoken': token,
            'name': 'Ali', 'phone': '+998901234567', 'lead_type': 'callback',
        })
        self.assertEqual(response.status_code, 302)


@NO_NETWORK
class CsrfFailurePageTests(TestCase):
    """Xato yuz berganda mijoz nimani ko'radi.

    Django o'zining ichki sahifasini beradi — inglizcha va texnik.
    `403_csrf.html` bo'lsa o'shani ishlatadi.
    """

    def failure_page(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/uz/')
        response = client.post('/uz/sorov/', {
            'csrfmiddlewaretoken': 'notogri',
            'name': 'Ali', 'phone': '+998901234567', 'lead_type': 'callback',
        })
        self.assertEqual(response.status_code, 403)
        return response.content.decode()

    def test_shablon_mavjud(self):
        from django.template.loader import get_template
        get_template('403_csrf.html')

    def test_ozbekcha_matn_chiqadi(self):
        html = self.failure_page()
        self.assertIn('eskirib', html.lower())

    def test_inglizcha_ichki_sahifa_emas(self):
        """Django ichki sahifasida aynan shu ibora bor."""
        html = self.failure_page()
        self.assertNotIn('CSRF verification failed', html)
        self.assertNotIn('Forbidden (403)', html)

    def test_yangilash_tugmasi_bor(self):
        self.assertIn('location.reload', self.failure_page())

    def test_saytning_ozi_dizaynida(self):
        """Sayt sarlavhasi ko‘rinsin — mijoz qayerdaligini bilsin."""
        self.assertIn('Sevara Design', self.failure_page())


@NO_NETWORK
class StaffFormsStillWorkTests(TestCase):
    """Tuzatishdan keyin xodim formalari ishlashda davom etsin."""

    def setUp(self):
        self.user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=self.user, role=Profile.ROLE_MANAGER)

    def test_kategoriya_qoshish_ishlaydi(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        page = client.get('/uz/boshqaruv/kategoriyalar/yangi/')
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode()).group(1)
        response = client.post('/uz/boshqaruv/kategoriyalar/yangi/', {
            'csrfmiddlewaretoken': token, 'name': 'Yangi tur', 'slug': '',
            'icon': '', 'description': '', 'sort_order': '1',
        })
        self.assertIn(response.status_code, (200, 302))
