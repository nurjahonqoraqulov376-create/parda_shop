"""Savat va buyurtma oqimi testlari.

Har bir test bir marta topilgan aniq xatoni qo'riqlaydi — kod o'zgarganda
o'sha xato qaytib kelsa, test darhol qizil bo'ladi.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from catalog.models import Category, Product
from orders.cart import MAX_QUANTITY
from orders.models import Order

User = get_user_model()


def make_product(**kwargs):
    defaults = {
        'name': 'Zebra parda',
        'slug': 'zebra-parda',
        'short_description': 'Qisqa tavsif',
        'description': 'To‘liq tavsif',
        'price': Decimal('100000'),
        'stock': 5,
        'is_active': True,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


# Tarmoqqa chiqadigan avtomatik tarjima testlarda o'chirilgan bo'lsin.
@override_settings(AUTO_TRANSLATE=False)
class CartRobustnessTests(TestCase):
    """Sessiyadagi ma'lumot buzilgan bo'lsa ham sayt ishlashda davom etsin."""

    def setUp(self):
        self.product = make_product()

    def _set_cart(self, data):
        session = self.client.session
        session['cart'] = data
        session.save()

    def test_buzilgan_sessiya_saytni_yiqitmaydi(self):
        """Savat kontekst protsessorida — buzilgan ma'lumot butun saytni o'chirardi."""
        self._set_cart({
            'abc': {'quantity': 1, 'price': '100'},        # raqam bo'lmagan kalit
            '999': {'quantity': 'kop', 'price': '100'},    # son emas
            '998': {'quantity': 2, 'price': 'narx'},       # narx emas
            '997': 'umuman dict emas',
            str(self.product.pk): {'quantity': 2, 'price': '100000'},
        })
        response = self.client.get(reverse('pages:home'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('orders:cart_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['cart']), 2)

    def test_sessiya_royxat_bolsa_ham_yiqilmaydi(self):
        self._set_cart(['bu', 'dict', 'emas'])
        self.assertEqual(self.client.get(reverse('pages:home')).status_code, 200)

    def test_nofaol_mahsulot_savatdan_chiqadi(self):
        """Nofaol mahsulot ro'yxatda ko'rinmasdan summaga qo'shilib turardi."""
        other = make_product(name='Rimcha', slug='rimcha', price=Decimal('50000'))
        self._set_cart({
            str(self.product.pk): {'quantity': 1, 'price': '100000'},
            str(other.pk): {'quantity': 1, 'price': '50000'},
        })
        other.is_active = False
        other.save()

        response = self.client.get(reverse('orders:cart_detail'))
        cart = response.context['cart']
        self.assertEqual(len(cart), 1)
        # Jami summa ko'rsatilgan qatorlar bilan mos bo'lishi shart.
        self.assertEqual(cart.total, Decimal('100000'))

    def test_ochirilgan_mahsulot_savatdan_chiqadi(self):
        ghost_pk = self.product.pk + 12345
        self._set_cart({ghost_pk_str: {'quantity': 3, 'price': '70000'}
                        for ghost_pk_str in [str(ghost_pk)]})
        response = self.client.get(reverse('orders:cart_detail'))
        self.assertTrue(response.context['cart'].is_empty)

    def test_narx_bazadagi_joriy_narxdan_olinadi(self):
        """Sessiyada eskirgan narx qolib ketardi — mijoz eski narxni to'lardi."""
        self._set_cart({str(self.product.pk): {'quantity': 2, 'price': '1'}})
        response = self.client.get(reverse('orders:cart_detail'))
        self.assertEqual(response.context['cart'].total, Decimal('200000'))

    def test_miqdor_yuqori_chegara_bilan_cheklanadi(self):
        self._set_cart({str(self.product.pk): {'quantity': 10 ** 9, 'price': '100000'}})
        response = self.client.get(reverse('orders:cart_detail'))
        self.assertEqual(len(response.context['cart']), MAX_QUANTITY)


