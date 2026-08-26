from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'Profil', 'verbose_name_plural': 'Profillar'},
        ),
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('customer', 'Mijoz'), ('manager', 'Menejer'), ('admin', 'Administrator')],
                default='customer',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
    ]
