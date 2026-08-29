"""Guruhlangan formalar, o'z profili va «kim qo'shgan».

Ilgari mahsulot formasi 15 dan ortiq maydonni bitta uzun ustunga tizardi
va xodim nimadan boshlashni bilmasdi. Shuningdek, xodim o'z ismini yoki
parolini o'zi o'zgartira olmasdi — administratorga murojaat qilardi.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from catalog.models import Category, Product
from dashboard.fieldgroups import GROUPS, OTHER_TITLE, group_fields
from dashboard.registry import REGISTRY, get_form_class
from pages.models import Work

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


def tiny_image():
    """Kichik haqiqiy JPEG — `Work` rasmsiz saqlanmaydi."""
    import io as _io
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image
    buffer = _io.BytesIO()
    Image.new('RGB', (40, 30), (200, 180, 160)).save(buffer, 'JPEG')
    return SimpleUploadedFile('ish.jpg', buffer.getvalue(), content_type='image/jpeg')


def make_staff(username, role):
    user = User.objects.create_user(username, password='Parol12345!')
    Profile.objects.create(user=user, role=role)
    return user


class FieldGroupTests(TestCase):
    """Guruhlash maydon NOMI bo'yicha ishlaydi — har model uchun sozlash shart emas."""

    def groups(self, key):
        return group_fields(get_form_class(key)())

    def test_mahsulot_guruhlarga_bolinadi(self):
        titles = [g['title'] for g in self.groups('mahsulotlar')]
        self.assertIn('Asosiy ma’lumot', titles)
        self.assertIn('Narx va ombor', titles)
        self.assertIn('Matnlar', titles)

    def test_hech_bir_maydon_yoqolmaydi(self):
        """Tanish bo‘lmagan maydon oxirgi guruhga tushishi kerak."""
        for key in REGISTRY:
            with self.subTest(section=key):
                form = get_form_class(key)()
                grouped = [f.name for g in group_fields(form) for f in g['fields']]
                self.assertEqual(sorted(grouped), sorted(f.name for f in form))

    def test_maydon_ikki_marta_chiqmaydi(self):
        for key in REGISTRY:
            with self.subTest(section=key):
                names = [f.name for g in self.groups(key) for f in g['fields']]
                self.assertEqual(len(names), len(set(names)))

    def test_bosh_guruh_korsatilmaydi(self):
        for key in REGISTRY:
            with self.subTest(section=key):
                for group in self.groups(key):
                    self.assertTrue(group['fields'], '%s bo‘sh guruh' % group['title'])

    def test_ruscha_maydon_tarjimasi_yonida(self):
        """`name` va `name_ru` bir guruhda, yonma-yon tursin."""
        fields = [f.name for f in self.groups('mahsulotlar')[0]['fields']]
        self.assertEqual(fields.index('name_ru'), fields.index('name') + 1)

    def test_narx_alohida_guruhda(self):
        for group in self.groups('mahsulotlar'):
            if group['title'] == 'Narx va ombor':
                names = [f.name for f in group['fields']]
                self.assertIn('price', names)
                self.assertIn('stock', names)
                return
        self.fail('«Narx va ombor» guruhi topilmadi')

    def test_guruh_nomlari_takrorlanmaydi(self):
        titles = [title for title, _note, _names in GROUPS] + [OTHER_TITLE]
        self.assertEqual(len(titles), len(set(titles)))


class FieldHintTests(TestCase):
    """Har bir muhim maydonda tushuntirish bo'lsin."""

    def test_narxda_tushuntirish_bor(self):
        form = get_form_class('mahsulotlar')()
        self.assertTrue(form.fields['price'].help_text)

    def test_slugda_tushuntirish_bor(self):
        """Slug — xodim uchun eng tushunarsiz maydon; bo‘sh qoldirsa
        bo‘lishini aytib turishi kerak."""
        hint = get_form_class('mahsulotlar')().fields['slug'].help_text
        self.assertIn('bo‘sh qoldiring', hint.lower())

    def test_muhim_maydonlar_izohsiz_qolmaydi(self):
        form = get_form_class('mahsulotlar')()
        for name in ('name', 'price', 'stock', 'image', 'is_active'):
            with self.subTest(field=name):
                self.assertTrue(form.fields[name].help_text, '%s izohsiz' % name)


