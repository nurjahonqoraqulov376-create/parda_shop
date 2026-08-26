from django.conf import settings
from django.db import models

from catalog.models import Product
from parda_shop.regions import DEFAULT_DISTRICT, DISTRICT_CHOICES


class Order(models.Model):
    STATUS = [
        ('new', 'Yangi'),
        ('confirmed', 'Tasdiqlangan'),
        ('done', 'Yetkazildi'),
        ('cancelled', 'Bekor qilindi'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='Foydalanuvchi',
    )
    full_name = models.CharField('Ism-familiya', max_length=160)
    phone = models.CharField('Telefon', max_length=30)
    region = models.CharField(
        'Tuman / shahar', max_length=40,
        choices=DISTRICT_CHOICES, default=DEFAULT_DISTRICT,
    )
    address = models.TextField('Manzil')
    comment = models.TextField('Izoh', blank=True)
    total_amount = models.DecimalField('Jami summa', max_digits=14, decimal_places=0, default=0)
    status = models.CharField('Holat', max_length=20, choices=STATUS, default='new')
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)

    class Meta:
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Buyurtma #{self.pk}'

    @property
    def total(self):
        return sum(item.total for item in self.items.all())

    def recalculate_total(self):
        self.total_amount = self.total
        self.save(update_fields=['total_amount'])
        return self.total_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Mahsulot')
    quantity = models.PositiveIntegerField('Miqdor')
    price = models.DecimalField('Narxi', max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = 'Buyurtma qatori'
        verbose_name_plural = 'Buyurtma qatorlari'

    def __str__(self):
        return f'{self.product} × {self.quantity}'

    @property
    def total(self):
        return self.price * self.quantity


class Lead(models.Model):
    """Sayt formalaridan tushgan ariza (qo'ng'iroq, konsultatsiya, chegirma, o'lchov)."""

    TYPES = [
        ('callback', 'Qo‘ng‘iroqni so‘rash'),
        ('consultation', 'Bepul konsultatsiya'),
        ('discount', '10% chegirma'),
        ('measure', 'Bepul o‘lchov'),
        ('order', 'Buyurtma so‘rovi'),
        ('contact', 'Aloqa formasi'),
        ('popup', 'Bildirishnoma'),
    ]
    STATUS = [
        ('new', 'Yangi'),
        ('in_progress', 'Ishlanmoqda'),
        ('done', 'Bajarildi'),
        ('rejected', 'Rad etilgan'),
    ]

    name = models.CharField('Ism', max_length=120)
    phone = models.CharField('Telefon', max_length=30)
    message = models.TextField('Xabar', blank=True)
    lead_type = models.CharField('Ariza turi', max_length=20, choices=TYPES, default='callback')
    status = models.CharField('Holat', max_length=20, choices=STATUS, default='new')
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_leads', verbose_name='Mas’ul',
    )
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)

    class Meta:
        verbose_name = 'So‘rov'
        verbose_name_plural = 'So‘rovlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.phone}'
