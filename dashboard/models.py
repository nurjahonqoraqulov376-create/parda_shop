"""Boshqaruv paneli jadvallari."""

from django.conf import settings
from django.db import models


class AgentAction(models.Model):
    """AI yordamchi bajargan har bir amalning yozuvi.

    Agent xodim nomidan baza yozadi, shuning uchun «kim, qachon, nimani
    o'zgartirdi» degan savolga javob bo'lishi shart. Bu yozuvlar
    o'chirilmaydi va tahrirlanmaydi — faqat qo'shiladi.
    """

    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUSES = [
        (STATUS_DONE, 'Bajarildi'),
        (STATUS_FAILED, 'Xato'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='agent_actions', verbose_name='Xodim',
    )
    action = models.CharField('Amal', max_length=50)
    summary = models.CharField('Tavsif', max_length=255)
    payload = models.JSONField('Yuborilgan maydonlar', default=dict, blank=True)
    status = models.CharField('Holat', max_length=10, choices=STATUSES, default=STATUS_DONE)
    error = models.TextField('Xato matni', blank=True)
    object_id = models.PositiveIntegerField('Yozuv raqami', null=True, blank=True)
    object_url = models.CharField('Yozuv manzili', max_length=255, blank=True)
    created_at = models.DateTimeField('Sana', auto_now_add=True)

    class Meta:
        verbose_name = 'Yordamchi amali'
        verbose_name_plural = 'Yordamchi amallari'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return '%s — %s' % (self.action, self.summary)
