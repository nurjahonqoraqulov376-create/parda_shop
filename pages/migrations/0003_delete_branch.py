from django.db import migrations


class Migration(migrations.Migration):
    """Filiallar bo'limi olib tashlandi."""

    dependencies = [
        ('pages', '0002_alter_sitesettings_phone_primary'),
    ]

    operations = [
        migrations.DeleteModel(name='Branch'),
    ]
