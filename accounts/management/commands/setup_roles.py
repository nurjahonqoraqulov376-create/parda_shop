from django.core.management.base import BaseCommand

from accounts.roles import ensure_roles


class Command(BaseCommand):
    help = 'Menejer va Administrator guruhlarini yaratadi hamda ruxsatlarni yangilaydi.'

    def handle(self, *args, **options):
        manager, admin_group = ensure_roles()
        self.stdout.write(self.style.SUCCESS(
            f'Guruhlar tayyor: {manager.name} ({manager.permissions.count()} ruxsat), '
            f'{admin_group.name} ({admin_group.permissions.count()} ruxsat)'
        ))
