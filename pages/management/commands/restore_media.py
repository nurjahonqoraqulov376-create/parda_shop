"""Yo'qolgan rasm fayllarini `seed/` papkasidan tiklaydi.

Nima uchun kerak
----------------
Railway'da rasm fayllari alohida ulanadigan diskda (volume) turadi, baza esa
Postgres'da. Ikkalasining umri boshqa-boshqa:

* **Pre-deploy buyruqlari alohida konteynerda ishlaydi va u yerda disk
  ULANMAGAN.** Shu sababli `import_works` pre-deploy'da ishga tushirilsa,
  bazaga yozuv tushadi, rasm esa vaqtinchalik konteyner bilan birga yo'qoladi
  — saytda barcha `/media/...` manzillari 404 qaytaradi.
* Disk almashtirilsa yoki tozalansa ham xuddi shu holat yuzaga keladi.

Bu buyruq **ishga tushish paytida** (start command) bajariladi — o'sha
konteynerda disk ulangan bo'ladi. U faqat **yo'q** fayllarni tiklaydi:
matnlarga, narxlarga, paneldan kiritilgan o'zgarishlarga tegmaydi.

Hech qachon xato bilan to'xtamaydi: ishga tushish shu buyruq sababli
buzilmasligi kerak.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from catalog.models import Category
from pages.management.commands.import_works import WORKS
from pages.models import Work

SEED_DIR = Path(settings.BASE_DIR) / 'seed'
SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')

# Portfolio yozuvining slug'i -> `seed/works/` dagi fayl nomi (kengaytmasiz).
WORK_FILES = {item['slug']: item['file'] for item in WORKS}


def find_seed_file(folder, stem):
    """`seed/<folder>/<stem>.<kengaytma>` faylini topadi."""
    directory = SEED_DIR / folder
    for candidate_stem in (stem, stem.replace(' (', '_').replace(')', '')):
        for suffix in SUFFIXES:
            path = directory / (candidate_stem + suffix)
            if path.exists():
                return path
    return None


class Command(BaseCommand):
    help = 'Yo‘qolgan media fayllarini seed/ papkasidan tiklaydi (xato bermaydi).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Hech narsa yozilmaydi, faqat nima tiklanishi ko‘rsatiladi.',
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        restored = missing = 0

        pairs = [
            ('works', ((work, WORK_FILES.get(work.slug)) for work in Work.objects.all())),
            ('categories', ((category, category.slug) for category in Category.objects.all())),
        ]

        for folder, items in pairs:
            for obj, stem in items:
                if not obj.image:
                    continue
                target = media_root / obj.image.name
                if target.exists():
                    continue
                source = find_seed_file(folder, stem) if stem else None
                if source is None:
                    missing += 1
                    self.stdout.write(self.style.WARNING(
                        'restore_media: nusxa topilmadi — %s' % obj.image.name
                    ))
                    continue
                if options['dry_run']:
                    self.stdout.write('  [sinov] %s  <-  %s' % (obj.image.name, source.name))
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                restored += 1

        if restored or missing:
            self.stdout.write(self.style.SUCCESS(
                'restore_media: %d ta fayl tiklandi, %d tasiga nusxa topilmadi.'
                % (restored, missing)
            ))
        else:
            self.stdout.write('restore_media: barcha rasmlar joyida.')
