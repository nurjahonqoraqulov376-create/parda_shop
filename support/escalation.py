"""«Jonli operator kerak» ni aniqlash va operatorni chaqirish."""

import logging
import re

from django.utils import timezone

from .models import Conversation, Message
from .notifications import notify_operators

logger = logging.getLogger(__name__)

# Kalit iboralar — AI ishlamasa ham (kalit yo'q, tarmoq yo'q) darhol va bepul
# ishlaydi. O'zbekcha va ruscha variantlar.
OPERATOR_PHRASES = (
    # o'zbekcha
    'jonli operator',
    'operator kerak',
    'operator bilan',
    'operatorni chaqir',
    'operator chaqir',
    'odam bilan',
    'inson bilan',
    'menejer bilan',
    'menejer kerak',
    'xodim bilan',
    'jonli odam',
    'real odam',
    # ruscha
    'живой оператор',
    'нужен оператор',
    'с оператором',
    'позовите оператора',
    'с человеком',
    'живой человек',
    'реальный человек',
    'с менеджером',
    'нужен менеджер',
)

# Loyihada apostrof uch xil belgida uchraydi (', ', ') — solishtirishdan oldin
# hammasini bittaga keltiramiz.
_APOSTROPHES = str.maketrans({'‘': "'", '’': "'", 'ʻ': "'", 'ʼ': "'"})
_SPACES_RE = re.compile(r'\s+')


def normalize(text):
    text = (text or '').translate(_APOSTROPHES).casefold()
    return _SPACES_RE.sub(' ', text).strip()


def wants_operator(text):
    """Mijoz matnida jonli operator so'rovi bormi?"""
    normalized = normalize(text)
    return any(phrase in normalized for phrase in OPERATOR_PHRASES)


def escalate(conversation, reason=''):
    """Suhbatni operatorga uzatadi va xodimlarga xabar beradi.

    Allaqachon operator kutilayotgan yoki ulangan bo'lsa hech narsa qilmaydi —
    mijoz bir necha marta yozsa ham operator bir marta xabar oladi.
    """
    if conversation.status in (Conversation.STATUS_WAITING, Conversation.STATUS_WITH_OPERATOR):
        return False

    conversation.status = Conversation.STATUS_WAITING
    conversation.escalated_at = timezone.now()
    conversation.save(update_fields=['status', 'escalated_at'])

    if reason:
        Message.objects.create(
            conversation=conversation, sender=Message.SENDER_SYSTEM, text=reason,
            seen_by_operator=True,
        )

    # Xabar yuborishdagi xatolik mijozning suhbatini buzmasligi kerak.
    try:
        notify_operators(conversation)
    except Exception as exc:  # noqa: BLE001 — bu yerda hech qanday xato o'tmasin
        logger.warning('Operatorlarga xabar yuborilmadi: %s', exc)
    return True
