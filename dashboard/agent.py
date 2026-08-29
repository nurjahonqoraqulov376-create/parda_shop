"""Boshqaruv paneli uchun AI yordamchi (agent).

Nima qiladi
-----------
1. **Savolga javob beradi** — saytdagi HAQIQIY holatdan: nechta buyurtma
   keldi, qaysi mahsulot tugayapti, javobsiz suhbat bormi va h.k.
2. **Qo'shishda yordam beradi** — mahsulot, kategoriya yoki ish (portfolio)
   uchun tayyor matn tuzib beradi va uni yozib qo'yishni **taklif qiladi**.
3. **Nazorat qilib turadi** — saytdagi diqqat talab qiladigan narsalarni
   (kutayotgan suhbat, javobsiz so'rov, tugagan ombor) ro'yxatlab beradi.

Xavfsizlik qoidalari
--------------------
* Agent hech narsani **o'zi yozmaydi**. U faqat amalni *taklif qiladi*;
  xodim tasdiqlagandan keyingina bajariladi (`execute`).
* Amallar **oq ro'yxat** bilan chegaralangan: faqat qo'shish va bir nechta
  xavfsiz o'zgartirish. **O'chirish yo'q.**
* Har bir yozuv panelning o'z formasidan o'tadi — tekshiruvlar bir xil.
* Menejer administratorgina kira oladigan bo'limlarga tegolmaydi.
* Bajarilgan har bir amal `AgentAction` jadvaliga yoziladi: kim, qachon, nima.

`support/ai.py` bilan bir xil yondashuv: qo'shimcha kutubxona yo'q, faqat
`urllib`. Tarmoq yo'q bo'lsa yoki javob buzilgan bo'lsa agent jim qoladi —
panel ishlashdan to'xtamaydi.
"""

import json
import logging
import re
import socket
import time
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone

from accounts.permissions import has_role
from support.ai import _extract_text, api_key  # bir xil Gemini mijozi

logger = logging.getLogger(__name__)

ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

# Javob ichidagi amal taklifi shu blokda keladi.
#
# Blok ICHI qanday bo'lishidan qat'i nazar tutiladi va matndan olib
# tashlanadi: ichi buzilgan bo'lsa ham xodimga xom `{...}` ko'rinmasligi
# kerak. To'g'ri JSON ekani keyin alohida tekshiriladi.
ACTION_RE = re.compile(r'```action\b\s*(.*?)(?:```|$)', re.DOTALL)

HISTORY_LIMIT = 10
SNAPSHOT_CACHE_SECONDS = 30

# Ruxsat etilgan amallar. `section` — `dashboard/registry.py` dagi kalit;
# ruxsat o'sha yerdagi `admin_only` bo'yicha tekshiriladi.
# DIQQAT: bu yerda o'chirish amali YO'Q va bo'lmasligi ham kerak.
ACTIONS = {
    'create_product': {
        'section': 'mahsulotlar',
        'label': 'Yangi mahsulot qo‘shish',
        'required': ('name', 'category', 'price'),
        'allowed': ('name', 'category', 'price', 'stock', 'short_description',
                    'description', 'sku', 'is_active', 'is_featured'),
    },
    'create_category': {
        'section': 'kategoriyalar',
        'label': 'Yangi kategoriya qo‘shish',
        'required': ('name',),
        'allowed': ('name', 'description', 'icon', 'sort_order',
                    'show_on_home', 'is_active'),
    },
    'create_work': {
        'section': 'ishlarimiz',
        'label': 'Portfolio‘ga yangi ish qo‘shish',
        'required': ('title',),
        'allowed': ('title', 'category', 'excerpt', 'description',
                    'sort_order', 'is_active'),
    },
    'update_product': {
        'section': 'mahsulotlar',
        'label': 'Mahsulotni o‘zgartirish',
        'required': ('pk',),
        'allowed': ('pk', 'price', 'stock', 'is_active', 'is_featured',
                    'short_description', 'description'),
    },
}


def is_enabled():
    """Agent shu paytda javob bera oladimi?"""
    if not getattr(settings, 'AI_AGENT', True):
        return False
    return bool(api_key())


# --------------------------------------------------------------------------
# Saytdagi jonli holat
# --------------------------------------------------------------------------

