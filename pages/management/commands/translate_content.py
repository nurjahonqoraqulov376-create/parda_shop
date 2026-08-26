"""Bazadagi kontentning ruscha variantlarini o'zbekchasidan to'ldiradi.

Misollar:
    python manage.py translate_content            # hammasini qayta tarjima qiladi
    python manage.py translate_content --missing  # faqat bo'sh ruscha maydonlar
    python manage.py translate_content --model Banner FaqItem
"""

from django.core.management.base import BaseCommand, CommandError

from catalog.models import Category, Product
from pages.models import Advantage, Article, Banner, ContentBlock, FaqItem, Service, SiteSettings

MODELS = [Banner, Advantage, FaqItem, Service, Article, ContentBlock, SiteSettings, Category, Product]
BY_NAME = {model.__name__.lower(): model for model in MODELS}


class Command(BaseCommand):
    help = 'Kontentning `_ru` maydonlarini o‘zbekcha matndan avtomatik tarjima qiladi.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing', action='store_true',
            help='Faqat bo‘sh ruscha maydonlarni to‘ldiradi, mavjudlariga tegmaydi.',
        )
        parser.add_argument(
            '--model', nargs='+', metavar='NOM', default=None,
            help=f'Faqat shu modellar: {", ".join(sorted(BY_NAME))}',
        )

    def handle(self, *args, **options):
        models = MODELS
        if options['model']:
            models = []
            for name in options['model']:
                model = BY_NAME.get(name.lower())
                if model is None:
                    raise CommandError(f'Noma’lum model: {name}')
                models.append(model)

        missing_only = options['missing']
        total, failed = 0, 0

        for model in models:
            pairs = model.translatable_fields()
            if not pairs:
                continue
            for obj in model.objects.all():
                sources = {
                    source for source, target in pairs
                    if (getattr(obj, source, '') or '').strip()
                    and not (missing_only and (getattr(obj, target, '') or '').strip())
                }
                if not sources:
                    continue
                updated = obj.apply_auto_translation(only=sources)
                if not updated:
                    failed += 1
                    self.stderr.write(f'  ! {model.__name__} #{obj.pk} — tarjima olinmadi')
                    continue
                obj.save(update_fields=sorted(updated))
                total += 1
                self.stdout.write(f'  ✓ {model.__name__} #{obj.pk} — {len(updated)} maydon')

        summary = f'Tayyor: {total} ta yozuv tarjima qilindi.'
        if failed:
            summary += f' {failed} ta yozuvda tarjima olinmadi (tarmoqni tekshiring).'
        self.stdout.write(self.style.SUCCESS(summary))
