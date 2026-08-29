"""Katalog, qidiruv va filtrlar testlari."""

from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.management.commands.seed_demo import (
    CATEGORIES, SAFE_PARTS_KEYS, SEED_CATEGORY_DIR,
)
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


@override_settings(AUTO_TRANSLATE=False)
class SeedCategoriesOnlyTests(TestCase):
    """`seed_demo --categories-only` — haqiqiy saytni to‘ldirish uchun.

    To‘liq `seed_demo` o‘ylab topilgan nom va narxli 70 ta mahsulot
    yaratadi. Ular ishlab turgan do‘konda turishi mumkin emas: mijoz
    soxta narxni ko‘rib qo‘ng‘iroq qiladi. Shu bayroq bilan faqat
    kategoriya tuzilmasi yaratiladi.
    """

    def run_cmd(self):
        from io import StringIO
        out = StringIO()
        call_command('seed_demo', '--categories-only', stdout=out)
        return out.getvalue()

    def test_kategoriyalar_yaratiladi(self):
        self.run_cmd()
        self.assertEqual(Category.objects.count(), len(CATEGORIES))

    def test_mahsulot_yaratilmaydi(self):
        self.run_cmd()
        self.assertEqual(Product.objects.count(), 0)

    def test_ruscha_nomlar_toldiriladi(self):
        self.run_cmd()
        self.assertFalse(Category.objects.filter(name_ru='').exists())

    def test_qayta_ishga_tushirsa_takrorlanmaydi(self):
        self.run_cmd()
        self.run_cmd()
        self.assertEqual(Category.objects.count(), len(CATEGORIES))

    def test_har_bir_kategoriya_uchun_seed_rasmi_bor(self):
        """Rasmi yo‘q kategoriya katalogda bo‘sh katak bo‘lib turadi."""
        for slug in (item[0] for item in CATEGORIES):
            with self.subTest(slug=slug):
                found = any((SEED_CATEGORY_DIR / (slug + suffix)).exists()
                            for suffix in ('.jpg', '.jpeg', '.png', '.webp'))
                self.assertTrue(found, 'seed/categories/%s.jpg yo‘q' % slug)

    def test_mavjud_rasm_ustidan_yozilmaydi(self):
        """Paneldan yuklangan rasm joylashtirishda yo‘qolmasligi kerak."""
        category = Category.objects.create(
            name='Plisse jalyuzi', slug='plisse-jalyuzi', image='categories/qolda.jpg')
        self.run_cmd()
        category.refresh_from_db()
        self.assertEqual(category.image.name, 'categories/qolda.jpg')


@override_settings(AUTO_TRANSLATE=False)
class SeedOnlyPartsTests(TestCase):
    """`--only` — ishlab turgan saytga chiqarish mumkin bo‘lgan qismlar.

    To‘liq `seed_demo` uchta narsani yaratadi va ular haqiqiy do‘konda
    turishi mumkin emas: o‘ylab topilgan narxli mahsulotlar, soxta mijoz
    sharhlari va soxta hamkorlar ro‘yxati. `--only` ularga yo‘l bermaydi.
    """

    def run_only(self, *parts):
        from io import StringIO
        out = StringIO()
        call_command('seed_demo', '--only', *parts, stdout=out)
        return out.getvalue()

    def test_afzalliklar_yaratiladi(self):
        from pages.models import Advantage
        self.run_only('advantages')
        self.assertGreater(Advantage.objects.filter(is_active=True).count(), 0)

    def test_bir_nechta_qism_birga(self):
        from pages.models import Advantage
        self.run_only('advantages', 'categories')
        self.assertGreater(Advantage.objects.count(), 0)
        self.assertEqual(Category.objects.count(), len(CATEGORIES))

    def test_soxta_kontent_hech_qachon_yaratilmaydi(self):
        from pages.models import Client, Testimonial
        self.run_only(*SAFE_PARTS_KEYS)
        self.assertEqual(Product.objects.count(), 0, 'o‘ylab topilgan narx saytga chiqdi')
        self.assertEqual(Testimonial.objects.count(), 0, 'soxta mijoz sharhi saytga chiqdi')
        self.assertEqual(Client.objects.count(), 0, 'soxta hamkor saytga chiqdi')

    def test_notanish_qism_rad_etiladi(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.run_only('mahsulotlar')

    def test_eski_bayroq_ishlashda_davom_etadi(self):
        from io import StringIO
        call_command('seed_demo', '--categories-only', stdout=StringIO())
        self.assertEqual(Category.objects.count(), len(CATEGORIES))

    def test_qayta_ishga_tushirsa_takrorlanmaydi(self):
        from pages.models import Advantage
        self.run_only('advantages')
        count = Advantage.objects.count()
        self.run_only('advantages')
        self.assertEqual(Advantage.objects.count(), count)
