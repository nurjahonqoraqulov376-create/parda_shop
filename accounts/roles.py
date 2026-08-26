"""Rollarga mos Django guruhlari va ruxsatlarini yaratish."""

from django.contrib.auth.models import Group, Permission

# Menejer boshqara oladigan modellar (view/add/change; o'chirish yo'q)
MANAGER_MODELS = [
    ('catalog', 'product'),
    ('catalog', 'category'),
    ('catalog', 'productimage'),
    ('orders', 'order'),
    ('orders', 'orderitem'),
    ('orders', 'lead'),
]
MANAGER_ACTIONS = ('view', 'add', 'change')

# Administrator to'liq boshqaradigan app'lar
ADMIN_APPS = ('catalog', 'orders', 'pages', 'accounts')

GROUP_MANAGER = 'Menejer'
GROUP_ADMIN = 'Administrator'


def ensure_roles():
    """Guruhlarni yaratadi va ruxsatlarni yangilaydi (idempotent)."""
    manager, _ = Group.objects.get_or_create(name=GROUP_MANAGER)
    admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)

    manager_codenames = [
        f'{action}_{model}' for app, model in MANAGER_MODELS for action in MANAGER_ACTIONS
    ]
    manager_perms = Permission.objects.filter(
        content_type__app_label__in={app for app, _ in MANAGER_MODELS},
        codename__in=manager_codenames,
    )
    if manager_perms.exists():
        manager.permissions.set(manager_perms)

    admin_perms = Permission.objects.filter(content_type__app_label__in=ADMIN_APPS)
    if admin_perms.exists():
        admin_group.permissions.set(admin_perms)

    return manager, admin_group
