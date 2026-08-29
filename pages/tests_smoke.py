"""Butun sayt bo'ylab uchdan-uchgacha tekshiruv (ikki tilda).

Bu yerda alohida mayda mantiq emas, foydalanuvchi bosib o'tadigan TO'LIQ
yo'llar sinaladi: sahifa ochish, til almashtirish, savat, buyurtma, ariza,
suhbat. Maqsad — biror bo'lim jimgina buzilib qolmasin.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from catalog.models import Category, Product
from orders.models import Lead, Order
from pages.models import Work

User = get_user_model()
LANGS = ('uz', 'ru')

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


def uz(path):
    """`/uz/...` manzilini beradi (reverse joriy tilga bog'liq)."""
    return path if path.startswith('/uz/') else '/uz' + path


@NO_NETWORK
class SiteWalkTests(TestCase):
    """Har bir ommaviy sahifa ikkala tilda ham ochilishi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Zebra', slug='zebra', is_active=True)
        cls.product = Product.objects.create(
            category=cls.category, name='Zebra parda', slug='zebra-parda',
            short_description='Qisqa', description='To‘liq', price=Decimal('120000'), stock=4,
        )
        cls.work = Work.objects.create(
            title='Yotoqxona', slug='yotoqxona', category='Zebra',
            excerpt='Qisqacha', description='Tavsif', image='works/a.jpg',
        )

    def paths(self):
        return [
            '/', '/katalog/', '/qidiruv/?q=parda', '/biz-haqimizda/', '/aloqa/',
            '/ishlarimiz/', '/ishlarimiz/%s/' % self.work.slug,
            '/katalog/%s/' % self.category.slug, '/mahsulot/%s/' % self.product.slug,
            '/savat/', '/boshqaruv/kirish/',
        ]

    def test_barcha_sahifalar_ikki_tilda_ochiladi(self):
        for lang in LANGS:
            for path in self.paths():
                url = '/%s%s' % (lang, path)
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_til_almashtirish_havolasi_har_sahifada_togri(self):
        """`ru -> uz` ilgari o'sha sahifada qoldirardi (set_language xatosi)."""
        for path in self.paths():
            with self.subTest(path=path):
                html = self.client.get('/ru%s' % path).content.decode('utf-8')
                expected = '/uz%s' % path
                self.assertIn('href="%s"' % expected, html,
                              'ru sahifasida uz havolasi noto‘g‘ri: %s' % path)

    def test_til_almashtirish_haqiqatan_tilni_ozgartiradi(self):
        for path in ('/katalog/', '/aloqa/', '/ishlarimiz/'):
            with self.subTest(path=path):
                ru = self.client.get('/ru%s' % path).content.decode('utf-8')
                self.assertIn('Каталог', ru)
                uz_html = self.client.get('/uz%s' % path).content.decode('utf-8')
                self.assertIn('Katalog', uz_html)

    def test_til_almashtirishda_qidiruv_parametri_saqlanadi(self):
        html = self.client.get('/ru/katalog/?q=zebra&sort=new').content.decode('utf-8')
        self.assertIn('href="/uz/katalog/?q=zebra&amp;sort=new"', html)

    def test_til_almashtirish_csrf_talab_qilmaydi(self):
        """Havola — GET; POST bo'lganda `Referer`siz brauzerda 403 berardi."""
        html = self.client.get('/uz/').content.decode('utf-8')
        self.assertNotIn("action=\"/i18n/setlang/\"", html)
        self.assertIn('hreflang="ru"', html)


@NO_NETWORK
class ShoppingFlowTests(TestCase):
    """Savatdan buyurtmagacha — to'liq yo'l, ikkala tilda."""

    def setUp(self):
        self.product = Product.objects.create(
            name='Rimcha', slug='rimcha', short_description='q', description='t',
            price=Decimal('200000'), stock=5,
        )

    def _order_data(self):
        return {
            'full_name': 'Ali Valiyev', 'phone': '+998901234567',
            'region': 'termiz', 'address': 'Navoiy 1', 'comment': '',
        }

    def test_toliq_xarid_yoli(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                Order.objects.all().delete()
                self.product.stock = 5
                self.product.save()
                client = self.client_class()

                add = '/%s/savat/qoshish/%s/' % (lang, self.product.pk)
                self.assertEqual(client.post(add, {'quantity': 2}).status_code, 302)

                cart = client.get('/%s/savat/' % lang)
                self.assertEqual(cart.status_code, 200)
                self.assertEqual(len(cart.context['cart']), 2)

                update = '/%s/savat/yangilash/%s/' % (lang, self.product.pk)
                client.post(update, {'quantity': 3})
                self.assertEqual(len(client.get('/%s/savat/' % lang).context['cart']), 3)

                checkout = client.post('/%s/rasmiylashtirish/' % lang, self._order_data())
                self.assertEqual(checkout.status_code, 302)
                order = Order.objects.get()
                self.assertEqual(order.total_amount, Decimal('600000'))

                # «Rahmat» sahifasi shu brauzerga ochiq bo'lishi kerak.
                self.assertEqual(client.get(checkout['Location']).status_code, 200)

                self.product.refresh_from_db()
                self.assertEqual(self.product.stock, 2)

    def test_savatdan_ochirish(self):
        self.client.post('/uz/savat/qoshish/%s/' % self.product.pk, {'quantity': 1})
        self.client.post('/uz/savat/ochirish/%s/' % self.product.pk)
        self.assertTrue(self.client.get('/uz/savat/').context['cart'].is_empty)

    def test_ariza_yuborish(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                before = Lead.objects.count()
                self.client.post('/%s/sorov/' % lang, {
                    'name': 'Ali', 'phone': '+998901234567', 'lead_type': 'callback',
                })
                self.assertEqual(Lead.objects.count(), before + 1)


@NO_NETWORK
class SupportFlowTests(TestCase):
    def test_suhbat_ikki_tilda_ishlaydi(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                client = self.client_class()
                response = client.post('/%s/suhbat/yuborish/' % lang, {'text': 'Salom'})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['ok'])

                history = client.get('/%s/suhbat/xabarlar/' % lang)
                self.assertEqual(history.status_code, 200)
                self.assertTrue(history.json()['messages'])


@NO_NETWORK
class DashboardWalkTests(TestCase):
    """Har bir rol o'z sahifalarini ocha olishi va begonasiga kira olmasligi."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = {}
        for role in (Profile.ROLE_SUPPORT, Profile.ROLE_MANAGER, Profile.ROLE_ADMIN):
            user = User.objects.create_user('u_%s' % role, password='Parol12345!')
            Profile.objects.create(user=user, role=role)
            cls.roles[role] = user

    def test_admin_barcha_sahifalarni_ochadi(self):
        self.client.force_login(self.roles[Profile.ROLE_ADMIN])
        for name in ('dashboard:overview', 'dashboard:order_list', 'dashboard:lead_list',
                     'dashboard:user_list', 'dashboard:settings', 'dashboard:chat_list'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_har_rol_kirgandan_keyin_toğri_sahifaga_tushadi(self):
        cases = {
            Profile.ROLE_SUPPORT: 'dashboard:chat_list',
            Profile.ROLE_MANAGER: 'dashboard:overview',
            Profile.ROLE_ADMIN: 'dashboard:overview',
        }
        for role, target in cases.items():
            with self.subTest(role=role):
                client = self.client_class()
                client.force_login(self.roles[role])
                self.assertRedirects(client.get(reverse('dashboard:after_login')), reverse(target))

    def test_panel_ikki_tilda_ochiladi(self):
        self.client.force_login(self.roles[Profile.ROLE_ADMIN])
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(self.client.get('/%s/boshqaruv/' % lang).status_code, 200)


@NO_NETWORK
class HostileInputTests(TestCase):
    """Manzilga qo'lda yozilgan bema'ni qiymat 500 bermasin."""

    def setUp(self):
        Product.objects.create(
            name='P', slug='p', short_description='q', description='t',
            price=Decimal('1000'), stock=1,
        )

    def test_katalog_parametrlari(self):
        cases = [
            {'price_from': 'salom'}, {'price_to': '-9'}, {'sort': 'yoq'},
            {'page': '0'}, {'page': '99999'}, {'page': 'abc'},
            {'q': 'a' * 500}, {'q': '<script>alert(1)</script>'},
            {'category': 'bunday-yoq'},
        ]
        for params in cases:
            for path in ('/uz/katalog/', '/uz/qidiruv/'):
                with self.subTest(path=path, params=params):
                    self.assertEqual(self.client.get(path, params).status_code, 200)

    def test_yoq_obyektlar_404_beradi(self):
        for path in ('/uz/mahsulot/yoq/', '/uz/katalog/yoq/', '/uz/ishlarimiz/yoq/',
                     '/uz/buyurtma/999999/rahmat/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_savatga_yoq_mahsulot(self):
        self.assertEqual(self.client.post('/uz/savat/qoshish/999999/').status_code, 404)

    def test_get_bilan_ozgartirib_bolmaydi(self):
        """Savat va ariza faqat POST qabul qilishi kerak."""
        for path in ('/uz/savat/qoshish/1/', '/uz/savat/ochirish/1/', '/uz/sorov/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)


@NO_NETWORK
class HeaderLoginLinkTests(TestCase):
    """Sarlavhadagi kirish tugmasi — xodimlar panelga shu yerdan o‘tadi."""

    def setUp(self):
        # `reverse` joriy tilga bog'liq — sahifa manzili bilan bir xil
        # tilda bo'lishi uchun har safar alohida quriladi.
        self.login_url = '/uz/boshqaruv/kirish/'

    def test_mehmonga_kirish_tugmasi_korinadi(self):
        html = self.client.get('/uz/').content.decode()
        self.assertIn(self.login_url, html)

    def test_ikkala_tilda_ham_bor(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                html = self.client.get('/%s/' % lang).content.decode()
                self.assertIn('/boshqaruv/kirish/', html)

    def test_xodimga_kirish_emas_panel_havolasi(self):
        """Kirgan xodimga takroriy «Kirish» tugmasi kerak emas."""
        user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=user, role=Profile.ROLE_MANAGER)
        self.client.force_login(user)
        html = self.client.get('/uz/').content.decode()
        self.assertIn(reverse('dashboard:overview'), html)
        self.assertNotIn('href="%s"' % self.login_url, html)

    def test_kirish_sahifasi_ochiladi(self):
        self.assertEqual(self.client.get(self.login_url).status_code, 200)

    def test_bosh_sahifa_kirishga_yonaltirmaydi(self):
        """Saytga kirgan odam darrov kirish sahifasiga tushib qolmasin."""
        for path in ('/', '/uz/', '/ru/'):
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)
                self.assertEqual(response.status_code, 200)
                final = response.redirect_chain[-1][0] if response.redirect_chain else path
                self.assertNotIn('kirish', final)
