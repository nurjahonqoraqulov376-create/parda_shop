from django import forms, template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def cell(obj, attr):
    """Ro'yxatdagi ustun qiymatini chiqaradi (bool bo'lsa belgi bilan)."""
    value = getattr(obj, attr, '')
    if callable(value):
        value = value()
    if isinstance(value, bool):
        return format_html('<span class="flag {}">{}</span>', 'yes' if value else 'no', '✓' if value else '×')
    if value in (None, ''):
        return '—'
    return value


@register.filter
def is_wide(field):
    """Maydon butun kenglikni egallashi kerakmi?

    Matn maydonlari va rasm tanlagichi ikki ustunga sig'maydi — ular
    yonma-yon turganda forma qiyshayib ketadi.
    """
    widget = field.field.widget
    if isinstance(widget, forms.Textarea):
        return True
    return isinstance(widget, (forms.FileInput, forms.ClearableFileInput))
