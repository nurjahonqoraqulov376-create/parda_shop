"""AI yordamchi (agent) testlari.

Agent xodim nomidan bazaga yozadi, shuning uchun bu yerdagi tekshiruvlar
asosan **nima qila OLMASLIGI** haqida: ruxsat etilmagan amal, o'chirish,
begona bo'lim, tasdiqsiz yozish.

Hech bir test tarmoqqa chiqmaydi — Gemini chaqiruvi o'rniga tayyor javob
qo'yiladi.
"""

import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from catalog.models import Category, Product
from dashboard import agent, agent_run
from dashboard.models import AgentAction
from pages.models import Work

User = get_user_model()

NO_NETWORK = override_settings(AUTO_TRANSLATE=False, AI_SUPPORT=False)


class _FakeResponse:
    """`urlopen` qaytaradigan javobning eng kichik taqlidi."""

    def __init__(self, payload):
        self._payload = json.dumps(payload).encode('utf-8')

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def fake_gemini(text):
    """Gemini `generateContent` javobi shaklidagi tayyor natija."""
    return _FakeResponse({'candidates': [{'content': {'parts': [{'text': text}]}}]})


def make_staff(username, role):
    user = User.objects.create_user(username, password='Parol12345!')
    Profile.objects.create(user=user, role=role)
    return user


@NO_NETWORK
class SnapshotTests(TestCase):
    """Agent raqamlarni HAQIQIY bazadan oladi, o'ylab topmaydi."""

    def setUp(self):
        agent.cache.delete('agent:snapshot')
        self.category = Category.objects.create(name='Zebra', slug='zebra')

    def test_mahsulotlar_sanaladi(self):
        Product.objects.create(category=self.category, name='A', slug='a',
                               short_description='q', description='t',
                               price=Decimal('100000'), stock=5)
        snapshot = agent.site_snapshot()
        self.assertEqual(snapshot['katalog']['mahsulotlar'], 1)

    def test_nofaol_mahsulot_alohida(self):
        Product.objects.create(category=self.category, name='B', slug='b',
                               short_description='q', description='t',
                               price=Decimal('1'), stock=1, is_active=False)
        snapshot = agent.site_snapshot()
        self.assertEqual(snapshot['katalog']['mahsulotlar'], 0)
        self.assertEqual(snapshot['katalog']['nofaol_mahsulotlar'], 1)

    def test_ombori_kam_royxati(self):
        Product.objects.create(category=self.category, name='Kam', slug='kam',
                               short_description='q', description='t',
                               price=Decimal('1'), stock=1)
        names = [row['nomi'] for row in agent.site_snapshot()['katalog']['ombori_kam']]
        self.assertIn('Kam', names)

    def test_portfolio_sanaladi(self):
        Work.objects.create(title='Ish', slug='ish', category='x',
                            excerpt='e', description='d')
        self.assertEqual(agent.site_snapshot()['portfolio']['ishlar'], 1)

    def test_keshlanadi(self):
        first = agent.site_snapshot()
        Work.objects.create(title='Yangi', slug='yangi', category='x',
                            excerpt='e', description='d')
        self.assertEqual(agent.site_snapshot()['portfolio']['ishlar'],
                         first['portfolio']['ishlar'])


@NO_NETWORK
class AlertsTests(TestCase):
    def setUp(self):
        agent.cache.delete('agent:snapshot')

    def test_bosh_katalog_haqida_ogohlantiradi(self):
        texts = ' '.join(item['text'] for item in agent.alerts())
        self.assertIn('mahsulot', texts)

    def test_hammasi_joyida_bolsa_bitta_xabar(self):
        category = Category.objects.create(name='Z', slug='z')
        Product.objects.create(category=category, name='A', slug='a',
                               short_description='q', description='t',
                               price=Decimal('1'), stock=9)
        agent.cache.delete('agent:snapshot')
        found = agent.alerts()
        self.assertEqual([item['level'] for item in found], ['ok'])


