"""Yordamchiga rasm biriktirish.

Portfolio ishi rasmsiz saqlanmaydi, ya'ni yordamchi uni umuman qo'sha
olmasdi. Endi xodim suratni chatga biriktiradi: yordamchi uni ko'rib
tavsif yozadi, tasdiqlangach rasm yozuvga o'tadi.

Hech bir test tarmoqqa chiqmaydi.
"""

import io
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from dashboard import agent, agent_run, agent_uploads
from pages.models import Work

User = get_user_model()


def picture(size=(600, 400), fmt='JPEG', name=None):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', size, (190, 150, 120)).save(buffer, fmt)
    suffix = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[fmt]
    return SimpleUploadedFile(name or ('parda.%s' % suffix), buffer.getvalue(),
                              content_type='image/%s' % suffix)


class MediaRoot(TestCase):
    """Har bir test o'z vaqtinchalik `media/` papkasida ishlaydi."""

    def setUp(self):
        super().setUp()
        self.media = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, True)
        self.override = override_settings(
            MEDIA_ROOT=str(self.media), AUTO_TRANSLATE=False, AI_SUPPORT=False)
        self.override.enable()
        self.addCleanup(self.override.disable)


class UploadValidationTests(MediaRoot):
    """Yuklangan faylni sarlavhasiga emas, ochib ko'rib tekshiramiz."""

    def test_haqiqiy_rasm_qabul_qilinadi(self):
        name, data = agent_uploads.stash(picture())
        self.assertTrue(name.startswith('agent_tmp/'))
        self.assertTrue(data)

    def test_rasm_diskka_yoziladi(self):
        name, _ = agent_uploads.stash(picture())
        self.assertTrue((self.media / name).exists())

    def test_rasm_emas_rad_etiladi(self):
        fake = SimpleUploadedFile('zararli.jpg', b'bu rasm emas',
                                  content_type='image/jpeg')
        with self.assertRaises(agent_uploads.UploadError):
            agent_uploads.stash(fake)

    def test_sarlavhaga_ishonilmaydi(self):
        """`Content-Type` ni yuboruvchi o‘zi yozadi — unga ishonib bo‘lmaydi."""
        script = SimpleUploadedFile('rasm.jpg', b'<?php echo 1; ?>',
                                    content_type='image/jpeg')
        with self.assertRaises(agent_uploads.UploadError):
            agent_uploads.stash(script)

    def test_juda_katta_fayl_rad_etiladi(self):
        big = picture()
        big.size = agent_uploads.MAX_BYTES + 1
        with self.assertRaises(agent_uploads.UploadError):
            agent_uploads.stash(big)

    def test_png_va_webp_qabul_qilinadi(self):
        for fmt in ('PNG', 'WEBP'):
            with self.subTest(fmt=fmt):
                name, _ = agent_uploads.stash(picture(fmt=fmt))
                self.assertTrue(name)

    def test_ochirish_ishlaydi(self):
        name, _ = agent_uploads.stash(picture())
        agent_uploads.discard(name)
        self.assertFalse((self.media / name).exists())

    def test_begona_yolni_ochirmaydi(self):
        """`discard` faqat o‘z papkasiga tegsin."""
        victim = self.media / 'works' / 'muhim.jpg'
        victim.parent.mkdir(parents=True, exist_ok=True)
        victim.write_bytes(b'muhim')
        agent_uploads.discard('works/muhim.jpg')
        self.assertTrue(victim.exists(), 'begona fayl o‘chirildi!')

    def test_begona_yolni_ochmaydi(self):
        self.assertIsNone(agent_uploads.load('works/muhim.jpg'))

    def test_eski_fayllar_tozalanadi(self):
        import os
        import time
        name, _ = agent_uploads.stash(picture())
        old = self.media / name
        past = time.time() - agent_uploads.MAX_AGE.total_seconds() - 60
        os.utime(old, (past, past))
        agent_uploads.purge_old()
        self.assertFalse(old.exists())

    def test_yangi_fayl_tozalanmaydi(self):
        name, _ = agent_uploads.stash(picture())
        agent_uploads.purge_old()
        self.assertTrue((self.media / name).exists())


class RequestBodyTests(TestCase):
    """Rasm Gemini so'roviga qo'shiladimi."""

    def test_rasm_qism_sifatida_ketadi(self):
        body = agent._request_body('tizim', [], 'savol', (b'baytlar', 'JPEG'))
        kinds = [list(part)[0] for part in body['contents'][0]['parts']]
        self.assertEqual(kinds, ['text', 'inlineData'])

    def test_mime_togri(self):
        for fmt, mime in (('JPEG', 'image/jpeg'), ('PNG', 'image/png'),
                          ('WEBP', 'image/webp')):
            with self.subTest(fmt=fmt):
                body = agent._request_body('t', [], 's', (b'x', fmt))
                self.assertEqual(
                    body['contents'][0]['parts'][1]['inlineData']['mimeType'], mime)

    def test_rasmsiz_ortiqcha_qism_yoq(self):
        body = agent._request_body('tizim', [], 'savol')
        self.assertEqual(len(body['contents'][0]['parts']), 1)

    def test_korsatmada_rasm_qoidasi_bor(self):
        user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=user, role=Profile.ROLE_MANAGER)
        prompt = agent.build_system_prompt(user)
        self.assertIn('RASM', prompt)
        self.assertIn('O‘YLAB TOPMA', prompt)


