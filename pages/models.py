from django.db import models
from django.urls import reverse

from .imaging import ShrinkImageOnSaveMixin
from .mixins import TranslatableMixin


class SiteSettings(TranslatableMixin, models.Model):
    """Sayt bo'ylab ishlatiladigan sozlamalar (bitta yozuv)."""

    brand_name = models.CharField('Brend nomi', max_length=80, default='Sevara Design')
    tagline = models.CharField('Shior', max_length=160, blank=True)
    tagline_ru = models.CharField('Shior (ru)', max_length=160, blank=True)
    about_short = models.TextField('Qisqacha ma’lumot', blank=True)
    about_short_ru = models.TextField('Qisqacha ma’lumot (ru)', blank=True)
    about_full = models.TextField('Biz haqimizda (to‘liq)', blank=True)
    about_full_ru = models.TextField('Biz haqimizda (to‘liq, ru)', blank=True)
    phone_primary = models.CharField('Asosiy telefon', max_length=40, default='+998 99 986 71 99')
    phone_secondary = models.CharField('Qo‘shimcha telefon', max_length=40, blank=True)
    email = models.EmailField('Email', blank=True)
    address = models.CharField('Manzil', max_length=200, blank=True)
    address_ru = models.CharField('Manzil (ru)', max_length=200, blank=True)
    map_url = models.URLField('Xarita havolasi', blank=True)
    working_hours = models.CharField('Ish vaqti', max_length=120, blank=True)
    working_hours_ru = models.CharField('Ish vaqti (ru)', max_length=120, blank=True)
    telegram_url = models.URLField('Telegram', blank=True)
    instagram_url = models.URLField('Instagram', blank=True)
    facebook_url = models.URLField('Facebook', blank=True)
    youtube_url = models.URLField('YouTube', blank=True)

    class Meta:
        verbose_name = 'Sayt sozlamalari'
        verbose_name_plural = 'Sayt sozlamalari'

    def __str__(self):
        return self.brand_name

    @classmethod
    def load(cls):
        """Yagona yozuvni qaytaradi, bo'lmasa yaratadi."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    @property
    def socials(self):
        return [
            ('Telegram', self.telegram_url),
            ('Instagram', self.instagram_url),
            ('Facebook', self.facebook_url),
            ('YouTube', self.youtube_url),
        ]


class Banner(TranslatableMixin, models.Model):
    """Bosh sahifadagi hero slayder elementi."""

    title = models.CharField('Sarlavha', max_length=160)
    title_ru = models.CharField('Sarlavha (ru)', max_length=160, blank=True)
    subtitle = models.CharField('Matn', max_length=240, blank=True)
    subtitle_ru = models.CharField('Matn (ru)', max_length=240, blank=True)
    image = models.ImageField('Rasm', upload_to='banners/', blank=True)
    button_text = models.CharField('Tugma matni', max_length=60, blank=True)
    button_text_ru = models.CharField('Tugma matni (ru)', max_length=60, blank=True)
    button_url = models.CharField('Tugma havolasi', max_length=255, blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Bannerlar'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title


class Advantage(TranslatableMixin, models.Model):
    """«Nima uchun aynan biz?» blokidagi afzallik."""

    icon = models.CharField('Ikon (emoji)', max_length=8, default='✓')
    title = models.CharField('Sarlavha', max_length=120)
    title_ru = models.CharField('Sarlavha (ru)', max_length=120, blank=True)
    text = models.TextField('Matn')
    text_ru = models.TextField('Matn (ru)', blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Afzallik'
        verbose_name_plural = 'Afzalliklar'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title


class Testimonial(TranslatableMixin, models.Model):
    """«Mijozlar fikri» blokidagi sharh."""

    author = models.CharField('Mijoz ismi', max_length=120)
    role = models.CharField('Kim (shahar yoki lavozim)', max_length=120, blank=True)
    role_ru = models.CharField('Kim (ru)', max_length=120, blank=True)
    text = models.TextField('Sharh matni')
    text_ru = models.TextField('Sharh matni (ru)', blank=True)
    rating = models.PositiveSmallIntegerField('Baho (1–5)', default=5)
    photo = models.ImageField('Surat', upload_to='testimonials/', blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Mijoz fikri'
        verbose_name_plural = 'Mijozlar fikri'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.author

    @property
    def stars(self):
        """Shablonda yulduzlarni aylanib chiqish uchun."""
        return range(min(5, max(0, self.rating)))


class Client(models.Model):
    """«Bizga ishonishadi» blokidagi hamkor logotipi."""

    name = models.CharField('Nomi', max_length=120)
    logo = models.ImageField('Logotip', upload_to='clients/', blank=True)
    url = models.URLField('Sayti', blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Hamkor'
        verbose_name_plural = 'Hamkorlar'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class FaqItem(TranslatableMixin, models.Model):
    question = models.CharField('Savol', max_length=255)
    question_ru = models.CharField('Savol (ru)', max_length=255, blank=True)
    answer = models.TextField('Javob')
    answer_ru = models.TextField('Javob (ru)', blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Savol-javob'
        verbose_name_plural = 'Savol-javoblar'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.question


class Service(TranslatableMixin, models.Model):
    name = models.CharField('Nomi', max_length=140)
    name_ru = models.CharField('Nomi (ru)', max_length=140, blank=True)
    slug = models.SlugField('Slug', unique=True)
    icon = models.CharField('Ikon (emoji)', max_length=8, default='🛠')
    short_description = models.CharField('Qisqa tavsif', max_length=240, blank=True)
    short_description_ru = models.CharField('Qisqa tavsif (ru)', max_length=240, blank=True)
    description = models.TextField('To‘liq tavsif', blank=True)
    description_ru = models.TextField('To‘liq tavsif (ru)', blank=True)
    image = models.ImageField('Rasm', upload_to='services/', blank=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Xizmat'
        verbose_name_plural = 'Xizmatlar'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class Article(TranslatableMixin, models.Model):
    title = models.CharField('Sarlavha', max_length=200)
    title_ru = models.CharField('Sarlavha (ru)', max_length=200, blank=True)
    slug = models.SlugField('Slug', unique=True)
    excerpt = models.CharField('Qisqacha', max_length=300, blank=True)
    excerpt_ru = models.CharField('Qisqacha (ru)', max_length=300, blank=True)
    body = models.TextField('Matn', blank=True)
    body_ru = models.TextField('Matn (ru)', blank=True)
    image = models.ImageField('Rasm', upload_to='articles/', blank=True)
    published_at = models.DateField('Chop etilgan sana', auto_now_add=True)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Maqola'
        verbose_name_plural = 'Maqolalar'
        ordering = ['-published_at', '-id']

    def __str__(self):
        return self.title


class Work(ShrinkImageOnSaveMixin, TranslatableMixin, models.Model):
    """Portfolio — tayyorlangan va o‘rnatilgan pardalar."""

    title = models.CharField('Sarlavha', max_length=200)
    title_ru = models.CharField('Sarlavha (ru)', max_length=200, blank=True)
    slug = models.SlugField('Slug', unique=True)
    category = models.CharField('Turi', max_length=100, blank=True,
                                help_text='Masalan: Zebra parda, Rimcha parda')
    category_ru = models.CharField('Turi (ru)', max_length=100, blank=True)
    excerpt = models.CharField('Qisqacha tavsif', max_length=300, blank=True)
    excerpt_ru = models.CharField('Qisqacha tavsif (ru)', max_length=300, blank=True)
    description = models.TextField('To‘liq tavsif', blank=True)
    description_ru = models.TextField('To‘liq tavsif (ru)', blank=True)
    image = models.ImageField('Asosiy rasm', upload_to='works/')
    created_at = models.DateField('Qo‘shilgan sana', auto_now_add=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Ish'
        verbose_name_plural = 'Mening ishlarim'
        ordering = ['sort_order', '-created_at', '-id']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('pages:work_detail', args=[self.slug])


class ContentBlock(TranslatableMixin, models.Model):
    """Bosh sahifadagi SEO/ma’lumot matn bloklari."""

    key = models.SlugField('Kalit', unique=True, help_text='Masalan: parda-turlari')
    title = models.CharField('Sarlavha', max_length=200)
    title_ru = models.CharField('Sarlavha (ru)', max_length=200, blank=True)
    body = models.TextField('Matn (HTML ruxsat etilgan)')
    body_ru = models.TextField('Matn (ru)', blank=True)
    show_on_home = models.BooleanField('Bosh sahifada ko‘rsatish', default=True)
    sort_order = models.PositiveIntegerField('Tartib', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Kontent bloki'
        verbose_name_plural = 'Kontent bloklari'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title