@NO_NETWORK
class ActionParsingTests(TestCase):
    """Javobdagi amal taklifi tekshiruvdan o'tishi shart."""

    def setUp(self):
        self.admin = make_staff('boshliq', Profile.ROLE_ADMIN)

    def parse(self, payload):
        text = 'Mana javob.\n```action\n%s\n```' % json.dumps(payload, ensure_ascii=False)
        return agent.parse_action(text, self.admin)

    def test_togri_taklif_qabul_qilinadi(self):
        cleaned, action = self.parse({
            'action': 'create_category',
            'fields': {'name': 'Yangi tur'},
        })
        self.assertEqual(cleaned, 'Mana javob.')
        self.assertEqual(action['action'], 'create_category')
        self.assertEqual(action['fields']['name'], 'Yangi tur')

    def test_notanish_amal_rad_etiladi(self):
        _, action = self.parse({'action': 'delete_everything', 'fields': {}})
        self.assertIsNone(action)

    def test_ochirish_amali_umuman_yoq(self):
        """Oq ro‘yxatda o‘chirish amali bo‘lmasligi kerak."""
        for name in agent.ACTIONS:
            with self.subTest(action=name):
                self.assertNotIn('delete', name)
                self.assertNotIn('remove', name)

    def test_royxatdan_tashqari_maydon_tashlanadi(self):
        _, action = self.parse({
            'action': 'create_category',
            'fields': {'name': 'Tur', 'is_superuser': True, 'slug': 'zararli'},
        })
        self.assertEqual(set(action['fields']), {'name'})

    def test_majburiy_maydonsiz_taklif_bermaydi(self):
        _, action = self.parse({'action': 'create_product', 'fields': {'name': 'Faqat nom'}})
        self.assertIsNone(action)

    def test_buzilgan_json_yiqitmaydi(self):
        """Ichi buzilgan blok ham matndan olib tashlanishi kerak.

        Aks holda xodim javob o‘rniga xom `{...}` ni ko‘rardi.
        """
        cleaned, action = agent.parse_action('Javob\n```action\n{buzilgan\n```', self.admin)
        self.assertEqual(cleaned, 'Javob')
        self.assertIsNone(action)

    def test_yopilmagan_blok_ham_yashiriladi(self):
        """Model javobni yarim uzsa, ochiq qolgan blok ko‘rinmasin."""
        cleaned, action = agent.parse_action(
            'Javob\n```action\n{"action": "create_category"', self.admin)
        self.assertEqual(cleaned, 'Javob')
        self.assertIsNone(action)

    def test_bloksiz_javob_ham_ishlaydi(self):
        cleaned, action = agent.parse_action('Oddiy javob', self.admin)
        self.assertEqual(cleaned, 'Oddiy javob')
        self.assertIsNone(action)

    def test_xom_json_xodimga_korinmaydi(self):
        cleaned, _ = self.parse({'action': 'create_category', 'fields': {'name': 'X'}})
        self.assertNotIn('```', cleaned)
        self.assertNotIn('create_category', cleaned)


@NO_NETWORK
class RolePermissionTests(TestCase):
    """Menejer administratorgina kiradigan bo'limlarga tegolmaydi."""

    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.admin = make_staff('admin2', Profile.ROLE_ADMIN)

    def test_menejerga_mahsulot_ruxsat(self):
        self.assertIn('create_product', agent.allowed_actions(self.manager))

    def test_har_bir_amal_mavjud_bolimga_ishora_qiladi(self):
        from dashboard.registry import get_section
        for name, spec in agent.ACTIONS.items():
            with self.subTest(action=name):
                self.assertIsNotNone(get_section(spec['section']),
                                     '%s mavjud bo‘lmagan bo‘limga ishora qiladi' % name)

    def test_admin_bolimi_menejerdan_yopiq(self):
        """Admin-only bo‘limga amal qo‘shilsa, menejer uni ko‘rmasligi kerak."""
        with patch.dict(agent.ACTIONS, {'create_banner': {
            'section': 'bannerlar', 'label': 'Banner',
            'required': ('title',), 'allowed': ('title',),
        }}):
            self.assertNotIn('create_banner', agent.allowed_actions(self.manager))
            self.assertIn('create_banner', agent.allowed_actions(self.admin))

    def test_menejer_admin_bolimiga_yoza_olmaydi(self):
        with patch.dict(agent.ACTIONS, {'create_banner': {
            'section': 'bannerlar', 'label': 'Banner',
            'required': ('title',), 'allowed': ('title',),
        }}):
            with self.assertRaises(PermissionDenied):
                agent_run.execute(
                    {'action': 'create_banner', 'fields': {'title': 'X'}}, self.manager)


