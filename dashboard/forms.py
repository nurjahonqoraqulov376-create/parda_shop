from django import forms
from django.contrib.auth import get_user_model
from django.forms import modelform_factory
from django.utils.text import slugify
from django.utils.translation import get_language

from orders.models import Lead, Order
from parda_shop.translations import translate


# Maydon nomi -> xodimga ko'rsatiladigan tushuntirish.
# Modelda `help_text` yozilmagan bo'lsa shu ishlatiladi: har bir model
# uchun alohida sozlash shart emas.
FIELD_HINTS = {
    'name': 'Mijoz katalogda ko‘radigan nom. Qisqa va aniq bo‘lsin.',
    'title': 'Sahifa sarlavhasi — ro‘yxatda ham shu ko‘rinadi.',
    'price': 'So‘mda, faqat raqam. Masalan: 250000',
    'old_price': 'Chegirmagacha bo‘lgan narx. Bo‘sh qoldirsangiz chegirma ko‘rsatilmaydi.',
    'stock': 'Omborda nechta bor. 0 bo‘lsa mijoz buyurtma bera olmaydi.',
    'sku': 'Ichki hisob uchun kod. Ixtiyoriy.',
    'category': 'Mahsulot qaysi bo‘limda turishi.',
    'icon': 'Bitta belgi yoki emoji. Masalan: ▤',
    'excerpt': 'Bir-ikki jumla — ro‘yxatda shu ko‘rinadi.',
    'short_description': 'Kartochkada ko‘rinadigan qisqa matn (1–2 jumla).',
    'description': 'To‘liq tavsif: mato, o‘lcham, o‘rnatish, kafolat.',
    'image': 'Keng (gorizontal) surat yaxshi chiqadi. Katta faylni tizim o‘zi kichraytiradi.',
    'sort_order': 'Kichik raqam yuqorida turadi.',
    'is_active': 'Belgini olib tashlasangiz saytdan yashiriladi (o‘chirilmaydi).',
    'is_featured': 'Bosh sahifadagi «Ommabop» bo‘limida chiqadi.',
    'show_on_home': 'Bosh sahifadagi ro‘yxatga qo‘shiladi.',
    'rating': '1 dan 5 gacha.',
}


class StyledFormMixin:
    """Barcha maydonlarga bir xil CSS klass va placeholder qo'shadi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.FileInput, forms.ClearableFileInput)):
                continue
            classes = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{classes} field'.strip()


class ReadOnlyTranslationMixin:
    """`_ru` maydonlarini faqat ko'rish uchun qoldiradi.

    Ruscha variantni saqlash paytida `TranslatableMixin` o'zbekcha matndan
    qayta yozadi, shuning uchun formada uni tahrirlashning ma'nosi yo'q —
    joriy tarjimani ko'rsatib turamiz, xolos.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hint = translate('dash.auto_translated', get_language())
        for name, field in self.fields.items():
            if not name.endswith('_ru'):
                continue
            field.disabled = True
            field.required = False
            field.help_text = hint


class AutoSlugMixin:
    """`slug` bo'sh qoldirilsa nom/sarlavhadan avtomatik yasaydi."""

    slug_source_fields = ('name', 'title')

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        if slug:
            return slug
        for source in self.slug_source_fields:
            value = self.data.get(source)
            if value:
                return slugify(value)[:50] or 'element'
        return 'element'


def dashboard_form(model, fields='__all__', with_slug=False):
    """Model uchun standart boshqaruv formasi yaratadi."""
    bases = (ReadOnlyTranslationMixin, StyledFormMixin, forms.ModelForm)
    if with_slug:
        bases = (AutoSlugMixin,) + bases
    form_class = modelform_factory(model, form=type('_Base', bases, {}), fields=fields)
    if with_slug and 'slug' in form_class.base_fields:
        form_class.base_fields['slug'].required = False
        form_class.base_fields['slug'].help_text = (
            'Sahifa manzili. Bo‘sh qoldiring — tizim nomdan o‘zi yasaydi.')

    # Tushuntirish faqat modelda yozilmagan joyga qo'yiladi.
    for name, field in form_class.base_fields.items():
        if not field.help_text and name in FIELD_HINTS:
            field.help_text = FIELD_HINTS[name]
    return form_class


class OrderStatusForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = ('status', 'comment')
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}


class LeadStatusForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Lead
        fields = ('status', 'handled_by', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mas'ul faqat xodimlar orasidan tanlanadi.
        self.fields['handled_by'].queryset = get_user_model().objects.filter(is_staff=True)
