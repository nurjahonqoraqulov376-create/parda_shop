"""Ommaviy sahifalar, ikki tillilik va portfolio testlari."""

from django.test import TestCase, override_settings
from django.urls import reverse

from pages.models import SiteSettings, Work
from pages.templatetags.site_extras import money
from parda_shop.translations import UI, translate


@override_settings(AUTO_TRANSLATE=False)
class PublicPageTests(TestCase):
    def test_asosiy_sahifalar_ochiladi(self):
        for name in ('pages:home', 'pages:about', 'pages:works', 'pages:contact'):
            for lang in ('uz', 'ru'):
                with self.subTest(name=name, lang=lang):
                    url = reverse(name)
                    url = '/%s/%s' % (lang, url.split('/', 2)[2])
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_olib_tashlangan_bolimlar_404(self):
        for url in ('/uz/savol-javob/', '/uz/maqolalar/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_yoq_sahifa_404(self):
        self.assertEqual(self.client.get('/uz/bunday-sahifa-yoq/').status_code, 404)


@override_settings(AUTO_TRANSLATE=False)
class WorkTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(
            title='Yotoqxona uchun zebra parda', slug='yotoqxona-zebra',
            category='Zebra parda', excerpt='Qisqacha', description='Tavsif',
            image='works/test.jpg',
        )

    def test_royxatda_korinadi(self):
        response = self.client.get(reverse('pages:works'))
        self.assertContains(response, 'Yotoqxona uchun zebra parda')

    def test_tafsilot_sahifasi(self):
        response = self.client.get(self.work.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zebra parda')

    def test_nofaol_ish_korinmaydi(self):
        self.work.is_active = False
        self.work.save()
        self.assertEqual(self.client.get(self.work.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse('pages:works')), 'yotoqxona-zebra')

    def test_bosh_sahifada_korinadi(self):
        self.assertContains(self.client.get(reverse('pages:home')), 'Yotoqxona uchun zebra parda')


class TranslationTests(TestCase):
    def test_ikki_lugat_bir_xil_kalitlarga_ega(self):
        """Bitta tilda kalit unutilsa, foydalanuvchi kalitning o'zini ko'radi."""
        uz, ru = set(UI['uz']), set(UI['ru'])
        self.assertEqual(uz - ru, set(), 'ruschada yetishmayotgan kalitlar')
        self.assertEqual(ru - uz, set(), 'o‘zbekchada yetishmayotgan kalitlar')

    def test_topilmagan_kalit_kalitning_ozini_qaytaradi(self):
        self.assertEqual(translate('bunday.kalit.yoq'), 'bunday.kalit.yoq')

    def test_ruscha_tarjima_qaytadi(self):
        self.assertEqual(translate('nav.catalog', 'ru'), 'Каталог')


class MoneyFilterTests(TestCase):
    def test_son_bolinadi(self):
        self.assertEqual(money(1234567), '1 234 567')

    def test_none_bosh_satr(self):
        """Ilgari shablonda «None» so'zi chiqib qolardi."""
        self.assertEqual(money(None), '')
        self.assertEqual(money(''), '')

    def test_notogri_qiymat_yiqitmaydi(self):
        self.assertEqual(money('salom'), 'salom')


@override_settings(AUTO_TRANSLATE=False)
class SiteSettingsTests(TestCase):
    def test_load_yagona_yozuv_yaratadi(self):
        first = SiteSettings.load()
        second = SiteSettings.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SiteSettings.objects.count(), 1)