def site_snapshot():
    """Saytda hozir nima bo'layotgani — agent shu ma'lumotdan javob beradi.

    Qisqa vaqtga keshlanadi: bir suhbatdagi ketma-ket savollar bazani
    qayta-qayta qiynamasin.
    """
    cached = cache.get('agent:snapshot')
    if cached is not None:
        return cached

    from catalog.models import Category, Product
    from orders.models import Lead, Order
    from pages.models import Work
    from support.models import Conversation

    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    orders = Order.objects.all()
    by_status = dict(
        orders.values_list('status').annotate(total=Count('id')).values_list('status', 'total')
    )
    revenue = orders.filter(created_at__gte=week_ago).aggregate(
        total=Sum('total_amount'))['total']

    low_stock = list(
        Product.objects.filter(is_active=True, stock__lte=3)
        .order_by('stock')
        .values_list('name', 'stock')[:10]
    )

    snapshot = {
        'sana': str(today),
        'buyurtmalar': {
            'jami': orders.count(),
            'bugun': orders.filter(created_at__date=today).count(),
            'hafta': orders.filter(created_at__gte=week_ago).count(),
            'holat_boyicha': by_status,
            'haftalik_summa': int(revenue or 0),
        },
        'sorovlar': {
            'jami': Lead.objects.count(),
            'yangi': Lead.objects.filter(status='new').count(),
            'bugun': Lead.objects.filter(created_at__date=today).count(),
        },
        'suhbatlar': {
            'operator_kutayotgan': Conversation.objects.filter(status=Conversation.STATUS_WAITING).count(),
            'operator_bilan': Conversation.objects.filter(status=Conversation.STATUS_WITH_OPERATOR).count(),
            'bugun': Conversation.objects.filter(created_at__date=today).count(),
        },
        'katalog': {
            'kategoriyalar': Category.objects.filter(is_active=True).count(),
            'mahsulotlar': Product.objects.filter(is_active=True).count(),
            'nofaol_mahsulotlar': Product.objects.filter(is_active=False).count(),
            'ombori_tugagan': Product.objects.filter(is_active=True, stock=0).count(),
            'ombori_kam': [{'nomi': name, 'qoldiq': stock} for name, stock in low_stock],
        },
        'portfolio': {
            'ishlar': Work.objects.filter(is_active=True).count(),
        },
    }
    cache.set('agent:snapshot', snapshot, SNAPSHOT_CACHE_SECONDS)
    return snapshot


def alerts():
    """Diqqat talab qiladigan narsalar — panel yuqorisidagi nazorat qatori."""
    snapshot = site_snapshot()
    found = []

    waiting = snapshot['suhbatlar']['operator_kutayotgan']
    if waiting:
        found.append({'level': 'urgent', 'text': '%d ta suhbat operatorni kutyapti' % waiting})

    new_leads = snapshot['sorovlar']['yangi']
    if new_leads:
        found.append({'level': 'warn', 'text': '%d ta so‘rovga javob berilmagan' % new_leads})

    new_orders = snapshot['buyurtmalar']['holat_boyicha'].get('new', 0)
    if new_orders:
        found.append({'level': 'warn', 'text': '%d ta yangi buyurtma kutyapti' % new_orders})

    empty = snapshot['katalog']['ombori_tugagan']
    if empty:
        found.append({'level': 'warn', 'text': '%d ta mahsulotning ombori tugagan' % empty})

    if not snapshot['katalog']['mahsulotlar']:
        found.append({'level': 'urgent', 'text': 'Katalogda birorta ham aktiv mahsulot yo‘q'})

    if not found:
        found.append({'level': 'ok', 'text': 'Hammasi joyida — kutayotgan ish yo‘q'})
    return found


# --------------------------------------------------------------------------
# Tizim ko'rsatmasi
# --------------------------------------------------------------------------

def allowed_actions(user):
    """Foydalanuvchi roli uchun ruxsat etilgan amallar."""
    from .registry import get_section

    names = []
    for name, spec in ACTIONS.items():
        section = get_section(spec['section'])
        if section is None:
            continue
        if section['admin_only'] and not has_role(user, 'admin'):
            continue
        names.append(name)
    return names


