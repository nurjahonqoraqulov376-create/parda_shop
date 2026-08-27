"""Mijoz tomonidagi suhbat (suzuvchi oyna) uchun JSON API."""

from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET, require_POST

from parda_shop.translations import translate

from . import ai
from .escalation import escalate, wants_operator
from .models import Conversation, Message

MAX_MESSAGE_LENGTH = 1000
# Bir sessiyada soatiga nechta xabar yuborish mumkin (suiiste'mol va bepul
# tarif kvotasiga qarshi).
RATE_LIMIT_PER_HOUR = 40


def _t(key):
    return translate(key, get_language())


def _session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_conversation(request, create=False):
    session_key = _session_key(request)
    conversation = (
        Conversation.objects
        .filter(session_key=session_key)
        .exclude(status=Conversation.STATUS_CLOSED)
        .order_by('-id')
        .first()
    )
    if conversation is None and create:
        conversation = Conversation.objects.create(
            session_key=session_key, language=(get_language() or 'uz')[:5],
        )
    return conversation


def _serialize(message):
    return {
        'id': message.pk,
        'sender': message.sender,
        'text': message.text,
        'time': timezone.localtime(message.created_at).strftime('%H:%M'),
    }


def _payload(conversation, messages):
    return {
        'conversation': conversation.pk,
        'status': conversation.status,
        'waiting': conversation.is_waiting,
        'messages': [_serialize(message) for message in messages],
    }


@require_GET
def history(request):
    """Suhbat tarixi yoki `after` dan keyingi yangi xabarlar."""
    conversation = _get_conversation(request)
    if conversation is None:
        return JsonResponse({'conversation': None, 'status': None, 'waiting': False, 'messages': []})

    messages = conversation.messages.exclude(sender=Message.SENDER_SYSTEM)
    after = request.GET.get('after')
    if after and after.isdigit():
        messages = messages.filter(pk__gt=int(after))
    return JsonResponse(_payload(conversation, messages))


@require_POST
def send(request):
    """Mijoz xabarini qabul qiladi va javob qaytaradi."""
    text = (request.POST.get('text') or '').strip()
    if not text:
        return JsonResponse({'error': _t('support.empty')}, status=400)
    if len(text) > MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': _t('support.too_long')}, status=400)

    conversation = _get_conversation(request, create=True)

    # Soatlik cheklov — sessiya bo'yicha.
    hour_ago = timezone.now() - timezone.timedelta(hours=1)
    recent = Message.objects.filter(
        conversation__session_key=conversation.session_key,
        sender=Message.SENDER_VISITOR,
        created_at__gte=hour_ago,
    ).count()
    if recent >= RATE_LIMIT_PER_HOUR:
        return JsonResponse({'error': _t('support.rate_limited')}, status=429)

    visitor_message = Message.objects.create(
        conversation=conversation, sender=Message.SENDER_VISITOR, text=text,
    )
    conversation.touch()

    replies = []

    if wants_operator(text):
        # Kalit ibora — AI'ni chaqirmaymiz, darhol operatorga uzatamiz.
        if escalate(conversation, reason='Mijoz jonli operator so‘radi.'):
            replies.append(_new_system_reply(conversation, _t('support.operator_called')))
    elif conversation.bot_is_answering:
        answer, needs_operator = ai.ask(
            text, history=_history_for_ai(conversation, exclude=visitor_message.pk),
            language=conversation.language,
        )
        if answer:
            replies.append(Message.objects.create(
                conversation=conversation, sender=Message.SENDER_AI, text=answer,
                seen_by_operator=True,
            ))
        if needs_operator and escalate(conversation, reason='AI javob bera olmadi.'):
            replies.append(_new_system_reply(conversation, _t('support.operator_called')))

    return JsonResponse({
        **_payload(conversation, [visitor_message, *replies]),
        'ok': True,
    })


def _new_system_reply(conversation, text):
    return Message.objects.create(
        conversation=conversation, sender=Message.SENDER_AI, text=text,
        seen_by_operator=True,
    )


def _history_for_ai(conversation, exclude=None):
    """AI uchun oxirgi xabarlar (tizim xabarlarisiz)."""
    queryset = conversation.messages.exclude(sender=Message.SENDER_SYSTEM)
    if exclude:
        queryset = queryset.exclude(pk=exclude)
    recent = list(queryset.order_by('-id')[:ai.HISTORY_LIMIT])
    return [(message.sender, message.text) for message in reversed(recent)]
