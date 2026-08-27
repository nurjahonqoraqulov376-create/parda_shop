from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Mijoz bilan bo'lgan bitta suhbat.

    Mijoz ro'yxatdan o'tmaydi (saytning umumiy tamoyili), shuning uchun suhbat
    brauzer sessiyasi orqali tanib olinadi.
    """

    STATUS_BOT = 'bot'
    STATUS_WAITING = 'waiting_operator'
    STATUS_WITH_OPERATOR = 'with_operator'
    STATUS_CLOSED = 'closed'
    STATUS = [
        (STATUS_BOT, 'Bot javob bermoqda'),
        (STATUS_WAITING, 'Operator kutilmoqda'),
        (STATUS_WITH_OPERATOR, 'Operator ulangan'),
        (STATUS_CLOSED, 'Yopilgan'),
    ]

    session_key = models.CharField('Sessiya', max_length=40, db_index=True)
    status = models.CharField('Holat', max_length=20, choices=STATUS, default=STATUS_BOT)
    language = models.CharField('Til', max_length=5, default='uz')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='support_conversations', verbose_name='Operator',
    )
    visitor_name = models.CharField('Mijoz ismi', max_length=120, blank=True)
    visitor_phone = models.CharField('Mijoz telefoni', max_length=30, blank=True)
    created_at = models.DateTimeField('Boshlangan', auto_now_add=True)
    last_message_at = models.DateTimeField('Oxirgi xabar', auto_now_add=True, db_index=True)
    escalated_at = models.DateTimeField('Operator so‘ralgan', null=True, blank=True)

    class Meta:
        verbose_name = 'Suhbat'
        verbose_name_plural = 'Suhbatlar'
        ordering = ['-last_message_at']

    def __str__(self):
        return 'Suhbat #%s' % self.pk

    @property
    def is_waiting(self):
        return self.status == self.STATUS_WAITING

    @property
    def bot_is_answering(self):
        """Operator ulangandan keyin AI aralashmaydi."""
        return self.status == self.STATUS_BOT

    @property
    def unread_count(self):
        return self.messages.filter(sender=Message.SENDER_VISITOR, seen_by_operator=False).count()

    def touch(self):
        """Oxirgi xabar vaqtini yangilaydi (ro'yxatda tepaga chiqishi uchun)."""
        from django.utils import timezone
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])


class Message(models.Model):
    SENDER_VISITOR = 'visitor'
    SENDER_AI = 'ai'
    SENDER_OPERATOR = 'operator'
    SENDER_SYSTEM = 'system'
    SENDERS = [
        (SENDER_VISITOR, 'Mijoz'),
        (SENDER_AI, 'Sun’iy intellekt'),
        (SENDER_OPERATOR, 'Operator'),
        (SENDER_SYSTEM, 'Tizim'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name='Suhbat',
    )
    sender = models.CharField('Kim yozdi', max_length=20, choices=SENDERS)
    text = models.TextField('Matn')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='support_messages', verbose_name='Xodim',
    )
    created_at = models.DateTimeField('Vaqti', auto_now_add=True)
    seen_by_operator = models.BooleanField('Operator ko‘rdi', default=False)

    class Meta:
        verbose_name = 'Xabar'
        verbose_name_plural = 'Xabarlar'
        ordering = ['id']

    def __str__(self):
        return '%s: %s' % (self.get_sender_display(), self.text[:40])

    @property
    def from_visitor(self):
        return self.sender == self.SENDER_VISITOR
