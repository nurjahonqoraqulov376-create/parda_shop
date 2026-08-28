"""Administrator hisobini muhit o'zgaruvchilaridan yaratadi yoki yangilaydi.

Serverda `createsuperuser` ni qo'lda ishga tushirish uchun terminal kerak
bo'ladi — Railway'da bu SSH kalit yoki brauzerdagi Console orqali bo'ladi.
Bu buyruq esa joylashtirish paytida o'zi bajariladi.

Ishlatish (Railway -> Variables):
    ADMIN_USERNAME=Sevara
    ADMIN_PASSWORD=<parol>
    ADMIN_EMAIL=<ixtiyoriy>

O'zgaruvchilar yo'q bo'lsa buyruq HECH NARSA QILMAYDI va xato bermaydi —
shuning uchun uni pre-deploy'da doim qoldirish xavfsiz.

Parol o'rnatilgach `ADMIN_PASSWORD` ni Railway'dan O'CHIRIB TASHLANG:
o'zgaruvchilarda ochiq matnda turishi kerak emas.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'ADMIN_USERNAME / ADMIN_PASSWORD dan administrator hisobini yaratadi.'

    def handle(self, *args, **options):
        username = (os.environ.get('ADMIN_USERNAME') or '').strip()
        password = os.environ.get('ADMIN_PASSWORD') or ''

        if not username or not password:
            self.stdout.write('ensure_admin: ADMIN_USERNAME/ADMIN_PASSWORD yo‘q — o‘tkazib yuborildi.')
            return

        email = (os.environ.get('ADMIN_EMAIL') or '').strip()
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        user.set_password(password)
        user.save()

        Profile.objects.update_or_create(user=user, defaults={'role': Profile.ROLE_ADMIN})

        self.stdout.write(self.style.SUCCESS(
            'ensure_admin: %s — %s (administrator)'
            % (username, 'yaratildi' if created else 'paroli yangilandi')
        ))
        if len(password) < 12:
            self.stdout.write(self.style.WARNING(
                'ensure_admin: parol qisqa (%d belgi). Kuchliroq parolga almashtiring.'
                % len(password)
            ))
