from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Xodim profili. Profil bor foydalanuvchi — boshqaruv paneliga kira oladi."""

    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'
    ROLES = [
        (ROLE_MANAGER, 'Menejer'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField('Telefon raqami', max_length=30, blank=True)
    role = models.CharField('Rol', max_length=20, choices=ROLES, default=ROLE_MANAGER)

    class Meta:
        verbose_name = 'Xodim profili'
        verbose_name_plural = 'Xodim profillari'

    def __str__(self):
        return self.user.get_username()

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN
