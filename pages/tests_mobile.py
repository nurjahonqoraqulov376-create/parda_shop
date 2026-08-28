"""Telefon (Android / iPhone) uchun moslashuv testlari.

Bu yerdagi tekshiruvlar brauzersiz ishlaydi: sahifaning HTML kodi va CSS
faylida telefon uchun zarur bo'lgan narsalar bor-yo'qligini qo'riqlaydi.
Kimdir keyinchalik ularni tasodifan o'chirib yuborsa, test qizil bo'ladi.
"""

import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Product

STYLE_CSS = Path(settings.BASE_DIR) / 'static' / 'css' / 'style.css'
DASHBOARD_CSS = Path(settings.BASE_DIR) / 'static' / 'css' / 'dashboard.css'
MAIN_JS = Path(settings.BASE_DIR) / 'static' / 'js' / 'main.js'


def read(path):
    return path.read_text(encoding='utf-8')


@override_settings(AUTO_TRANSLATE=False)
class ViewportTests(TestCase):
    def setUp(self):
        self.html = self.client.get(reverse('pages:home')).content.decode('utf-8')

    def test_viewport_mavjud(self):
        self.assertIn('width=device-width', self.html)

    def test_iphone_notch_uchun_viewport_fit(self):
        """`viewport-fit=cover` bo'lmasa `env(safe-area-inset-*)` doim 0 qaytaradi."""
        self.assertIn('viewport-fit=cover', self.html)

    def test_kattalashtirish_bloklanmagan(self):
        """`user-scalable=no` ko'zi ojiz foydalanuvchilarga to'siq bo'ladi."""
        self.assertNotIn('user-scalable=no', self.html)
        self.assertNotIn('maximum-scale=1', self.html)

    def test_brauzer_rangi_fon_bilan_mos(self):
        """Telefon manzil satri rangi sayt foni bilan bir xil bo'lsin."""
        self.assertIn('name="theme-color"', self.html)
        css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
        light = re.search(r':root \{[^}]*?--bg: *(#[0-9a-fA-F]+)', css, re.S)
        dark = re.search(r':root\[data-theme="dark"\] \{[^}]*?--bg: *(#[0-9a-fA-F]+)', css, re.S)
        self.assertIn(light.group(1), self.html, 'yorug‘ rejim rangi mos emas')
        self.assertIn(dark.group(1), self.html, 'tungi rejim rangi mos emas')


@override_settings(AUTO_TRANSLATE=False)
class MobileMarkupTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Zebra parda', slug='zebra', short_description='q', description='t',
            price=Decimal('100000'), stock=5,
        )

    def test_savat_jadvalida_ustun_nomlari_bor(self):
        """Telefonda jadval kartochkaga aylanadi — ustun nomi `data-label` dan olinadi."""
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 1, 'price': '100000'}}
        session.save()
        html = self.client.get(reverse('orders:cart_detail')).content.decode('utf-8')
        self.assertEqual(html.count('data-label='), 3)

    def test_miqdor_maydonida_raqamli_klaviatura(self):
        html = self.client.get(self.product.get_absolute_url()).content.decode('utf-8')
        self.assertIn('inputmode="numeric"', html)

    def test_telefon_maydonida_tel_klaviatura(self):
        html = self.client.get(reverse('pages:home')).content.decode('utf-8')
        self.assertIn('inputmode="tel"', html)
        self.assertIn('autocomplete="tel"', html)

    def test_buyurtma_formasida_mobil_atributlar(self):
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 1, 'price': '100000'}}
        session.save()
        html = self.client.get(reverse('orders:checkout')).content.decode('utf-8')
        self.assertIn('inputmode="tel"', html)
        self.assertIn('autocomplete="name"', html)

    def test_menyu_tugmasi_bor(self):
        html = self.client.get(reverse('pages:home')).content.decode('utf-8')
        self.assertIn('data-menu-toggle', html)

    def test_rasmlar_olchamga_moslashadi(self):
        """`width`/`height` bo'lmasa rasm yuklanguncha sahifa sakraydi (CLS)."""
        html = self.client.get(reverse('pages:home')).content.decode('utf-8')
        for tag in re.findall(r'<img[^>]*>', html):
            if 'src=' not in tag:
                continue
            with self.subTest(tag=tag[:70]):
                self.assertIn('width=', tag)
                self.assertIn('height=', tag)


