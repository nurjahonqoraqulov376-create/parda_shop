"""Boshqaruv panelidagi generic CRUD bo'limlari ro'yxati."""

from catalog.models import Category, Product
from pages.models import Advantage, Banner, Client, ContentBlock, Testimonial, Work

from .forms import dashboard_form

# key -> bo'lim sozlamalari
# columns: (ustun sarlavhasi, model atributi)
REGISTRY = {
    'mahsulotlar': {
        'model': Product,
        'title': 'Mahsulotlar',
        'title_ru': 'Товары',
        'columns': [('Nomi', 'name'), ('Kategoriya', 'category'), ('Narxi', 'price'),
                    ('Ombor', 'stock'), ('Aktiv', 'is_active')],
        'search_fields': ('name', 'name_ru', 'sku'),
        'with_slug': True,
        'admin_only': False,
        'select_related': ('category',),
    },
    'kategoriyalar': {
        'model': Category,
        'title': 'Kategoriyalar',
        'title_ru': 'Категории',
        'columns': [('Nomi', 'name'), ('Slug', 'slug'), ('Tartib', 'sort_order'),
                    ('Bosh sahifada', 'show_on_home'), ('Aktiv', 'is_active')],
        'search_fields': ('name', 'name_ru'),
        'with_slug': True,
        'admin_only': False,
    },
    'bannerlar': {
        'model': Banner,
        'title': 'Bannerlar',
        'title_ru': 'Баннеры',
        'columns': [('Sarlavha', 'title'), ('Tartib', 'sort_order'), ('Aktiv', 'is_active')],
        'search_fields': ('title',),
        'with_slug': False,
        'admin_only': True,
    },
    'afzalliklar': {
        'model': Advantage,
        'title': 'Afzalliklar',
        'title_ru': 'Преимущества',
        'columns': [('Ikon', 'icon'), ('Sarlavha', 'title'), ('Tartib', 'sort_order'), ('Aktiv', 'is_active')],
        'search_fields': ('title',),
        'with_slug': False,
        'admin_only': True,
    },
    'mijozlar-fikri': {
        'model': Testimonial,
        'title': 'Mijozlar fikri',
        'title_ru': 'Отзывы клиентов',
        'columns': [('Mijoz', 'author'), ('Kim', 'role'), ('Baho', 'rating'),
                    ('Tartib', 'sort_order'), ('Aktiv', 'is_active')],
        'search_fields': ('author', 'text'),
        'with_slug': False,
        'admin_only': True,
    },
    'hamkorlar': {
        'model': Client,
        'title': 'Hamkorlar',
        'title_ru': 'Партнёры',
        'columns': [('Nomi', 'name'), ('Tartib', 'sort_order'), ('Aktiv', 'is_active')],
        'search_fields': ('name',),
        'with_slug': False,
        'admin_only': True,
    },
    'ishlarimiz': {
        'model': Work,
        'title': 'Mening ishlarim',
        'title_ru': 'Наши работы',
        'columns': [('Sarlavha', 'title'), ('Turi', 'category'), ('Sana', 'created_at'),
                    ('Tartib', 'sort_order'), ('Aktiv', 'is_active')],
        'search_fields': ('title', 'title_ru', 'category'),
        'with_slug': True,
        'admin_only': False,
    },
    'matn-bloklari': {
        'model': ContentBlock,
        'title': 'Kontent bloklari',
        'title_ru': 'Контент-блоки',
        'columns': [('Sarlavha', 'title'), ('Kalit', 'key'), ('Bosh sahifada', 'show_on_home'), ('Aktiv', 'is_active')],
        'search_fields': ('title', 'key'),
        'with_slug': False,
        'admin_only': True,
    },
}


def get_section(key):
    """Bo'lim sozlamalarini qaytaradi, topilmasa None."""
    return REGISTRY.get(key)


def get_form_class(key):
    section = REGISTRY[key]
    return dashboard_form(section['model'], with_slug=section['with_slug'])
