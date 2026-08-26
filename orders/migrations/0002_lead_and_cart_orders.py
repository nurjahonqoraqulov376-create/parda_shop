import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Mehmon buyurtmasi, savat maydonlari va `Lead` modeli."""

    dependencies = [
        ('orders', '0001_initial'),
        ('catalog', '0002_product_and_content_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(model_name='orderitem', old_name='curtain', new_name='product'),
        migrations.AlterModelOptions(
            name='order',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Buyurtma',
                'verbose_name_plural': 'Buyurtmalar',
            },
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'verbose_name': 'Buyurtma qatori', 'verbose_name_plural': 'Buyurtma qatorlari'},
        ),
        migrations.AddField(
            model_name='order',
            name='region',
            field=models.CharField(blank=True, max_length=120, verbose_name='Shahar / viloyat'),
        ),
        migrations.AddField(
            model_name='order',
            name='comment',
            field=models.TextField(blank=True, verbose_name='Izoh'),
        ),
        migrations.AddField(
            model_name='order',
            name='total_amount',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=14, verbose_name='Jami summa'),
        ),
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Foydalanuvchi',
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'Yangi'),
                    ('confirmed', 'Tasdiqlangan'),
                    ('done', 'Yetkazildi'),
                    ('cancelled', 'Bekor qilindi'),
                ],
                default='new',
                max_length=20,
                verbose_name='Holat',
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='catalog.product',
                verbose_name='Mahsulot',
            ),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='quantity',
            field=models.PositiveIntegerField(verbose_name='Miqdor'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='price',
            field=models.DecimalField(decimal_places=0, max_digits=12, verbose_name='Narxi'),
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Ism')),
                ('phone', models.CharField(max_length=30, verbose_name='Telefon')),
                ('message', models.TextField(blank=True, verbose_name='Xabar')),
                ('lead_type', models.CharField(
                    choices=[
                        ('callback', 'Qo‘ng‘iroqni so‘rash'),
                        ('consultation', 'Bepul konsultatsiya'),
                        ('discount', '10% chegirma'),
                        ('measure', 'Bepul o‘lchov'),
                        ('order', 'Buyurtma so‘rovi'),
                        ('contact', 'Aloqa formasi'),
                    ],
                    default='callback', max_length=20, verbose_name='Ariza turi',
                )),
                ('status', models.CharField(
                    choices=[
                        ('new', 'Yangi'),
                        ('in_progress', 'Ishlanmoqda'),
                        ('done', 'Bajarildi'),
                        ('rejected', 'Rad etilgan'),
                    ],
                    default='new', max_length=20, verbose_name='Holat',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan')),
                ('handled_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='handled_leads',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Mas’ul',
                )),
            ],
            options={
                'verbose_name': 'So‘rov',
                'verbose_name_plural': 'So‘rovlar',
                'ordering': ['-created_at'],
            },
        ),
    ]