@NO_NETWORK
class ExecuteTests(TestCase):
    """Tasdiqlangan amal bajarilishi va jurnalga tushishi kerak."""

    def setUp(self):
        self.admin = make_staff('boshliq', Profile.ROLE_ADMIN)
        self.category = Category.objects.create(name='Zebra', slug='zebra')

    def test_kategoriya_yaratiladi(self):
        record, obj = agent_run.run_and_log(
            {'action': 'create_category', 'fields': {'name': 'Rim pardalari'}}, self.admin)
        self.assertIsNotNone(obj)
        self.assertEqual(record.status, AgentAction.STATUS_DONE)
        self.assertTrue(Category.objects.filter(name='Rim pardalari').exists())

    def test_slug_avtomatik_yasaladi(self):
        _, obj = agent_run.run_and_log(
            {'action': 'create_category', 'fields': {'name': 'Yangi Tur'}}, self.admin)
        self.assertTrue(obj.slug)

    def test_mahsulot_yaratiladi(self):
        _, obj = agent_run.run_and_log({'action': 'create_product', 'fields': {
            'name': 'Zebra parda', 'category': self.category.pk,
            'price': '250000', 'stock': 4,
            'short_description': 'qisqa', 'description': 'to‘liq',
        }}, self.admin)
        self.assertIsNotNone(obj)
        self.assertEqual(obj.price, Decimal('250000'))

    def test_mahsulot_narxi_ozgartiriladi(self):
        product = Product.objects.create(
            category=self.category, name='Eski', slug='eski',
            short_description='q', description='t', price=Decimal('100000'), stock=2)
        _, obj = agent_run.run_and_log(
            {'action': 'update_product', 'fields': {'pk': product.pk, 'price': '180000'}},
            self.admin)
        self.assertIsNotNone(obj)
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal('180000'))

    def test_ozgartirishda_boshqa_maydonlar_saqlanadi(self):
        """Faqat bitta maydon berilsa, qolganlari o‘chib ketmasligi kerak."""
        product = Product.objects.create(
            category=self.category, name='Nomi saqlansin', slug='saqlansin',
            short_description='qisqa matn', description='to‘liq matn',
            price=Decimal('100000'), stock=7)
        agent_run.run_and_log(
            {'action': 'update_product', 'fields': {'pk': product.pk, 'price': '120000'}},
            self.admin)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Nomi saqlansin')
        self.assertEqual(product.short_description, 'qisqa matn')
        self.assertEqual(product.stock, 7)

    def test_yoq_yozuvni_ozgartirib_bolmaydi(self):
        record, obj = agent_run.run_and_log(
            {'action': 'update_product', 'fields': {'pk': 999999, 'price': '1'}}, self.admin)
        self.assertIsNone(obj)
        self.assertEqual(record.status, AgentAction.STATUS_FAILED)

    def test_notogri_malumot_jurnalga_tushadi(self):
        record, obj = agent_run.run_and_log(
            {'action': 'create_product',
             'fields': {'name': 'Yomon', 'category': self.category.pk, 'price': 'narx emas'}},
            self.admin)
        self.assertIsNone(obj)
        self.assertEqual(record.status, AgentAction.STATUS_FAILED)
        self.assertTrue(record.error)

    def test_jurnalda_kim_qilgani_yoziladi(self):
        record, _ = agent_run.run_and_log(
            {'action': 'create_category', 'fields': {'name': 'Kim'}}, self.admin)
        self.assertEqual(record.user, self.admin)
        self.assertTrue(record.created_at)

    def test_notanish_amal_bajarilmaydi(self):
        record, obj = agent_run.run_and_log(
            {'action': 'drop_database', 'fields': {}}, self.admin)
        self.assertIsNone(obj)
        self.assertEqual(record.status, AgentAction.STATUS_FAILED)


