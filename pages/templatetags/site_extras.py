from django import template
from django.utils.translation import get_language

from parda_shop.regions import district_label
from parda_shop.translations import translate

register = template.Library()


@register.simple_tag
def t(key):
    """Interfeys matni: {% t "nav.catalog" %}"""
    return translate(key, get_language())


@register.simple_tag
def tf(obj, field):
    """Model maydonining tilga mos varianti: {% tf product "name" %}"""
    if obj is None:
        return ''
    if hasattr(obj, 't'):
        return obj.t(field)
    return getattr(obj, field, '')


@register.filter
def money(value):
    """Narxni 1 234 567 ko'rinishida chiqaradi.

    Qiymat yo'q bo'lsa bo'sh satr qaytadi — shablonda "None" ko'rinib
    qolmasligi uchun.
    """
    if value is None or value == '':
        return ''
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return f'{number:,}'.replace(',', ' ')


@register.filter
def district(value):
    """Tuman qiymatini joriy tildagi nomga aylantiradi."""
    return district_label(value, get_language())


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """Joriy GET parametrlarini saqlab, ba'zilarini almashtiradi."""
    request = context.get('request')
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value in (None, ''):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode() if hasattr(params, 'urlencode') else ''
    return f'?{encoded}' if encoded else ''
