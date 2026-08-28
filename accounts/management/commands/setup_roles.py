from django.core.management.base import BaseCommand

from accounts.roles import ensure_roles


class Command(BaseCommand):
    help = 'Support, Menejer va Administrator guruhlarini yaratadi hamda ruxsatlarni yangilaydi.'

    def handle(self, *args, **options):
        # `ensure_roles()` guruhlar ro'yxatini qaytaradi. Yangi rol qo'shilganda
        # bu yer o'zgarmasligi uchun ochiq sondagi qiymat sifatida olamiz —
        # ilgari aynan shu joyda `manager, admin_group = ...` deb ikkitaga
        # ajratilgani uchun Support roli qo'shilgach buyruq ishlamay qolgandi.
        groups = ensure_roles()
        for group in groups:
            self.stdout.write(self.style.SUCCESS(
                '%s — %d ruxsat' % (group.name, group.permissions.count())
            ))
        self.stdout.write(self.style.SUCCESS('Guruhlar tayyor: %d ta' % len(groups)))