@NO_NETWORK
class ViewTests(TestCase):
    """Sahifa, ruxsatlar va tasdiqlash oqimi."""

    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.support = make_staff('yordam', Profile.ROLE_SUPPORT)
        self.url = reverse('dashboard:agent')

    def test_menejer_kira_oladi(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_support_kira_olmaydi(self):
        self.client.force_login(self.support)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_mehmon_kira_olmaydi(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_javob_va_taklif_qaytadi(self):
        """Javob va taklif xodimga tasdiq uchun ko‘rsatiladi."""
        self.client.force_login(self.manager)
        action = {'action': 'create_category', 'label': 'Kategoriya',
                  'fields': {'name': 'Rim'}}
        with patch('dashboard.agent.ask',
                   return_value=('Yangi kategoriya tayyorladim.', action, None)):
            response = self.client.post(reverse('dashboard:agent_send'),
                                        {'text': 'kategoriya qo‘sh'})
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['answer'], 'Yangi kategoriya tayyorladim.')
        self.assertEqual(data['action']['label'], 'Kategoriya')
        self.assertIn('Rim', data['action']['summary'])

    def test_gemini_javobidan_taklif_ajratiladi(self):
        """Uchdan-uchgacha: Gemini javobi -> tozalangan matn + taklif.

        Tarmoqqa chiqmaydi — `urlopen` o‘rniga tayyor javob qo‘yiladi.
        """
        self.client.force_login(self.manager)
        raw = ('Yangi kategoriya tayyorladim.\n'
               '```action\n{"action": "create_category", "fields": {"name": "Rim"}}\n```')
        with patch('dashboard.agent.is_enabled', return_value=True), \
             patch('dashboard.agent.urlopen', return_value=fake_gemini(raw)):
            response = self.client.post(reverse('dashboard:agent_send'), {'text': 'qo‘sh'})
        data = response.json()
        self.assertEqual(data['answer'], 'Yangi kategoriya tayyorladim.')
        self.assertIn('Rim', data['action']['summary'])

    def test_gemini_yiqilsa_panel_ishlaydi(self):
        """Tarmoq uzilsa xodim xatolik sahifasini emas, xabarni ko‘radi."""
        self.client.force_login(self.manager)
        with patch('dashboard.agent.is_enabled', return_value=True), \
             patch('dashboard.agent.urlopen', side_effect=OSError('tarmoq yo‘q')):
            response = self.client.post(reverse('dashboard:agent_send'), {'text': 'salom'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['ok'])

    def test_javob_kelmasa_sahifa_yiqilmaydi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask', return_value=(None, None, agent.REASON_OFFLINE)):
            response = self.client.post(reverse('dashboard:agent_send'), {'text': 'salom'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['ok'])

    def test_bosh_savol_rad_etiladi(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('dashboard:agent_send'), {'text': '   '})
        self.assertEqual(response.status_code, 400)

    def test_juda_uzun_savol_rad_etiladi(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('dashboard:agent_send'), {'text': 'a' * 2100})
        self.assertEqual(response.status_code, 400)

    def test_tasdiqsiz_hech_narsa_yozilmaydi(self):
        """Taklif sessiyada tursa ham, tugma bosilmaguncha baza o‘zgarmaydi."""
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask',
                   return_value=('Tayyor', {'action': 'create_category',
                                            'label': 'Kategoriya', 'fields': {'name': 'Kutmoqda'}}, None)):
            self.client.post(reverse('dashboard:agent_send'), {'text': 'qo‘sh'})
        self.assertFalse(Category.objects.filter(name='Kutmoqda').exists())

    def test_tasdiqlangach_yoziladi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask',
                   return_value=('Tayyor', {'action': 'create_category',
                                            'label': 'Kategoriya', 'fields': {'name': 'Tasdiq'}}, None)):
            self.client.post(reverse('dashboard:agent_send'), {'text': 'qo‘sh'})
        self.client.post(reverse('dashboard:agent_run'))
        self.assertTrue(Category.objects.filter(name='Tasdiq').exists())

    def test_bekor_qilingach_yozilmaydi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask',
                   return_value=('Tayyor', {'action': 'create_category',
                                            'label': 'Kategoriya', 'fields': {'name': 'Bekor'}}, None)):
            self.client.post(reverse('dashboard:agent_send'), {'text': 'qo‘sh'})
        self.client.post(reverse('dashboard:agent_cancel'))
        self.client.post(reverse('dashboard:agent_run'))
        self.assertFalse(Category.objects.filter(name='Bekor').exists())

    def test_bir_taklif_ikki_marta_bajarilmaydi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask',
                   return_value=('Tayyor', {'action': 'create_category',
                                            'label': 'Kategoriya', 'fields': {'name': 'Bir marta'}}, None)):
            self.client.post(reverse('dashboard:agent_send'), {'text': 'qo‘sh'})
        self.client.post(reverse('dashboard:agent_run'))
        self.client.post(reverse('dashboard:agent_run'))
        self.assertEqual(Category.objects.filter(name='Bir marta').count(), 1)

    def test_nazorat_json_qaytaradi(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('dashboard:agent_pulse'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('alerts', response.json())

    def test_nazorat_support_uchun_yopiq(self):
        self.client.force_login(self.support)
        self.assertEqual(self.client.get(reverse('dashboard:agent_pulse')).status_code, 403)

    def test_suhbat_tozalanadi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask', return_value=('Javob', None, None)):
            self.client.post(reverse('dashboard:agent_send'), {'text': 'salom'})
        self.client.post(reverse('dashboard:agent_reset'))
        self.assertEqual(self.client.session.get('agent_history'), [])

    def test_menyuda_havola_bor(self):
        self.client.force_login(self.manager)
        html = self.client.get(self.url).content.decode()
        self.assertIn(self.url, html)


@NO_NETWORK
class OfflineTests(TestCase):
    """Kalit yo'q yoki tarmoq uzilgan — panel baribir ishlashi kerak."""

    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)

    @override_settings(GEMINI_API_KEY='')
    def test_kalitsiz_ochiq_qoladi(self):
        self.assertFalse(agent.is_enabled())
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('dashboard:agent')).status_code, 200)

    @override_settings(GEMINI_API_KEY='')
    def test_kalitsiz_javob_bermaydi(self):
        self.assertEqual(agent.ask('savol', self.manager),
                         (None, None, agent.REASON_OFFLINE))

    @override_settings(AI_AGENT=False, GEMINI_API_KEY='kalit')
    def test_ochirib_qoyish_mumkin(self):
        self.assertFalse(agent.is_enabled())


