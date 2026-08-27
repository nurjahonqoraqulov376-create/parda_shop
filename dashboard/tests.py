"""Boshqaruv paneli — ruxsatlar va xavfsiz o'chirish testlari."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from catalog.models import Product
from dashboard.registry import REGISTRY, get_form_class
from orders.models import Order
from support.models import Conversation, Message

User = get_user_model()


def make_staff(username, role):
    user = User.objects.create_user(username, password='Parol12345!')
    Profile.objects.create(user=user, role=role)
    return user


@override_settings(AUTO_TRANSLATE=False)
class AccessTests(TestCase):
    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.admin = make_staff('admin2', Profile.ROLE_ADMIN)
        self.outsider = User.objects.create_user('mijoz', password='Parol12345!')

    def test_mehmon_kirish_sahifasiga_yonaltiriladi(self):
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('kirish', response['Location'])

    def test_profilsiz_foydalanuvchiga_ruxsat_yoq(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse('dashboard:overview')).status_code, 403)

    def test_menejer_kira_oladi(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('dashboard:overview')).status_code, 200)

    def test_menejer_admin_bolimiga_kira_olmaydi(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('dashboard:user_list')).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('dashboard:section_list', args=['bannerlar'])).status_code, 403,
        )

    def test_admin_hamma_joyga_kiradi(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('dashboard:user_list')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('dashboard:section_list', args=['bannerlar'])).status_code, 200,
        )

    def test_yoq_bolim_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('dashboard:section_list', args=['bunday-bolim-yoq'])).status_code, 404,
        )

    def test_barcha_bolimlar_ochiladi(self):
        """Registry'ga yangi bo'lim qo'shilganda u darhol sinaladi."""
        self.client.force_login(self.admin)
        for key in REGISTRY:
            with self.subTest(key=key):
                self.assertEqual(
                    self.client.get(reverse('dashboard:section_list', args=[key])).status_code, 200,
                )
                self.assertEqual(
                    self.client.get(reverse('dashboard:section_create', args=[key])).status_code, 200,
                )


@override_settings(AUTO_TRANSLATE=False)
class ProtectedDeleteTests(TestCase):
    """Buyurtmada ishlatilgan mahsulotni o'chirish 500 xato berardi."""

    def setUp(self):
        self.admin = make_staff('admin3', Profile.ROLE_ADMIN)
        self.client.force_login(self.admin)
        self.product = Product.objects.create(
            name='Sotilgan parda', slug='sotilgan', short_description='q',
            description='t', price=Decimal('100000'), stock=1,
        )
        order = Order.objects.create(
            full_name='Ali', phone='+998901234567', region='termiz', address='Navoiy 1',
        )
        order.items.create(product=self.product, quantity=1, price=self.product.price)

    def test_ochirish_500_bermaydi(self):
        url = reverse('dashboard:section_delete', args=['mahsulotlar', self.product.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_bemalol_ochiriladigan_yozuv_ochiriladi(self):
        free = Product.objects.create(
            name='Erkin parda', slug='erkin', short_description='q',
            description='t', price=Decimal('1000'), stock=1,
        )
        url = reverse('dashboard:section_delete', args=['mahsulotlar', free.pk])
        self.client.post(url)
        self.assertFalse(Product.objects.filter(pk=free.pk).exists())


class RegistryTests(TestCase):
    def test_har_bir_bolim_uchun_forma_yasaladi(self):
        for key, section in REGISTRY.items():
            with self.subTest(key=key):
                form = get_form_class(key)()
                # Ustunlarda ko'rsatilgan har bir maydon modelda bo'lishi shart.
                for _, attr in section['columns']:
                    self.assertTrue(
                        hasattr(section['model'], attr),
                        '%s bo‘limida «%s» maydoni yo‘q' % (key, attr),
                    )
                # Qidiruv maydonlari ham haqiqiy bo'lsin.
                field_names = {f.name for f in section['model']._meta.get_fields()}
                for field in section['search_fields']:
                    self.assertIn(field, field_names, '%s: %s maydoni yo‘q' % (key, field))
                self.assertTrue(form.fields)


@override_settings(AUTO_TRANSLATE=False)
class SupportRoleTests(TestCase):
    """Support xodimi faqat suhbatlarni ko'radi — boshqa hech narsani."""

    def setUp(self):
        self.support = make_staff('support_xodim', Profile.ROLE_SUPPORT)
        self.conversation = Conversation.objects.create(
            session_key='abc', status=Conversation.STATUS_WAITING,
        )
        Message.objects.create(
            conversation=self.conversation, sender=Message.SENDER_VISITOR,
            text='jonli operator kerak',
        )
        self.client.force_login(self.support)

    def test_suhbatlarga_kiradi(self):
        self.assertEqual(self.client.get(reverse('dashboard:chat_list')).status_code, 200)
        detail = reverse('dashboard:chat_detail', args=[self.conversation.pk])
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_buyurtma_va_sorovlarga_kira_olmaydi(self):
        for name in ('dashboard:overview', 'dashboard:order_list',
                     'dashboard:lead_list', 'dashboard:user_list', 'dashboard:settings'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_crud_bolimlariga_kira_olmaydi(self):
        for key in ('mahsulotlar', 'kategoriyalar', 'ishlarimiz', 'bannerlar'):
            with self.subTest(key=key):
                url = reverse('dashboard:section_list', args=[key])
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_kirgandan_keyin_suhbatlarga_tushadi(self):
        response = self.client.get(reverse('dashboard:after_login'))
        self.assertRedirects(response, reverse('dashboard:chat_list'))

    def test_menyuda_faqat_suhbatlar_korinadi(self):
        html = self.client.get(reverse('dashboard:chat_list')).content.decode('utf-8')
        self.assertIn(reverse('dashboard:chat_list'), html)
        self.assertNotIn(reverse('dashboard:order_list'), html)
        self.assertNotIn(reverse('dashboard:lead_list'), html)

    def test_javob_yozganda_ai_ochadi(self):
        url = reverse('dashboard:chat_detail', args=[self.conversation.pk])
        self.client.post(url, {'text': 'Assalomu alaykum, tinglayman'})
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, Conversation.STATUS_WITH_OPERATOR)
        self.assertEqual(self.conversation.operator, self.support)
        self.assertTrue(self.conversation.messages.filter(sender='operator').exists())

    def test_ochilganda_oqilgan_deb_belgilanadi(self):
        self.assertEqual(self.conversation.unread_count, 1)
        self.client.get(reverse('dashboard:chat_detail', args=[self.conversation.pk]))
        self.assertEqual(self.conversation.unread_count, 0)

    def test_suhbatni_yopadi(self):
        url = reverse('dashboard:chat_close', args=[self.conversation.pk])
        self.client.post(url)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, Conversation.STATUS_CLOSED)


@override_settings(AUTO_TRANSLATE=False)
class ManagerChatAccessTests(TestCase):
    """Menejer va admin ham suhbatlarni ko'radi."""

    def test_menejer_kiradi(self):
        self.client.force_login(make_staff('menejer_chat', Profile.ROLE_MANAGER))
        self.assertEqual(self.client.get(reverse('dashboard:chat_list')).status_code, 200)

    def test_admin_umumiy_korinishga_tushadi(self):
        self.client.force_login(make_staff('admin_chat', Profile.ROLE_ADMIN))
        response = self.client.get(reverse('dashboard:after_login'))
        self.assertRedirects(response, reverse('dashboard:overview'))

    def test_profilsiz_foydalanuvchi_kira_olmaydi(self):
        outsider = User.objects.create_user('begona', password='Parol12345!')
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('dashboard:chat_list')).status_code, 403)