def build_system_prompt(user):
    names = allowed_actions(user)
    catalog = [
        '%s — %s (majburiy: %s; ruxsat etilgan: %s)'
        % (name, ACTIONS[name]['label'],
           ', '.join(ACTIONS[name]['required']),
           ', '.join(ACTIONS[name]['allowed']))
        for name in names
    ]
    role = 'administrator' if has_role(user, 'admin') else 'menejer'

    return (
        'Sen «Sevara Design» parda do‘koni saytining boshqaruv panelidagi '
        'yordamchisan. Suhbatdoshing — saytning %(role)si (%(name)s).\n\n'
        'HOZIRGI HOLAT (JSON, real vaqtda olingan):\n%(state)s\n\n'
        'QOIDALAR:\n'
        '1. Faqat shu sayt va do‘kon ishi haqida gaplash. Boshqa mavzu '
        'so‘ralsa muloyim rad et.\n'
        '2. Raqamlarni FAQAT yuqoridagi holatdan ol. O‘ylab topma. '
        'Ma’lumot yetishmasa — ochiq ayt.\n'
        '3. Javobing qisqa va aniq bo‘lsin, o‘zbek tilida.\n'
        '4. Xodim biror narsa QO‘SHISHNI yoki O‘ZGARTIRISHNI so‘rasa, javob '
        'oxiriga quyidagi blokni qo‘sh:\n'
        '```action\n{"action": "<nomi>", "fields": {...}}\n```\n'
        'Ruxsat etilgan amallar:\n%(actions)s\n'
        '5. Amalni O‘ZING bajarmaysan — blok faqat TAKLIF. Xodim tugmani '
        'bosgandan keyin tizim o‘zi yozadi. Shuni matnda ham ayt.\n'
        '6. Majburiy maydon yetishmasa blok yozma — avval so‘rab ol.\n'
        '7. Narx va o‘lchamni O‘YLAB TOPMA. Xodim aytmasa, so‘ra.\n'
        '8. Hech narsani O‘CHIRA olmaysan. O‘chirish so‘ralsa, buni '
        'paneldan qo‘lda qilish kerakligini ayt.\n'
        '9. Matn yozib berayotganda (tavsif, sarlavha) o‘zbekcha yoz — '
        'ruschasini tizim o‘zi tarjima qiladi.'
    ) % {
        'role': role,
        'name': user.get_username(),
        'state': json.dumps(site_snapshot(), ensure_ascii=False, indent=1),
        'actions': '\n'.join('   - %s' % line for line in catalog) or '   (yo‘q)',
    }


# --------------------------------------------------------------------------
# Amal taklifi
# --------------------------------------------------------------------------

def parse_action(text, user):
    """Javobdagi ```action``` blokini oladi va tekshiradi.

    `(tozalangan_matn, amal|None)` qaytaradi. Blok noto'g'ri bo'lsa
    jimgina tashlab yuboriladi — xodimga xom JSON ko'rsatilmaydi.
    """
    match = ACTION_RE.search(text or '')
    if not match:
        return (text or '').strip(), None

    cleaned = ACTION_RE.sub('', text).strip()
    try:
        raw = json.loads(match.group(1))
    except ValueError:
        logger.warning('Agent buzilgan action bloki yubordi')
        return cleaned, None

    name = raw.get('action')
    spec = ACTIONS.get(name)
    if spec is None or name not in allowed_actions(user):
        logger.warning('Agent ruxsat etilmagan amal so‘radi: %s', name)
        return cleaned, None

    fields = raw.get('fields')
    if not isinstance(fields, dict):
        return cleaned, None

    # Faqat oq ro'yxatdagi maydonlar o'tadi.
    fields = {key: value for key, value in fields.items() if key in spec['allowed']}
    missing = [key for key in spec['required'] if not str(fields.get(key, '')).strip()]
    if missing:
        logger.info('Agent taklifida maydon yetishmadi: %s', missing)
        return cleaned, None

    return cleaned, {'action': name, 'label': spec['label'], 'fields': fields}


# --------------------------------------------------------------------------
# So'rov
# --------------------------------------------------------------------------

def _request_body(system_prompt, history, question):
    contents = []
    for role, text in history[-HISTORY_LIMIT:]:
        contents.append({
            'role': 'model' if role == 'agent' else 'user',
            'parts': [{'text': text}],
        })
    contents.append({'role': 'user', 'parts': [{'text': question}]})
    return {
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'contents': contents,
        'generationConfig': {
            'temperature': 0.3,
            'maxOutputTokens': getattr(settings, 'AI_AGENT_MAX_TOKENS', 900),
        },
    }


