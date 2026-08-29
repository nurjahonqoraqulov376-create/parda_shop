"""Qidiruv tizimlari va brauzer so'raydigan fayllar.

Ishlab chiqarish jurnalidan olingan dalil: 500 qatorlik jurnalda
`/favicon.ico` ga **33 ta** 404 va `/sitemap.xml` ga 404 tushgan edi.
Brauzer faviconni har sahifada so'raydi, qidiruv roboti esa sayt
xaritasini o'zi qidiradi.
"""

import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from catalog.models import Category, Product
from pages.models import Work

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


@NO_NETWORK
class RobotsTests(TestCase):
    def test_ochiladi(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)

    def test_matn_sifatida_beriladi(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response['Content-Type'].split(';')[0], 'text/plain')

    def test_til_prefiksisiz_manzilda(self):
        """Robot uni aynan ildizdan qidiradi — `/uz/robots.txt` yaramaydi."""
        self.assertEqual(self.client.get('/robots.txt').status_code, 200)

    def test_sitemap_manzili_korsatilgan(self):
        body = self.client.get('/robots.txt').content.decode()
        self.assertIn('/sitemap.xml', body)

    def test_sitemap_manzili_joriy_domendan(self):
        """Domen almashsa fayl o‘zi to‘g‘ri manzilni ko‘rsatsin."""
        body = self.client.get('/robots.txt', headers={'host': 'testserver'}).content.decode()
        self.assertIn('http://testserver/sitemap.xml', body)

    def test_panel_indeksga_tushmaydi(self):
        body = self.client.get('/robots.txt').content.decode()
        for path in ('/uz/boshqaruv/', '/ru/boshqaruv/', '/admin/'):
            with self.subTest(path=path):
                self.assertIn('Disallow: %s' % path, body)

    def test_ommaviy_qism_ochiq(self):
        body = self.client.get('/robots.txt').content.decode()
        self.assertIn('Allow: /', body)
        self.assertNotIn('Disallow: /\n', body)


@NO_NETWORK
class SitemapTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Zebra', slug='zebra')
        self.product = Product.objects.create(
            category=self.category, name='Zebra parda', slug='zebra-parda',
            short_description='q', description='t', price=100000, stock=3)
        self.work = Work.objects.create(
            title='Mehmonxona', slug='mehmonxona', category='Baxmal',
            excerpt='e', description='d')

    def body(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def locations(self):
        return re.findall(r'<loc>([^<]+)</loc>', self.body())

    def test_ochiladi(self):
        self.assertEqual(self.client.get('/sitemap.xml').status_code, 200)

    def test_bosh_sahifa_bor(self):
        self.assertTrue(any(url.endswith('/uz/') for url in self.locations()))

    def test_ikkala_til_ham_bor(self):
        urls = self.locations()
        self.assertTrue(any('/uz/' in url for url in urls))
        self.assertTrue(any('/ru/' in url for url in urls))

    def test_kategoriya_mahsulot_ish_bor(self):
        urls = ' '.join(self.locations())
        for slug in ('zebra', 'zebra-parda', 'mehmonxona'):
            with self.subTest(slug=slug):
                self.assertIn(slug, urls)

    def test_nofaol_yozuv_chiqmaydi(self):
        self.product.is_active = False
        self.product.save()
        self.assertNotIn('zebra-parda', ' '.join(self.locations()))

    def test_panel_manzillari_yoq(self):
        self.assertNotIn('boshqaruv', ' '.join(self.locations()))

    def test_xml_sifatida_beriladi(self):
        response = self.client.get('/sitemap.xml')
        self.assertIn('xml', response['Content-Type'])


@NO_NETWORK
class FaviconTests(TestCase):
    """Brauzer har sahifada `/favicon.ico` so‘raydi — jurnal 404 ga to‘lardi."""

    def test_fayl_repoda_bor(self):
        from django.conf import settings
        from pathlib import Path
        found = [Path(root) / 'img' / 'favicon.ico' for root in settings.STATICFILES_DIRS]
        self.assertTrue(any(path.exists() for path in found), 'favicon.ico topilmadi')

    def test_sahifada_havola_bor(self):
        html = self.client.get('/uz/').content.decode()
        self.assertIn('rel="icon"', html)

    def test_apple_ikonkasi_ham_bor(self):
        """iPhone «bosh ekranga qo‘shish» da shu rasmni oladi."""
        html = self.client.get('/uz/').content.decode()
        self.assertIn('apple-touch-icon', html)

    def test_panelda_ham_bor(self):
        user = User.objects.create_superuser('boss', 'b@example.com', 'Parol12345!')
        self.client.force_login(user)
        html = self.client.get('/uz/boshqaruv/').content.decode()
        self.assertIn('rel="icon"', html)
