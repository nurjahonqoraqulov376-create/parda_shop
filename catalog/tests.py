"""Katalog, qidiruv va filtrlar testlari."""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product


@override_settings(AUTO_TRANSLATE=False)
class CatalogViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Zebra', slug='zebra')
        self.cheap = Product.objects.create(
            category=self.category, name='Arzon parda', slug='arzon',
            short_description='q', description='t', price=Decimal('50000'), stock=5,
        )
        self.pricey = Product.objects.create(
            category=self.category, name='Qimmat parda', slug='qimmat',
            short_description='q', description='t', price=Decimal('500000'), stock=5,
        )
        Product.objects.create(
            name='Yashirin parda', slug='yashirin', short_description='q',
            description='t', price=Decimal('1000'), stock=1, is_active=False,
        )

    def test_katalog_ochiladi(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertEqual(response.status_code, 200)

    def test_nofaol_mahsulot_korinmaydi(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertNotContains(response, 'Yashirin parda')

    def test_kategoriya_sahifasi(self):
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 2)

    def test_mahsulot_sahifasi(self):
        response = self.client.get(self.cheap.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_nofaol_mahsulot_sahifasi_404(self):
        response = self.client.get('/uz/mahsulot/yashirin/')
        self.assertEqual(response.status_code, 404)

    def test_qidiruv_ishlaydi(self):
        response = self.client.get(reverse('catalog:search'), {'q': 'Qimmat'})
        self.assertEqual(response.context['total'], 1)

    def test_narx_filtri(self):
        response = self.client.get(reverse('catalog:list'), {'price_from': '100000'})
        self.assertEqual(response.context['total'], 1)

    def test_notogri_filtr_qiymati_yiqitmaydi(self):
        """Manzilga qo'lda yozilgan bema'ni qiymat 500 bermasin."""
        for params in ({'price_from': 'salom'}, {'price_to': '-5'}, {'sort': 'yoq'},
                       {'page': 'abc'}, {'page': '99999'}):
            with self.subTest(params=params):
                response = self.client.get(reverse('catalog:list'), params)
                self.assertEqual(response.status_code, 200)


@override_settings(AUTO_TRANSLATE=False)
class ProductModelTests(TestCase):
    def test_chegirma_foizi(self):
        product = Product.objects.create(
            name='Chegirmali', slug='chegirmali', short_description='q', description='t',
            price=Decimal('80000'), old_price=Decimal('100000'), stock=1,
        )
        self.assertEqual(product.discount_percent, 20)

    def test_eski_narx_kichik_bolsa_chegirma_yoq(self):
        product = Product.objects.create(
            name='Oddiy', slug='oddiy', short_description='q', description='t',
            price=Decimal('100000'), old_price=Decimal('90000'), stock=1,
        )
        self.assertEqual(product.discount_percent, 0)

    def test_ombor_bosh_bolsa_in_stock_false(self):
        product = Product.objects.create(
            name='Tugagan', slug='tugagan', short_description='q', description='t',
            price=Decimal('1000'), stock=0,
        )
        self.assertFalse(product.in_stock)
