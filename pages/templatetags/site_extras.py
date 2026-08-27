from django import template
from django.conf import settings
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


@register.simple_tag(takes_context=True)
def language_url(context, code):
    """Joriy sahifaning boshqa tildagi manzili.

    Django'ning `set_language` view'i bu saytda ishonchli emas: u
    `i18n_patterns` dan TASHQARIDA turadi, shuning uchun `resolve()` ni
    joriy faol til prefiksi bilan bajaradi va `/ru/...` manzilini `uz` faol
    bo'lganda topa olmaydi. Natijada foydalanuvchi o'sha tildagi sahifada
    qolib ketardi (`uz -> ru` ishlardi, `ru -> uz` yo'q).

    Bu yerda prefiksning o'zi almashtiriladi. Sayt manzillari ikkala tilda
    bir xil (`katalog/`, `savat/` va h.k. tarjima qilinmagan), shuning uchun
    bu har doim to'g'ri ishlaydi. Qo'shimcha foyda: POST o'rniga oddiy
    havola — CSRF ham, `Referer` sarlavhasi ham talab qilinmaydi.
    """
    codes = [item[0] for item in settings.LANGUAGES]
    if code not in codes:
        return '/'
    request = context.get('request')
    if request is None:
        return '/%s/' % code

    path = request.get_full_path()
    head, _, tail = path.lstrip('/').partition('/')
    if head in codes:
        return '/%s/%s' % (code, tail)
    return '/%s/%s' % (code, path.lstrip('/'))
