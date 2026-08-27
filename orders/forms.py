from django import forms
from django.utils.translation import get_language

from parda_shop.regions import district_choices
from parda_shop.translations import translate

from .models import Lead, Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('full_name', 'phone', 'region', 'address', 'comment')
        widgets = {
            # Telefonda mos klaviatura ochilishi va avtoto'ldirish ishlashi uchun.
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Ism-familiyangiz', 'autocomplete': 'name',
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+998 90 123 45 67', 'type': 'tel',
                'inputmode': 'tel', 'autocomplete': 'tel',
            }),
            'region': forms.Select(),
            'address': forms.Textarea(attrs={
                'rows': 3, 'placeholder': 'Ko‘cha, uy, xonadon',
                'autocomplete': 'street-address',
            }),
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Qo‘shimcha izoh (ixtiyoriy)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tuman nomlari joriy tilda ko'rsatiladi (bazaga qiymat yoziladi).
        self.fields['region'].choices = district_choices(get_language())


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ('name', 'phone', 'message', 'lead_type')
        widgets = {
            'lead_type': forms.HiddenInput(),
            'message': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        digits = [ch for ch in phone if ch.isdigit()]
        if len(digits) < 7:
            raise forms.ValidationError(translate('lead.error', get_language()))
        return phone
