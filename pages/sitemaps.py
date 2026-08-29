"""Qidiruv tizimlari uchun sayt xaritasi.

Sayt ikki tilli (`i18n_patterns`), shuning uchun har bir sahifa ikki
manzilda mavjud: `/uz/...` va `/ru/...`. Django'ning `Sitemap` sinfi
`i18n = True` bilan ikkalasini ham o'zi qo'shadi.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Category, Product
from pages.models import Work


class StaticViewSitemap(Sitemap):
    """O'zgarmas sahifalar: bosh sahifa, biz haqimizda, portfolio, aloqa."""

    i18n = True
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return ['pages:home', 'pages:about', 'pages:works', 'pages:contact',
                'catalog:list']

    def location(self, item):
        return reverse(item)

    def priority_for(self, item):  # pragma: no cover - hujjat uchun
        return 1.0 if item == 'pages:home' else self.priority


class CategorySitemap(Sitemap):
    i18n = True
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True)


class ProductSitemap(Sitemap):
    i18n = True
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Product.objects.filter(is_active=True)


class WorkSitemap(Sitemap):
    i18n = True
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Work.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at


SITEMAPS = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
    'works': WorkSitemap,
}