@NO_NETWORK
class SectionFormPageTests(TestCase):
    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.admin = make_staff('boshliq', Profile.ROLE_ADMIN)
        self.category = Category.objects.create(name='Zebra', slug='zebra')
        self.client.force_login(self.manager)
        self.url = reverse('dashboard:section_create', args=['mahsulotlar'])

    def test_sahifa_ochiladi(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_guruh_sarlavhalari_korinadi(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Narx va ombor', html)
        self.assertIn('fset-legend', html)

    def test_majburiy_maydon_belgilangan(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('class="req"', html)

    def test_saqlash_ishlaydi(self):
        response = self.client.post(self.url, {
            'name': 'Yangi parda', 'slug': '', 'category': self.category.pk,
            'price': '250000', 'old_price': '', 'stock': '5', 'sku': '',
            'short_description': 'qisqa', 'description': 'to‘liq',
            'sort_order': '0',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='Yangi parda').exists())

    def test_xato_bolsa_ogohlantiradi(self):
        response = self.client.post(self.url, {'name': '', 'price': ''})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('has-error', html)

    def test_menejerga_ochirish_tugmasi_korinmaydi(self):
        """O‘chirish faqat administratorda."""
        product = Product.objects.create(
            category=self.category, name='A', slug='a', short_description='q',
            description='t', price=Decimal('1'), stock=1)
        url = reverse('dashboard:section_edit', args=['mahsulotlar', product.pk])
        self.assertNotIn('button danger', self.client.get(url).content.decode())

    def test_adminga_ochirish_tugmasi_korinadi(self):
        product = Product.objects.create(
            category=self.category, name='B', slug='b', short_description='q',
            description='t', price=Decimal('1'), stock=1)
        self.client.force_login(self.admin)
        url = reverse('dashboard:section_edit', args=['mahsulotlar', product.pk])
        self.assertIn('button danger', self.client.get(url).content.decode())


@NO_NETWORK
class CreatedByTests(TestCase):
    """Kim qo'shganini eslab qolamiz — xodim o'z yozuvlarini ajrata olsin."""

    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.other = make_staff('boshqa', Profile.ROLE_MANAGER)
        self.category = Category.objects.create(name='Zebra', slug='zebra')
        self.client.force_login(self.manager)

    def add_product(self, name):
        self.client.post(reverse('dashboard:section_create', args=['mahsulotlar']), {
            'name': name, 'slug': '', 'category': self.category.pk,
            'price': '100000', 'old_price': '', 'stock': '1', 'sku': '',
            'short_description': 'q', 'description': 't', 'sort_order': '0',
        })
        return Product.objects.get(name=name)

    def test_qoshgan_xodim_yoziladi(self):
        self.assertEqual(self.add_product('Meniki').created_by, self.manager)

    def test_tahrirlaganda_muallif_ozgarmaydi(self):
        product = self.add_product('Meniki')
        self.client.force_login(self.other)
        self.client.post(
            reverse('dashboard:section_edit', args=['mahsulotlar', product.pk]), {
                'name': 'Tahrirlandi', 'slug': product.slug, 'category': self.category.pk,
                'price': '120000', 'old_price': '', 'stock': '1', 'sku': '',
                'short_description': 'q', 'description': 't', 'sort_order': '0',
            })
        product.refresh_from_db()
        self.assertEqual(product.name, 'Tahrirlandi')
        self.assertEqual(product.created_by, self.manager, 'muallif almashib ketdi')

    def test_boshqa_xodim_ham_tahrirlay_oladi(self):
        """Menejer va administrator barcha yozuvlarni tahrirlaydi."""
        product = self.add_product('Umumiy')
        self.client.force_login(self.other)
        url = reverse('dashboard:section_edit', args=['mahsulotlar', product.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_faqat_meniki_filtri(self):
        mine = self.add_product('Meniki')
        Product.objects.create(
            category=self.category, name='Begona', slug='begona', short_description='q',
            description='t', price=Decimal('1'), stock=1, created_by=self.other)
        html = self.client.get(
            reverse('dashboard:section_list', args=['mahsulotlar']) + '?mine=1'
        ).content.decode()
        self.assertIn(mine.name, html)
        self.assertNotIn('Begona', html)

    def test_muallif_ustuni_korinadi(self):
        self.add_product('Meniki')
        html = self.client.get(
            reverse('dashboard:section_list', args=['mahsulotlar'])).content.decode()
        self.assertIn('menejer', html)

    def test_muallifsiz_bolimda_filtr_yoq(self):
        """`created_by` maydoni yo‘q bo‘limda ortiqcha tugma chiqmasin."""
        html = self.client.get(
            reverse('dashboard:section_list', args=['kategoriyalar'])).content.decode()
        self.assertNotIn('name="mine"', html)

    def test_ish_uchun_ham_ishlaydi(self):
        self.client.post(reverse('dashboard:section_create', args=['ishlarimiz']), {
            'title': 'Yangi ish', 'slug': '', 'category': 'Baxmal',
            'excerpt': 'e', 'description': 'd', 'sort_order': '0',
            'image': tiny_image(),
        })
        self.assertEqual(Work.objects.get(title='Yangi ish').created_by, self.manager)


@NO_NETWORK
class MyProfileTests(TestCase):
    """Har bir xodim o'z profilini o'zi tahrirlaydi."""

    def setUp(self):
        self.user = make_staff('menejer', Profile.ROLE_MANAGER)
        self.client.force_login(self.user)
        self.url = reverse('dashboard:profile')

    def test_sahifa_ochiladi(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_support_ham_kira_oladi(self):
        support = make_staff('yordam', Profile.ROLE_SUPPORT)
        self.client.force_login(support)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_mehmon_kira_olmaydi(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_ism_ozgartiriladi(self):
        self.client.post(self.url, {
            'first_name': 'Sevara', 'last_name': 'Qoraqulova',
            'email': 'sevara@example.com', 'phone': '+998901112233',
            'current_password': '', 'password1': '', 'password2': '',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Sevara')
        self.assertEqual(self.user.profile.phone, '+998901112233')

    def test_parol_ozgartiriladi(self):
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': 'Parol12345!',
            'password1': 'YangiParol123', 'password2': 'YangiParol123',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('YangiParol123'))

    def test_parol_ozgargach_chiqib_ketmaydi(self):
        """Django sessiyani bekor qiladi — xodim o‘zini chiqarib yubormasin."""
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': 'Parol12345!',
            'password1': 'YangiParol123', 'password2': 'YangiParol123',
        })
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_joriy_parolsiz_ozgartirib_bolmaydi(self):
        """Ochiq qolgan sahifadan foydalanib parol almashtirilmasin."""
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': '', 'password1': 'YangiParol123',
            'password2': 'YangiParol123',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Parol12345!'))

    def test_notogri_joriy_parol_rad_etiladi(self):
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': 'xato', 'password1': 'YangiParol123',
            'password2': 'YangiParol123',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Parol12345!'))

    def test_parollar_mos_kelmasa_rad_etiladi(self):
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': 'Parol12345!', 'password1': 'YangiParol123',
            'password2': 'Boshqacha123',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Parol12345!'))

    def test_qisqa_parol_rad_etiladi(self):
        self.client.post(self.url, {
            'first_name': '', 'last_name': '', 'email': '', 'phone': '',
            'current_password': 'Parol12345!', 'password1': 'qisqa',
            'password2': 'qisqa',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Parol12345!'))

    def test_ozini_administrator_qila_olmaydi(self):
        """ENG MUHIMI: profilda rol maydoni bo‘lmasligi kerak."""
        html = self.client.get(self.url).content.decode()
        self.assertNotIn('name="role"', html)

    def test_rol_post_orqali_ham_ozgarmaydi(self):
        self.client.post(self.url, {
            'first_name': 'X', 'last_name': '', 'email': '', 'phone': '',
            'current_password': '', 'password1': '', 'password2': '',
            'role': Profile.ROLE_ADMIN,
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.role, Profile.ROLE_MANAGER)

    def test_login_ozgarmaydi(self):
        self.client.post(self.url, {
            'username': 'boshqa', 'first_name': 'X', 'last_name': '',
            'email': '', 'phone': '', 'current_password': '',
            'password1': '', 'password2': '',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'menejer')

    def test_menyuda_havola_bor(self):
        html = self.client.get(reverse('dashboard:overview')).content.decode()
        self.assertIn(self.url, html)
