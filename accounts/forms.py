from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class StaffLoginForm(AuthenticationForm):
    """Boshqaruv paneliga kirish — faqat xodimlar uchun."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Login yoki parol noto‘g‘ri.',
        'inactive': 'Bu hisob faol emas.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Login'
        self.fields['password'].label = 'Parol'
        for field in self.fields.values():
            field.widget.attrs['class'] = 'field'

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError('Sizda boshqaruv paneliga ruxsat yo‘q.', code='no_access')


class StaffUserForm(forms.ModelForm):
    """Yangi xodim yaratish yoki mavjudini tahrirlash (rol, telefon, parol)."""

    role = forms.ChoiceField(label='Rol', choices=Profile.ROLES)
    phone = forms.CharField(label='Telefon', max_length=30, required=False)
    password1 = forms.CharField(label='Parol', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Parolni takrorlang', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        labels = {'username': 'Login', 'first_name': 'Ism', 'last_name': 'Familiya'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None) if self.instance.pk else None
        if profile:
            self.fields['role'].initial = profile.role
            self.fields['phone'].initial = profile.phone
        if self.instance.pk:
            self.fields['password1'].help_text = 'Bo‘sh qoldirsangiz parol o‘zgarmaydi.'
        else:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
        for name, field in self.fields.items():
            if name not in ('password1', 'password2'):
                field.widget.attrs['class'] = 'field'
            else:
                field.widget.attrs['class'] = 'field'

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', 'Parollar mos kelmadi.')
            elif len(password1) < 8:
                self.add_error('password1', 'Parol kamida 8 belgidan iborat bo‘lsin.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        user.save()
        Profile.objects.update_or_create(
            user=user,
            defaults={'role': self.cleaned_data['role'], 'phone': self.cleaned_data['phone']},
        )
        return user


class MyProfileForm(forms.ModelForm):
    """Xodim O'ZINING profilini tahrirlaydi.

    `StaffUserForm` dan farqi — bu yerda **rol yo'q**. Aks holda menejer
    o'ziga administrator rolini berib qo'ya olardi. Rolni faqat
    administrator, boshqa xodimning sahifasidan o'zgartiradi.

    Login ham o'zgarmaydi: u bilan kiriladi va boshqa yozuvlarda
    (buyurtma mas'uli, «kim qo'shgan») ishlatiladi.
    """

    phone = forms.CharField(label='Telefon', max_length=30, required=False)
    current_password = forms.CharField(
        label='Joriy parol', widget=forms.PasswordInput, required=False,
        help_text='Parolni o‘zgartirmoqchi bo‘lsangiz to‘ldiring.')
    password1 = forms.CharField(label='Yangi parol', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Yangi parolni takrorlang',
                                widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {'first_name': 'Ism', 'last_name': 'Familiya', 'email': 'Email'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        if profile:
            self.fields['phone'].initial = profile.phone
        for field in self.fields.values():
            field.widget.attrs['class'] = 'field'

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if not password1 and not password2:
            return cleaned

        # Parolni almashtirish uchun joriy parolni bilish shart: kimdir
        # ochiq qolgan sahifadan foydalanib parolni o'zgartirib ketmasin.
        current = cleaned.get('current_password')
        if not current or not self.instance.check_password(current):
            self.add_error('current_password', 'Joriy parol noto‘g‘ri.')
        elif password1 != password2:
            self.add_error('password2', 'Parollar mos kelmadi.')
        elif len(password1) < 8:
            self.add_error('password1', 'Parol kamida 8 belgidan iborat bo‘lsin.')
        return cleaned

    @property
    def password_changed(self):
        return bool(self.cleaned_data.get('password1'))

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        user.save()
        profile = getattr(user, 'profile', None)
        if profile:
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save(update_fields=['phone'])
        return user
