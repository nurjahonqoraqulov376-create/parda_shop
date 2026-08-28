from django.db import models
from django.urls import reverse

from pages.imaging import ShrinkImageOnSaveMixin
from pages.mixins import TranslatableMixin


class Category(ShrinkImageOnSaveMixin, TranslatableMixin, models.Model):
    name = models.CharField('Nomi', max_length=120)
    name_ru = models.CharField('Nomi (ru)', max_length=120, blank=True)
    slug = models.SlugField('Slug', unique=True)
    description = models.TextField('Tavsif', blank=True)
    description_ru = models.TextField('Tavsif (ru)', blank=True)
    image = models.ImageField('Rasm', upload_to='categories/', blank=True)
    icon = models.CharField('Ikon (emoji)', max_length=8, blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)
    show_on_home = models.BooleanField('Bosh sahifada bo‘lim sifatida', default=False)

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category', args=[self.slug])

    @property
    def min_price(self):
        return self.products.filter(is_active=True).aggregate(models.Min('price'))['price__min']


class Product(ShrinkImageOnSaveMixin, TranslatableMixin, models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products', verbose_name='Kategoriya',
    )
    name = models.CharField('Nomi', max_length=160)
    name_ru = models.CharField('Nomi (ru)', max_length=160, blank=True)
    slug = models.SlugField('Slug', unique=True)
    sku = models.CharField('Artikul', max_length=40, blank=True)
    image = models.ImageField('Asosiy rasm', upload_to='curtains/', blank=True)
    short_description = models.CharField('Qisqa tavsif', max_length=240)
    short_description_ru = models.CharField('Qisqa tavsif (ru)', max_length=240, blank=True)
    description = models.TextField('To‘liq tavsif')
    description_ru = models.TextField('To‘liq tavsif (ru)', blank=True)
    price = models.DecimalField('Narxi', max_digits=12, decimal_places=0)
    old_price = models.DecimalField('Eski narxi', max_digits=12, decimal_places=0, null=True, blank=True)
    stock = models.PositiveIntegerField('Ombordagi soni', default=0)
    is_active = models.BooleanField('Aktiv', default=True)
    is_featured = models.BooleanField('Tanlangan (ommabop)', default=False)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.slug])

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(round((1 - self.price / self.old_price) * 100))
        return 0

    @property
    def in_stock(self):
        return self.stock > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images', verbose_name='Mahsulot',
    )
    image = models.ImageField('Rasm', upload_to='curtains/gallery/')
    sort_order = models.PositiveIntegerField('Tartib', default=0)

    class Meta:
        verbose_name = 'Mahsulot rasmi'
        verbose_name_plural = 'Mahsulot rasmlari'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.product.name} — rasm #{self.pk}'