class ExecuteWithImageTests(MediaRoot):
    """Tasdiqlangach rasm yozuvga biriktiriladi."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=self.user, role=Profile.ROLE_MANAGER)

    def test_rasm_maydonini_topadi(self):
        self.assertEqual(agent_run.image_field_name(Work), 'image')

    def test_rasmsiz_modelda_none(self):
        from support.models import Conversation
        self.assertIsNone(agent_run.image_field_name(Conversation))

    def test_ish_rasm_bilan_yaratiladi(self):
        name, _ = agent_uploads.stash(picture())
        with agent_uploads.load(name) as handle:
            record, obj = agent_run.run_and_log(
                {'action': 'create_work', 'label': 'Ish',
                 'fields': {'title': 'Mehmonxona pardasi', 'category': 'Baxmal',
                            'excerpt': 'qisqa', 'description': 'to‘liq'}},
                self.user, handle)
        self.assertIsNotNone(obj, record.error)
        self.assertTrue(obj.image.name)
        self.assertTrue((self.media / obj.image.name).exists())

    def test_rasmsiz_ish_yaratilmaydi(self):
        """Portfolio ishi rasmsiz saqlanmaydi — sabab jurnalga tushsin."""
        record, obj = agent_run.run_and_log(
            {'action': 'create_work', 'label': 'Ish',
             'fields': {'title': 'Rasmsiz', 'category': 'x',
                        'excerpt': 'e', 'description': 'd'}},
            self.user, None)
        self.assertIsNone(obj)
        self.assertIn('image', record.error)

    def test_mahsulot_ham_rasm_oladi(self):
        from catalog.models import Category
        category = Category.objects.create(name='Zebra', slug='zebra')
        name, _ = agent_uploads.stash(picture())
        with agent_uploads.load(name) as handle:
            _, obj = agent_run.run_and_log(
                {'action': 'create_product', 'label': 'Mahsulot',
                 'fields': {'name': 'Zebra parda', 'category': category.pk,
                            'price': '250000', 'short_description': 'q',
                            'description': 't'}},
                self.user, handle)
        self.assertIsNotNone(obj)
        self.assertTrue(obj.image.name)


class AgentImageViewTests(MediaRoot):
    """Chatdan rasm yuborish va tasdiqlash oqimi."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('menejer', password='Parol12345!')
        Profile.objects.create(user=self.user, role=Profile.ROLE_MANAGER)
        self.client.force_login(self.user)
        self.send_url = reverse('dashboard:agent_send')

    def send(self, text='pardaga ish qo‘sh', image=None, action=None):
        payload = {'text': text}
        if image is not None:
            payload['image'] = image
        with patch('dashboard.agent.ask', return_value=('Tayyor', action, None)):
            return self.client.post(self.send_url, payload)

    def work_action(self):
        return {'action': 'create_work', 'label': 'Ish',
                'fields': {'title': 'Yangi ish', 'category': 'Baxmal',
                           'excerpt': 'e', 'description': 'd'}}

    def test_rasm_qabul_qilinadi(self):
        response = self.send(image=picture())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['has_image'])

    def test_rasm_sessiyada_saqlanadi(self):
        self.send(image=picture())
        self.assertTrue(self.client.session.get('agent_pending_image'))

    def test_buzuq_rasm_tushunarli_xato_beradi(self):
        bad = SimpleUploadedFile('x.jpg', b'rasm emas', content_type='image/jpeg')
        response = self.send(image=bad)
        self.assertEqual(response.status_code, 400)
        self.assertIn('rasm', response.json()['error'].lower())

    def test_faqat_rasm_yuborsa_ham_boladi(self):
        """Matnsiz, faqat surat — «buni portfolioga qo‘sh» degani."""
        response = self.send(text='', image=picture())
        self.assertEqual(response.status_code, 200)

    def test_matnsiz_va_rasmsiz_rad_etiladi(self):
        response = self.send(text='')
        self.assertEqual(response.status_code, 400)

    def test_tasdiqlangach_ish_rasm_bilan_yaratiladi(self):
        self.send(image=picture(), action=self.work_action())
        self.client.post(reverse('dashboard:agent_run'))
        work = Work.objects.get(title='Yangi ish')
        self.assertTrue(work.image.name)
        self.assertTrue((self.media / work.image.name).exists())

    def test_tasdiqlangach_vaqtinchalik_nusxa_ochiriladi(self):
        self.send(image=picture(), action=self.work_action())
        stored = self.client.session['agent_pending_image']
        self.client.post(reverse('dashboard:agent_run'))
        self.assertFalse((self.media / stored).exists())

    def test_bekor_qilinsa_rasm_ochiriladi(self):
        self.send(image=picture(), action=self.work_action())
        stored = self.client.session['agent_pending_image']
        self.client.post(reverse('dashboard:agent_cancel'))
        self.assertFalse((self.media / stored).exists())

    def test_tozalansa_rasm_ochiriladi(self):
        self.send(image=picture(), action=self.work_action())
        stored = self.client.session['agent_pending_image']
        self.client.post(reverse('dashboard:agent_reset'))
        self.assertFalse((self.media / stored).exists())

    def test_yangi_rasm_eskisini_almashtiradi(self):
        self.send(image=picture())
        first = self.client.session['agent_pending_image']
        self.send(image=picture())
        self.assertFalse((self.media / first).exists(), 'eski rasm qolib ketdi')

    def test_sahifada_rasm_korinadi(self):
        self.send(image=picture(), action=self.work_action())
        html = self.client.get(reverse('dashboard:agent')).content.decode()
        self.assertIn('agent_tmp/', html)

    def test_biriktirish_tugmasi_bor(self):
        html = self.client.get(reverse('dashboard:agent')).content.decode()
        self.assertIn('data-agent-image', html)

    def test_support_rasm_yubora_olmaydi(self):
        support = User.objects.create_user('yordam', password='Parol12345!')
        Profile.objects.create(user=support, role=Profile.ROLE_SUPPORT)
        self.client.force_login(support)
        response = self.client.post(self.send_url, {'text': 'x', 'image': picture()})
        self.assertEqual(response.status_code, 403)
