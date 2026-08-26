import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """`Curtain` modelini `Product` ga aylantiradi va kontent maydonlarini qo'shadi."""

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(old_name='Curtain', new_name='Product'),
        migrations.RenameField(model_name='product', old_name='active', new_name='is_active'),
        migrations.AlterModelOptions(
            name='category',
            options={
                'ordering': ['sort_order', 'name'],
                'verbose_name': 'Kategoriya',
                'verbose_name_plural': 'Kategoriyalar',
            },
        ),
        migrations.AlterModelOptions(
            name='product',
            options={
                'ordering': ['sort_order', '-created_at'],
                'verbose_name': 'Mahsulot',
                'verbose_name_plural': 'Mahsulotlar',
            },
        ),
        # --- Category ---
        migrations.AddField(
            model_name='category',
            name='name_ru',
            field=models.CharField(blank=True, max_length=120, verbose_name='Nomi (ru)'),
        ),
        migrations.AddField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True, verbose_name='Tavsif'),
        ),
        migrations.AddField(
            model_name='category',
            name='description_ru',
            field=models.TextField(blank=True, verbose_name='Tavsif (ru)'),
        ),
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, upload_to='categories/', verbose_name='Rasm'),
        ),
        migrations.AddField(
            model_name='category',
            name='icon',
            field=models.CharField(blank=True, max_length=8, verbose_name='Ikon (emoji)'),
        ),
        migrations.AddField(
            model_name='category',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, verbose_name='Tartib'),
        ),
        migrations.AddField(
            model_name='category',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktiv'),
        ),
        migrations.AddField(
            model_name='category',
            name='show_on_home',
            field=models.BooleanField(default=False, verbose_name='Bosh sahifada bo‘lim sifatida'),
        ),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(unique=True, verbose_name='Slug'),
        ),
        # --- Product ---
        migrations.AddField(
            model_name='product',
            name='name_ru',
            field=models.CharField(blank=True, max_length=160, verbose_name='Nomi (ru)'),
        ),
        migrations.AddField(
            model_name='product',
            name='sku',
            field=models.CharField(blank=True, max_length=40, verbose_name='Artikul'),
        ),
        migrations.AddField(
            model_name='product',
            name='short_description_ru',
            field=models.CharField(blank=True, max_length=240, verbose_name='Qisqa tavsif (ru)'),
        ),
        migrations.AddField(
            model_name='product',
            name='description_ru',
            field=models.TextField(blank=True, verbose_name='To‘liq tavsif (ru)'),
        ),
        migrations.AddField(
            model_name='product',
            name='old_price',
            field=models.DecimalField(
                blank=True, decimal_places=0, max_digits=12, null=True, verbose_name='Eski narxi'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='is_featured',
            field=models.BooleanField(default=False, verbose_name='Tanlangan (ommabop)'),
        ),
        migrations.AddField(
            model_name='product',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, verbose_name='Tartib'),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='catalog.category',
                verbose_name='Kategoriya',
            ),
        ),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(unique=True, verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, upload_to='curtains/', verbose_name='Asosiy rasm'),
        ),
        migrations.AlterField(
            model_name='product',
            name='short_description',
            field=models.CharField(max_length=240, verbose_name='Qisqa tavsif'),
        ),
        migrations.AlterField(
            model_name='product',
            name='description',
            field=models.TextField(verbose_name='To‘liq tavsif'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=0, max_digits=12, verbose_name='Narxi'),
        ),
        migrations.AlterField(
            model_name='product',
            name='stock',
            field=models.PositiveIntegerField(default=0, verbose_name='Ombordagi soni'),
        ),
        migrations.AlterField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktiv'),
        ),
        # --- ProductImage ---
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='curtains/gallery/', verbose_name='Rasm')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Tartib')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='images',
                    to='catalog.product',
                    verbose_name='Mahsulot',
                )),
            ],
            options={
                'verbose_name': 'Mahsulot rasmi',
                'verbose_name_plural': 'Mahsulot rasmlari',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