@NO_NETWORK
class FailureReasonTests(TestCase):
    """Nosozlikda xodim SABABNI ko‘rishi kerak.

    Ilgari har qanday nosozlikda bitta umumiy «javob bera olmadi»
    chiqardi: xodim kutish kerakmi, savolni qisqartirish kerakmi —
    bilmasdi va serverda ham sabab yozilmasdi.
    """

    def setUp(self):
        self.manager = make_staff('menejer', Profile.ROLE_MANAGER)
        self.url = reverse('dashboard:agent_send')

    def enabled(self):
        return patch('dashboard.agent.is_enabled', return_value=True)

    def http_error(self, code):
        from urllib.error import HTTPError
        return HTTPError('u', code, 'xato', {}, None)

    def test_limitda_kutish_aytiladi(self):
        with self.enabled(),              patch('dashboard.agent.time.sleep'),              patch('dashboard.agent.urlopen', side_effect=self.http_error(429)):
            answer, action, reason = agent.ask('savol', self.manager)
        self.assertEqual(reason, agent.REASON_BUSY)

    def test_limitda_bir_marta_qayta_urinadi(self):
        """Bepul tarifda daqiqalik limit tez bo‘shaydi — qayta urinish arziydi."""
        good = fake_gemini('Ikkinchi urinishda javob')
        with self.enabled(),              patch('dashboard.agent.time.sleep') as slept,              patch('dashboard.agent.urlopen',
                   side_effect=[self.http_error(503), good]):
            answer, action, reason = agent.ask('savol', self.manager)
        self.assertEqual(answer, 'Ikkinchi urinishda javob')
        self.assertIsNone(reason)
        self.assertTrue(slept.called, 'qayta urinishdan oldin kutilmadi')

    def test_boshqa_http_xatosida_qayta_urinmaydi(self):
        """400 — so‘rovning o‘zida xato; qayta yuborish foydasiz."""
        with self.enabled(),              patch('dashboard.agent.urlopen', side_effect=self.http_error(400)) as call:
            _, _, reason = agent.ask('savol', self.manager)
        self.assertEqual(reason, agent.REASON_OFFLINE)
        self.assertEqual(call.call_count, 1)

    def test_kechikish_alohida_sabab(self):
        with self.enabled(),              patch('dashboard.agent.urlopen', side_effect=TimeoutError('kech')):
            _, _, reason = agent.ask('savol', self.manager)
        self.assertEqual(reason, agent.REASON_TIMEOUT)

    def test_urlerror_ichidagi_timeout_ham_tanildi(self):
        from urllib.error import URLError
        with self.enabled(),              patch('dashboard.agent.urlopen', side_effect=URLError(TimeoutError('kech'))):
            _, _, reason = agent.ask('savol', self.manager)
        self.assertEqual(reason, agent.REASON_TIMEOUT)

    def test_chegaraga_sigmagan_javob(self):
        """`MAX_TOKENS` da matn BO‘SH keladi — buni aytish kerak."""
        payload = _FakeResponse({'candidates': [
            {'finishReason': 'MAX_TOKENS', 'content': {'parts': []}},
        ]})
        with self.enabled(), patch('dashboard.agent.urlopen', return_value=payload):
            _, _, reason = agent.ask('uzun savol', self.manager)
        self.assertEqual(reason, agent.REASON_TOO_LONG)

    def test_sabab_xodimga_matn_bolib_korinadi(self):
        self.client.force_login(self.manager)
        with patch('dashboard.agent.ask',
                   return_value=(None, None, agent.REASON_TOO_LONG)):
            response = self.client.post(self.url, {'text': 'savol'})
        data = response.json()
        from parda_shop.translations import UI
        self.assertFalse(data['ok'])
        self.assertEqual(data['answer'], UI['uz']['dash.agent_too_big'])
        self.assertNotEqual(data['answer'], UI['uz']['dash.agent_offline'])

    def test_har_bir_sabab_uchun_matn_bor(self):
        from dashboard.views import AGENT_REASON_TEXT
        from parda_shop.translations import UI
        for reason in (agent.REASON_BUSY, agent.REASON_TIMEOUT,
                       agent.REASON_TOO_LONG, agent.REASON_OFFLINE):
            with self.subTest(reason=reason):
                key = AGENT_REASON_TEXT[reason]
                self.assertIn(key, UI['uz'])
                self.assertIn(key, UI['ru'])


