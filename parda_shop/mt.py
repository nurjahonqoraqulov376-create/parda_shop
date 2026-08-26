"""O'zbekchadan ruschaga avtomatik mashina tarjimasi.

Google'ning ochiq `translate_a` endpointi ishlatiladi: API kalit ham,
qo'shimcha kutubxona ham kerak emas — faqat standart `urllib`. Tarmoq
bo'lmasa yoki javob buzilgan bo'lsa `None` qaytadi, chaqiruvchi shunda
mavjud qiymatni o'zgarishsiz qoldiradi.

Natijalar keshlanadi, shuning uchun bir xil matnni qayta saqlash tarmoqqa
chiqmaydi.
"""

import hashlib
import json
import logging
import re
import threading
from contextlib import contextmanager
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

from .translations import UI

logger = logging.getLogger(__name__)

ENDPOINT = 'https://translate.googleapis.com/translate_a/single'
USER_AGENT = 'Mozilla/5.0 (compatible; SevaraDesign/1.0)'

# `q` GET parametri juda uzun bo'lsa Google xato qaytaradi — matn shu hajmda bo'linadi.
CHUNK_LIMIT = 1200
CACHE_PREFIX = 'mt:'
CACHE_TTL = 60 * 60 * 24 * 30  # 30 kun

TAG_RE = re.compile(r'(<[^>]+>)')
LETTER_RE = re.compile(r'[^\W\d_]', re.UNICODE)

# `suspend()` blokida tarjima o'chiriladi (seed, import va shunga o'xshash ishlar uchun).
_state = threading.local()


def _build_glossary():
    """Interfeys lug'atidan uz -> ru moslik jadvali.

    Mashina tarjimasi qisqa iboralarni kontekstsiz noto'g'ri o'giradi
    («Batafsil» -> «Более»), shuning uchun saytda allaqachon tasdiqlangan
    variantlar ustuvor hisoblanadi.
    """
    russian = UI['ru']
    return {
        value.strip().casefold(): russian[key]
        for key, value in UI['uz'].items()
        if value.strip() and key in russian
    }


GLOSSARY = _build_glossary()


@contextmanager
def suspend():
    """Blok ichida avtomatik tarjimani vaqtincha o'chiradi."""
    previous = getattr(_state, 'suspended', False)
    _state.suspended = True
    try:
        yield
    finally:
        _state.suspended = previous


def is_enabled():
    """Avtomatik tarjima shu paytda ishlashi mumkinmi?"""
    if getattr(_state, 'suspended', False):
        return False
    return getattr(settings, 'AUTO_TRANSLATE', True)


def _timeout():
    return getattr(settings, 'AUTO_TRANSLATE_TIMEOUT', 4.0)


def _chunks(text, limit=CHUNK_LIMIT):
    """Matnni ketma-ket bo'laklarga ajratadi; bo'laklar birikkanda asl matn chiqadi."""
    if len(text) <= limit:
        yield text
        return
    buffer = ''
    for part in re.split(r'(\n+)', text):  # ajratgichlar ham saqlanadi
        while len(part) > limit:  # bitta parchaning o'zi juda uzun
            cut = part.rfind(' ', 0, limit) + 1 or limit
            if buffer:
                yield buffer
                buffer = ''
            yield part[:cut]
            part = part[cut:]
        if len(buffer) + len(part) > limit:
            yield buffer
            buffer = part
        else:
            buffer += part
    if buffer:
        yield buffer


def _fetch(text, source, target):
    """Bitta bo'lakni Google orqali tarjima qiladi."""
    query = urlencode({'client': 'gtx', 'sl': source, 'tl': target, 'dt': 't', 'q': text})
    request = Request(f'{ENDPOINT}?{query}', headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=_timeout()) as response:
        payload = json.loads(response.read().decode('utf-8'))
    # Javob ko'rinishi: [[["tarjima", "manba", ...], ...], ...]
    return ''.join(part[0] for part in payload[0] if part and part[0])


def translate_text(text, source='uz', target='ru'):
    """Oddiy matnni tarjima qiladi. Bo'sh matn yoki xatoda `None` qaytadi."""
    text = (text or '').strip()
    if not text or not is_enabled() or not LETTER_RE.search(text):
        return None

    if source == 'uz' and target == 'ru':
        known = GLOSSARY.get(text.casefold())
        if known:
            return known

    digest = hashlib.sha1(text.encode('utf-8')).hexdigest()
    key = f'{CACHE_PREFIX}{source}:{target}:{digest}'
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        result = ''.join(_fetch(chunk, source, target) for chunk in _chunks(text)).strip()
    except (OSError, ValueError, IndexError, TypeError) as exc:
        logger.warning('Avtomatik tarjima bajarilmadi: %s', exc)
        return None

    if not result:
        return None
    cache.set(key, result, CACHE_TTL)
    return result


def _keep_spacing(original, translated):
    """Asl bo'lakning oldi-orqasidagi bo'shliqlarni tarjimaga qaytaradi."""
    lead = original[:len(original) - len(original.lstrip())]
    tail = original[len(original.rstrip()):]
    return f'{lead}{translated}{tail}'


def translate_html(html, source='uz', target='ru'):
    """HTML teglarini saqlab qolib, faqat matn qismlarini tarjima qiladi.

    Bo'laklardan bittasi tarjima bo'lmasa, yarim tarjima qilingan natija
    saqlanib qolmasligi uchun `None` qaytariladi.
    """
    if '<' not in (html or ''):
        return translate_text(html, source, target)

    pieces = []
    translated_any = False
    for piece in TAG_RE.split(html):
        if piece.startswith('<') or not LETTER_RE.search(piece):
            pieces.append(piece)
            continue
        translated = translate_text(piece, source, target)
        if translated is None:
            return None
        translated_any = True
        pieces.append(_keep_spacing(piece, translated))
    return ''.join(pieces) if translated_any else None