@override_settings(AUTO_TRANSLATE=False)
class CartStockTests(TestCase):
    def setUp(self):
        self.product = make_product(stock=3)

    def test_tugagan_mahsulot_savatga_qoshilmaydi(self):
        self.product.stock = 0
        self.product.save()
        self.client.post(reverse('orders:cart_add', args=[self.product.pk]), {'quantity': 1})
        response = self.client.get(reverse('orders:cart_detail'))
        self.assertTrue(response.context['cart'].is_empty)

    def test_ombordagidan_kop_soralsa_kamaytiriladi(self):
        self.client.post(reverse('orders:cart_add', args=[self.product.pk]), {'quantity': 99})
        response = self.client.get(reverse('orders:cart_detail'))
        self.assertEqual(len(response.context['cart']), 3)

    def test_son_bolmagan_miqdor_yiqitmaydi(self):
        response = self.client.post(
            reverse('orders:cart_add', args=[self.product.pk]), {'quantity': 'salom'},
        )
        self.assertEqual(response.status_code, 302)


@override_settings(AUTO_TRANSLATE=False)
class CheckoutTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Pardalar', slug='pardalar')
        self.product = make_product(category=self.category, stock=2)

    def _fill_cart(self, quantity=1):
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': quantity, 'price': str(self.product.price)}}
        session.save()

    def _order_payload(self):
        return {
            'full_name': 'Ali Valiyev',
            'phone': '+998901234567',
            'region': 'termiz',
            'address': 'Navoiy 12',
            'comment': '',
        }

    def test_buyurtma_yaratiladi_va_ombor_kamayadi(self):
        self._fill_cart(quantity=2)
        response = self.client.post(reverse('orders:checkout'), self._order_payload())
        self.assertEqual(response.status_code, 302)

        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_amount, Decimal('200000'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_ombordan_kop_buyurtma_qabul_qilinmaydi(self):
        """Ilgari ombor manfiyga tushib, 0 ga «yaxlitlanardi»."""
        self._fill_cart(quantity=2)
        self.product.stock = 1
        self.product.save()

        response = self.client.post(reverse('orders:checkout'), self._order_payload())
        self.assertRedirects(response, reverse('orders:cart_detail'))
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)  # ombor o'zgarmagan

    def test_nofaol_mahsulotni_rasmiylashtirib_bolmaydi(self):
        self._fill_cart(quantity=1)
        self.product.is_active = False
        self.product.save()
        response = self.client.post(reverse('orders:checkout'), self._order_payload())
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(response.status_code, 302)

    def test_bosh_savat_bilan_katalogga_qaytariladi(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('catalog:list'))


@override_settings(AUTO_TRANSLATE=False)
class OrderPrivacyTests(TestCase):
    """«Rahmat» sahifasi begona buyurtmani ko'rsatmasligi kerak."""

    def setUp(self):
        self.product = make_product()
        self.order = Order.objects.create(
            full_name='Ali Valiyev', phone='+998901234567',
            region='termiz', address='Navoiy 12',
        )

    def test_begona_odam_kora_olmaydi(self):
        """Ilgari manzildagi raqamni almashtirib har kimning ma'lumotini o'qish mumkin edi."""
        response = self.client.get(reverse('orders:success', args=[self.order.pk]))
        self.assertEqual(response.status_code, 404)

    def test_buyurtma_bergan_brauzer_kora_oladi(self):
        session = self.client.session
        session['completed_orders'] = [self.order.pk]
        session.save()
        response = self.client.get(reverse('orders:success', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#%s' % self.order.pk)

    def test_menejer_kora_oladi(self):
        staff = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=staff, role=Profile.ROLE_MANAGER)
        self.client.force_login(staff)
        response = self.client.get(reverse('orders:success', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)


@override_settings(AUTO_TRANSLATE=False)
class LeadTests(TestCase):
    def test_tashqi_saytga_yonaltirish_bloklanadi(self):
        """`next` orqali begona saytga olib chiqib bo'lmasin (open redirect)."""
        response = self.client.post(reverse('orders:lead_create'), {
            'name': 'Ali', 'phone': '+998901234567',
            'lead_type': 'callback', 'next': 'https://firibgar.example/',
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('firibgar.example', response['Location'])

    def test_notogri_telefon_rad_etiladi(self):
        from orders.models import Lead
        self.client.post(reverse('orders:lead_create'), {
            'name': 'Ali', 'phone': '12', 'lead_type': 'callback',
        })
        self.assertEqual(Lead.objects.count(), 0)