class SessionPersistenceTests(TestCase):
    """Panelga kirgan xodim tez-tez qayta parol so‘rashiga tushmasin."""

    def test_sirgaluvchi_muddat_yoqilgan(self):
        from django.conf import settings as django_settings
        self.assertTrue(django_settings.SESSION_SAVE_EVERY_REQUEST)

    def test_muddat_kamida_bir_hafta(self):
        from django.conf import settings as django_settings
        self.assertGreaterEqual(django_settings.SESSION_COOKIE_AGE, 60 * 60 * 24 * 7)

    def test_sessiya_bazada_saqlanadi(self):
        """Ishchi jarayonlar bir nechta — xotiradagi sessiya ular orasida yo‘qoladi."""
        from django.conf import settings as django_settings
        engine = getattr(django_settings, 'SESSION_ENGINE',
                         'django.contrib.sessions.backends.db')
        self.assertNotIn('cache', engine)

    def test_bir_necha_sahifada_kirgan_holat_saqlanadi(self):
        user = make_staff('menejer', Profile.ROLE_MANAGER)
        self.client.force_login(user)
        for path in ('dashboard:overview', 'dashboard:order_list', 'dashboard:lead_list'):
            with self.subTest(path=path):
                response = self.client.get(reverse(path))
                self.assertEqual(response.status_code, 200, 'qayta kirish so‘raldi')
