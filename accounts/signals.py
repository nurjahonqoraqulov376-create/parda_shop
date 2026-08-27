from django.contrib.auth.models import Group
from django.db.models.signals import post_delete, post_migrate, post_save
from django.dispatch import receiver

from .models import Profile
from .roles import GROUP_ADMIN, GROUP_MANAGER, GROUP_SUPPORT, ensure_roles

GROUP_BY_ROLE = {
    Profile.ROLE_SUPPORT: GROUP_SUPPORT,
    Profile.ROLE_MANAGER: GROUP_MANAGER,
    Profile.ROLE_ADMIN: GROUP_ADMIN,
}


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    """Migratsiyadan keyin guruh va ruxsatlarni tayyorlaydi.

    Har bir app uchun chaqiriladi — oxirgi chaqiruv barcha ruxsatlar
    yaratilgandan keyin bo'lgani uchun to'liq ro'yxat o'rnatiladi.
    """
    ensure_roles()


def _apply_group(user, target_group):
    for group_name in GROUP_BY_ROLE.values():
        group = Group.objects.filter(name=group_name).first()
        if group is None:
            continue
        if group_name == target_group:
            user.groups.add(group)
        else:
            user.groups.remove(group)


def _set_staff(user, should_be_staff):
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        user.save(update_fields=['is_staff'])


@receiver(post_save, sender=Profile)
def sync_role_with_groups(sender, instance, **kwargs):
    """Profil roli o'zgarganda Django guruhlari va `is_staff` ni moslashtiradi."""
    _apply_group(instance.user, GROUP_BY_ROLE.get(instance.role))
    _set_staff(instance.user, True)


@receiver(post_delete, sender=Profile)
def revoke_staff_access(sender, instance, **kwargs):
    """Profil o'chirilganda foydalanuvchi xodimlikdan chiqariladi."""
    user = instance.user
    if user.pk is None:  # foydalanuvchining o'zi o'chirilyapti
        return
    _apply_group(user, None)
    _set_staff(user, user.is_superuser)
