from django.db import migrations, models


def convert_customer_profiles(apps, schema_editor):
    """Mijoz rolini olib tashlash: xodimlarni moslab, mijoz profillarini o'chirish."""
    Profile = apps.get_model('accounts', 'Profile')
    for profile in Profile.objects.select_related('user'):
        user = profile.user
        if not user.is_staff:
            # Endi kira olmaydigan eski mijoz akkaunti — profil kerak emas.
            profile.delete()
        elif profile.role == 'customer':
            profile.role = 'admin' if user.is_superuser else 'manager'
            profile.save(update_fields=['role'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_profile_role'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'Xodim profili', 'verbose_name_plural': 'Xodim profillari'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('manager', 'Menejer'), ('admin', 'Administrator')],
                default='manager',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
        migrations.RunPython(convert_customer_profiles, noop),
    ]
