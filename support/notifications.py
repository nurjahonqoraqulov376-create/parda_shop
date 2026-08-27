"""Support xodimlariga xabar berish (email).

Panel tomonidagi belgi alohida ishlaydi — u kontekst protsessoridagi
hisoblagichdan olinadi, bu yerda faqat email yuboriladi.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)
User = get_user_model()

# Kim xabar oladi: support xodimlari va administratorlar.
NOTIFY_ROLES = ('support', 'admin')


def recipient_emails():
    """Xabar yuboriladigan manzillar ro'yxati."""
    emails = list(getattr(settings, 'SUPPORT_NOTIFY_EMAILS', []) or [])
    staff = (
        User.objects
        .filter(is_active=True, profile__role__in=NOTIFY_ROLES)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    emails.extend(staff)
    # Takrorlanmasin, tartib barqaror bo'lsin (test uchun ham qulay).
    return sorted({email.strip() for email in emails if email and email.strip()})


def _conversation_url(conversation):
    path = reverse('dashboard:chat_detail', args=[conversation.pk])
    base = (getattr(settings, 'SITE_BASE_URL', '') or '').rstrip('/')
    return '%s%s' % (base, path) if base else path


def notify_operators(conversation):
    """Yangi operator so'rovi haqida email yuboradi.

    Hech qachon istisno ko'tarmaydi: SMTP sozlanmagan yoki yiqilgan bo'lsa ham
    mijozning suhbati davom etishi kerak.
    """
    recipients = recipient_emails()
    if not recipients:
        logger.info('Support xabari yuborilmadi: qabul qiluvchi email yo‘q.')
        return False

    last_messages = conversation.messages.filter(sender='visitor').order_by('-id')[:3]
    excerpt = '\n'.join('— %s' % message.text for message in reversed(list(last_messages)))

    subject = 'Jonli operator so‘raldi — suhbat #%s' % conversation.pk
    body = (
        'Saytdagi mijoz jonli operator so‘radi.\n\n'
        'Suhbat: #%(pk)s\n'
        'Til: %(lang)s\n\n'
        'Mijozning oxirgi xabarlari:\n%(excerpt)s\n\n'
        'Javob berish: %(url)s\n'
    ) % {
        'pk': conversation.pk,
        'lang': conversation.language,
        'excerpt': excerpt or '(xabar yo‘q)',
        'url': _conversation_url(conversation),
    }

    try:
        send_mail(
            subject, body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipients,
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 — SMTP xatosi suhbatni buzmasin
        logger.warning('Support emaili yuborilmadi: %s', exc)
        return False
    return True
