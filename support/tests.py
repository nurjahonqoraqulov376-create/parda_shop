"""Suhbat tizimi testlari — AI, eskalatsiya, ruxsatlar va cheklovlar.

Testlar hech qachon tarmoqqa chiqmasligi kerak: `AI_SUPPORT=False` bo'lsa
`ai.is_enabled()` `False` qaytaradi va Gemini chaqirilmaydi.
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from support import ai
from support.escalation import normalize, wants_operator
from support.models import Conversation, Message

User = get_user_model()

NO_AI = override_settings(AI_SUPPORT=False, AUTO_TRANSLATE=False)


def make_support(username='support1', role=Profile.ROLE_SUPPORT, email='support@example.com'):
    user = User.objects.create_user(username, email=email, password='Parol12345!')
    Profile.objects.create(user=user, role=role)
    return user


# --------------------------------------------------------------------------
# «Jonli operator» iborasini aniqlash
# --------------------------------------------------------------------------
class PhraseDetectionTests(TestCase):
    def test_ozbekcha_iboralar(self):
        for text in ('jonli operator kerak', 'Operator kerak!', 'menejer bilan gaplashmoqchiman',
                     'odam bilan gaplashsam bo‘ladimi', 'JONLI OPERATOR'):
            with self.subTest(text=text):
                self.assertTrue(wants_operator(text))

    def test_ruscha_iboralar(self):
        for text in ('нужен оператор', 'хочу с человеком поговорить', 'Живой оператор пожалуйста'):
            with self.subTest(text=text):
                self.assertTrue(wants_operator(text))

    def test_oddiy_savol_eskalatsiya_qilmaydi(self):
        for text in ('zebra parda qancha turadi?', 'yetkazib berasizmi?', 'сколько стоит?'):
            with self.subTest(text=text):
                self.assertFalse(wants_operator(text))

    def test_apostrof_turlari_bir_xil_qabul_qilinadi(self):
        """Loyihada apostrof uch xil belgida uchraydi (', ', ')."""
        self.assertEqual(normalize('bo‘ladi'), normalize("bo'ladi"))
        self.assertEqual(normalize('bo’ladi'), normalize("bo'ladi"))


# --------------------------------------------------------------------------
# Mijoz suhbati
# --------------------------------------------------------------------------
@NO_AI
class VisitorChatTests(TestCase):
    def test_xabar_saqlanadi_va_javob_qaytadi(self):
        response = self.client.post(reverse('support:send'), {'text': 'Salom, parda kerak'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(Message.objects.filter(sender='visitor').count(), 1)

    def test_ai_ochiq_bolmasa_operatorga_ulanadi(self):
        """Kalit yo'q / AI o'chiq — suhbat buzilmasin, operator chaqirilsin."""
        self.client.post(reverse('support:send'), {'text': 'Narxi qancha?'})
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.status, Conversation.STATUS_WAITING)

    def test_bosh_xabar_rad_etiladi(self):
        response = self.client.post(reverse('support:send'), {'text': '   '})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_juda_uzun_xabar_rad_etiladi(self):
        response = self.client.post(reverse('support:send'), {'text': 'a' * 1001})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_soatlik_cheklov(self):
        conversation = Conversation.objects.create(session_key='x')
        with patch('support.views.RATE_LIMIT_PER_HOUR', 2):
            self.client.post(reverse('support:send'), {'text': 'birinchi'})
            self.client.post(reverse('support:send'), {'text': 'ikkinchi'})
            response = self.client.post(reverse('support:send'), {'text': 'uchinchi'})
        self.assertEqual(response.status_code, 429)

    def test_tarix_after_bilan_yangilarini_qaytaradi(self):
        self.client.post(reverse('support:send'), {'text': 'birinchi'})
        first = Message.objects.filter(sender='visitor').first()
        self.client.post(reverse('support:send'), {'text': 'ikkinchi'})

        response = self.client.get(reverse('support:history'), {'after': first.pk})
        texts = [message['text'] for message in response.json()['messages']]
        self.assertIn('ikkinchi', texts)
        self.assertNotIn('birinchi', texts)

    def test_suhbat_boshlanmagan_bolsa_tarix_bosh(self):
        response = self.client.get(reverse('support:history'))
        self.assertEqual(response.json()['messages'], [])

    def test_get_bilan_yuborib_bolmaydi(self):
        self.assertEqual(self.client.get(reverse('support:send')).status_code, 405)


# --------------------------------------------------------------------------
# Eskalatsiya va xabar berish
# --------------------------------------------------------------------------
@NO_AI
class EscalationTests(TestCase):
    def setUp(self):
        self.operator = make_support()

    def test_kalit_ibora_operatorni_chaqiradi(self):
        self.client.post(reverse('support:send'), {'text': 'jonli operator kerak'})
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.status, Conversation.STATUS_WAITING)
        self.assertIsNotNone(conversation.escalated_at)

    def test_email_yuboriladi(self):
        self.client.post(reverse('support:send'), {'text': 'jonli operator kerak'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('support@example.com', mail.outbox[0].to)
        self.assertIn('operator', mail.outbox[0].subject.lower())

    def test_takroriy_sorov_ikkinchi_email_yubormaydi(self):
        self.client.post(reverse('support:send'), {'text': 'jonli operator kerak'})
        self.client.post(reverse('support:send'), {'text': 'operator kerak yana'})
        self.assertEqual(len(mail.outbox), 1)

    def test_email_xatosi_suhbatni_buzmaydi(self):
        """SMTP yiqilsa ham mijoz xabari saqlanishi va 200 qaytishi kerak."""
        with patch('support.notifications.send_mail', side_effect=OSError('SMTP o‘chiq')):
            response = self.client.post(reverse('support:send'), {'text': 'jonli operator kerak'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.get().status, Conversation.STATUS_WAITING)

    def test_qabul_qiluvchi_yoq_bolsa_yiqilmaydi(self):
        Profile.objects.all().delete()
        User.objects.all().delete()
        response = self.client.post(reverse('support:send'), {'text': 'jonli operator kerak'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


# --------------------------------------------------------------------------
# AI qatlami
# --------------------------------------------------------------------------
class AiLayerTests(TestCase):
    @override_settings(AI_SUPPORT=True, GEMINI_API_KEY='')
    def test_kalitsiz_ochiq_hisoblanmaydi(self):
        self.assertFalse(ai.is_enabled())

    @override_settings(AI_SUPPORT=False, GEMINI_API_KEY='kalit')
    def test_sozlama_ochirsa_ishlamaydi(self):
        self.assertFalse(ai.is_enabled())

    @override_settings(AI_SUPPORT=True, GEMINI_API_KEY='kalit')
    def test_suspend_vaqtincha_ochiradi(self):
        self.assertTrue(ai.is_enabled())
        with ai.suspend():
            self.assertFalse(ai.is_enabled())
        self.assertTrue(ai.is_enabled())

    def test_telefon_raqami_niqoblanadi(self):
        """Bepul tarifda matn Google'ga boradi — raqam yuborilmasin."""
        masked = ai.mask_personal_data('Mening raqamim +998 90 123 45 67, qo‘ng‘iroq qiling')
        self.assertNotIn('998', masked)
        self.assertIn('[telefon]', masked)

    @override_settings(AUTO_TRANSLATE=False)
    def test_tizim_korsatmasida_mavzu_cheklovi_bor(self):
        prompt = ai.build_system_prompt('uz')
        self.assertIn('FAQAT SHU DO‘KON VA SAYT MAVZUSIDA', prompt)
        self.assertIn(ai.OPERATOR_MARKER, prompt)

    @override_settings(AUTO_TRANSLATE=False)
    def test_tizim_korsatmasida_sayt_malumoti_bor(self):
        prompt = ai.build_system_prompt('uz')
        self.assertIn('Buyurtma berish', prompt)
        self.assertIn('Sayt bo‘limlari', prompt)


@override_settings(AI_SUPPORT=True, GEMINI_API_KEY='sinov-kalit', AUTO_TRANSLATE=False)
class AiResponseTests(TestCase):
    """Gemini javobi soxtalashtiriladi — tarmoqqa chiqilmaydi."""

    def _fake_response(self, text):
        payload = json.dumps({'candidates': [{'content': {'parts': [{'text': text}]}}]})

        class FakeHTTP:
            def read(self):
                return payload.encode('utf-8')

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return FakeHTTP()

    def test_oddiy_javob_qaytadi(self):
        with patch('support.ai.urlopen', return_value=self._fake_response('Zebra parda bor.')):
            text, needs_operator = ai.ask('zebra parda bormi?')
        self.assertEqual(text, 'Zebra parda bor.')
        self.assertFalse(needs_operator)

    def test_operator_belgisi_javobdan_olib_tashlanadi(self):
        answer = 'Buni aniq bilmayman. %s' % ai.OPERATOR_MARKER
        with patch('support.ai.urlopen', return_value=self._fake_response(answer)):
            text, needs_operator = ai.ask('narxi qancha?')
        self.assertNotIn(ai.OPERATOR_MARKER, text)
        self.assertTrue(needs_operator)

    def test_tarmoq_xatosi_operatorga_uzatadi(self):
        with patch('support.ai.urlopen', side_effect=OSError('tarmoq yo‘q')):
            text, needs_operator = ai.ask('salom')
        self.assertIsNone(text)
        self.assertTrue(needs_operator)

    def test_bosh_javob_operatorga_uzatadi(self):
        with patch('support.ai.urlopen', return_value=self._fake_response('   ')):
            text, needs_operator = ai.ask('salom')
        self.assertIsNone(text)
        self.assertTrue(needs_operator)

    def test_ai_javobi_suhbatga_yoziladi(self):
        with patch('support.ai.urlopen', return_value=self._fake_response('Salom! Qanday yordam beray?')):
            self.client.post(reverse('support:send'), {'text': 'salom'})
        self.assertTrue(Message.objects.filter(sender='ai').exists())
        self.assertEqual(Conversation.objects.get().status, Conversation.STATUS_BOT)

    def test_operator_ulangach_ai_javob_bermaydi(self):
        conversation = Conversation.objects.create(
            session_key='x', status=Conversation.STATUS_WITH_OPERATOR,
        )
        session = self.client.session
        session.save()
        conversation.session_key = session.session_key
        conversation.save(update_fields=['session_key'])

        with patch('support.ai.urlopen') as fake:
            self.client.post(reverse('support:send'), {'text': 'yana savol'})
        fake.assert_not_called()
        self.assertFalse(Message.objects.filter(sender='ai').exists())