# Xodimga ko'rsatiladigan sabab. Oldin har qanday nosozlikda bitta umumiy
# xabar chiqardi va nima bo'lganini bilishning iloji yo'q edi.
REASON_BUSY = 'busy'          # kvota/limit — biroz kutish kerak
REASON_TIMEOUT = 'timeout'    # javob kechikdi
REASON_TOO_LONG = 'too_long'  # javob chegaraga sig'madi
REASON_OFFLINE = 'offline'    # tarmoq yoki kalit muammosi

# Vaqtinchalik nosozliklarda bir marta qayta urinamiz.
RETRY_STATUSES = (429, 500, 502, 503, 504)
RETRY_DELAY_SECONDS = 2.0


def _call_gemini(body, timeout):
    """Gemini'ga so'rov yuboradi.

    `(javob_json, sabab)` qaytaradi. Muvaffaqiyatda sabab `None`.
    """
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-3.5-flash-lite')
    url = '%s?key=%s' % (ENDPOINT.format(model=model), api_key())
    request = Request(url, data=body.encode('utf-8'),
                      headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8')), None
    except HTTPError as exc:
        # Xato matnini ham yozamiz — aks holda serverda sababni topib bo'lmaydi.
        detail = ''
        try:
            detail = exc.read().decode('utf-8', 'replace')[:400]
        except Exception:  # pragma: no cover - o'qib bo'lmasa ham davom etamiz
            pass
        logger.warning('Agent: Gemini %s qaytardi — %s', exc.code, detail)
        if exc.code in RETRY_STATUSES:
            return None, REASON_BUSY
        return None, REASON_OFFLINE
    except (TimeoutError, socket.timeout) as exc:
        logger.warning('Agent: javob kechikdi — %s', exc)
        return None, REASON_TIMEOUT
    except (URLError, OSError, ValueError) as exc:
        # `URLError` ichida ham timeout bo'lishi mumkin.
        if isinstance(getattr(exc, 'reason', None), (TimeoutError, socket.timeout)):
            logger.warning('Agent: javob kechikdi — %s', exc)
            return None, REASON_TIMEOUT
        logger.warning('Agent javob bermadi: %s', exc)
        return None, REASON_OFFLINE


def _answer_text(payload):
    """Javob matni; matn yo'q bo'lsa sababi bilan.

    Gemini javobni chegaraga sig'dira olmasa (`MAX_TOKENS`) matn qismi
    BO'SH kelishi mumkin. Ilgari bu ham «javob bera olmadi» deb
    ko'rsatilardi — xodim savolini qisqartirish kerakligini bilmasdi.
    """
    text = _extract_text(payload)
    if text:
        return text, None
    candidates = payload.get('candidates') or []
    finish = (candidates[0].get('finishReason') if candidates else '') or ''
    if finish.upper() == 'MAX_TOKENS':
        return None, REASON_TOO_LONG
    logger.warning('Agent: bo‘sh javob keldi (finishReason=%s)', finish or '—')
    return None, REASON_OFFLINE


def ask(question, user, history=()):
    """Xodim savoliga javob qaytaradi.

    `(javob_matni, amal_taklifi, sabab)` uchligi. Javob bo'lsa sabab `None`,
    aks holda matn `None` va sabab yuqoridagi `REASON_*` lardan biri.
    """
    question = (question or '').strip()
    if not is_enabled() or not question:
        return None, None, REASON_OFFLINE

    body = json.dumps(_request_body(build_system_prompt(user), list(history), question))
    timeout = getattr(settings, 'AI_AGENT_TIMEOUT', 30.0)

    payload, reason = _call_gemini(body, timeout)
    if reason == REASON_BUSY:
        # Bepul tarifda daqiqasiga so'rov soni cheklangan; qisqa kutib
        # bitta qayta urinish ko'p holatda yetarli bo'ladi.
        time.sleep(RETRY_DELAY_SECONDS)
        payload, reason = _call_gemini(body, timeout)
    if payload is None:
        return None, None, reason

    text, reason = _answer_text(payload)
    if not text:
        return None, None, reason

    cleaned, action = parse_action(text, user)
    return cleaned, action, None