class MobileStyleTests(TestCase):
    """CSS'dagi telefon uchun kritik qoidalar joyida turibdimi."""

    def setUp(self):
        self.css = read(STYLE_CSS)

    def test_ios_zoomni_toxtatuvchi_shrift(self):
        """iOS maydon shrifti 16px dan kichik bo'lsa sahifani kattalashtiradi."""
        self.assertIn('@media (pointer: coarse)', self.css)
        coarse = self.css.split('@media (pointer: coarse)', 1)[1]
        self.assertIn('font-size: 16px', coarse)

    def test_gorizontal_siljish_yopilgan(self):
        self.assertIn('overflow-x: clip', self.css)

    def test_safe_area_hisobga_olingan(self):
        self.assertIn('env(safe-area-inset-left)', self.css)
        self.assertIn('env(safe-area-inset-bottom)', self.css)

    def test_bosish_chaqnashi_ochirilgan(self):
        self.assertIn('-webkit-tap-highlight-color', self.css)
        self.assertIn('touch-action: manipulation', self.css)

    def test_savat_kartochka_korinishi(self):
        self.assertIn('.cart-table thead { display: none; }', self.css)

    def test_katalog_menyusi_bosish_bilan_ochiladi(self):
        self.assertIn('.has-mega.is-open .mega', self.css)

    def test_qavslar_balansda(self):
        for path in (STYLE_CSS, DASHBOARD_CSS):
            with self.subTest(path=path.name):
                css = read(path)
                self.assertEqual(css.count('{'), css.count('}'))

    def test_dashboard_ham_moslashgan(self):
        dash = read(DASHBOARD_CSS)
        self.assertIn('@media (pointer: coarse)', dash)
        self.assertIn('font-size: 16px', dash)


class MobileScriptTests(TestCase):
    def setUp(self):
        self.js = read(MAIN_JS)

    def test_ios_uchun_surish_qulfi(self):
        """iOS'da `body { overflow: hidden }` orqa fonni ushlab tura olmaydi."""
        self.assertIn('function lockScroll', self.js)
        self.assertIn("position = 'fixed'", self.js)
        self.assertNotIn("document.body.style.overflow = 'hidden'", self.js)

    def test_bildirishnoma_takrorlanmaydi(self):
        """Ilgari har 15 soniyada qayta chiqib, o'qishga imkon bermasdi."""
        self.assertIn('PROMO_DELAY', self.js)
        self.assertNotIn('}, 15000)', self.js)

    def test_slayderda_swipe_bor(self):
        self.assertIn("addEventListener('touchstart'", self.js)
        self.assertIn("addEventListener('touchend'", self.js)

    def test_menyu_holati_elon_qilinadi(self):
        self.assertIn('aria-expanded', self.js)


class SupportWidgetTests(TestCase):
    """Suhbat oynasining dizayni va xatti-harakati."""

    def setUp(self):
        self.js = read(MAIN_JS.parent / 'support.js')
        self.css = read(STYLE_CSS)

    def test_xabar_ikki_marta_chiqmaydi(self):
        """Optimistik pufakcha serverdan javob kelgach olib tashlanishi shart.

        Ilgari xabar id'siz qo'shilardi, keyin server uni id bilan qaytarardi va
        `addMessage` faqat id bo'yicha tekshirgani uchun xabar ikki marta
        ko'rinardi.
        """
        self.assertIn('function dropPending', self.js)
        self.assertIn('dropPending()', self.js)
        self.assertIn("dataset.pending", self.js)
        self.assertIn('[data-pending]', self.css)

    def test_matn_html_sifatida_talqin_qilinmaydi(self):
        """XSS: mijoz yozgan matn `textContent` orqali qo'yiladi."""
        self.assertIn('bubble.textContent', self.js)
        self.assertNotIn('innerHTML = message', self.js)

    def test_yozmoqda_koresatkichi_bor(self):
        self.assertIn('function showTyping', self.js)
        self.assertIn('.sc-typing', self.css)

    def test_yuborish_tugmasi_bosh_matnda_ochiq_emas(self):
        self.assertIn('function syncSendButton', self.js)
        self.assertIn('.sc-send:disabled', self.css)

    def test_telefonda_toliq_ekran_va_16px(self):
        self.assertIn('100dvh', self.css)
        coarse = self.css.rsplit('@media (pointer: coarse)', 1)[1]
        self.assertIn('.sc-input { font-size: 16px; }', coarse)

    def test_ingichka_aylantirgich(self):
        self.assertIn('.sc-log::-webkit-scrollbar', self.css)

    def test_telefonda_ixcham_doira_tugma(self):
        """Tugma butun kenglikni egallab, sahifa pastini to'sib turardi."""
        mobile = self.css.split('Telefon: ixcham doira', 1)[1].split('@supports', 1)[0]
        self.assertIn('border-radius: 50%', mobile)
        self.assertIn('.sc-fab-text { display: none; }', mobile)
        self.assertNotIn('width: 100%', mobile.split('.sc-panel', 1)[0])

    def test_tugma_safe_area_ustida(self):
        """iPhone pastki chizig'i tugmani bosib qo'ymasin."""
        self.assertIn('calc(18px + env(safe-area-inset-bottom))', self.css)

    def test_yozishma_foni_bor(self):
        log = self.css.split('.sc-log {', 1)[1].split('}', 1)[0]
        self.assertIn('background-image', log)
        # Fon tokenlardan olinadi — tungi rejimda o'zi moslashadi.
        self.assertIn('var(--accent-soft)', log)
        self.assertIn('var(--line)', log)
