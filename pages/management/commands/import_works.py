"""Portfolio rasmlarini «Mening ishlarim» bo'limiga yuklaydi.

Ishlatish:
    py manage.py import_works                      # repodagi seed/works/ dan
    py manage.py import_works --dir "D:\rasmlar"  # boshqa papkadan

Sukut bo'lgan papka — loyihaning `seed/works/` si. U git'ga kiritilgan,
shuning uchun buyruq SERVERDA ham ishlaydi: portfolio disk tozalansa ham
qaytadan tiklanadi.

Papkadagi fayllar quyidagi nomlar bilan bo'lishi kerak (kengaytmasi ixtiyoriy:
.jpg, .jpeg, .png). Har bir nom uchun sarlavha, turi va tavsif shu faylda
oldindan yozilgan.

Buyruq qayta ishga tushirilsa yozuvlarni yangilaydi (slug bo'yicha), takror
yaratmaydi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from pages.models import Work

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')

# Rasmlar loyiha ichida ham saqlanadi: serverdagi `media/` disk tozalanishi
# mumkin, `seed/` esa kod bilan birga keladi.
DEFAULT_DIR = Path(settings.BASE_DIR) / 'seed' / 'works'

# Fayl nomi -> yozuv ma'lumotlari. Ruscha maydonlar saqlashda avtomatik
# tarjima qilinadi (`TranslatableMixin`), shuning uchun bu yerda yozilmaydi.
WORKS = [
    {
        'file': 'photo_2026-08-26_22-11-30',
        'slug': 'mehmonxona-jigarrang-baxmal',
        'title': 'Mehmonxona uchun jigarrang baxmal parda',
        'category': 'Baxmal parda',
        'excerpt': 'Keng mehmonxona devori bo‘ylab: zich jigarrang baxmal va o‘t naqshli oq tyul.',
        'description': (
            'Butun devorni egallagan keng deraza uchun tayyorlangan.\n\n'
            'Mato: jigarrang-pushti tusdagi zich baxmal, tik burmalar bilan tikilgan.\n'
            'Tyul: oq, pastki qismida o‘t-boshoq naqshi bor — kunduzi yorug‘likni '
            'yumshatib o‘tkazadi.\n\n'
            'Karniz: oltin bezakli, shift bo‘ylab butun devor uzunligida o‘rnatilgan, '
            'ichiga nuqtali yoritgichlar joylangan.\n'
            'Ushlagich: oltin sharchali osma bezak.\n\n'
            'Parda shiftdan polgacha tushirilgan — bu xonani balandroq ko‘rsatadi.'
        ),
        'sort_order': 1,
    },
    {
        'file': 'photo_2026-08-17_14-24-36',
        'slug': 'bej-kulrang-zamonaviy-parda',
        'title': 'Bej va kulrang zamonaviy parda',
        'category': 'Kombinatsiya parda',
        'excerpt': 'Ikki rang birga: to‘q kulrang asos va bej yon qismlar, o‘rtasida gulli oq tyul.',
        'description': (
            'Katta mehmonxonaning bir necha derazasi bir xil uslubda bezatilgan.\n\n'
            'Mato: to‘q kulrang asosiy parda va bej rangli yon qismlar. Bej qism '
            'yuqoridan qiya yig‘ilgan — bu deraza balandligini cho‘zib ko‘rsatadi.\n'
            'Tyul: oq, o‘rtasidan gul-novda naqshi o‘tgan.\n\n'
            'Karniz: oltin bezakli, shift plintusi bilan uyg‘un.\n'
            'Ushlagich: metall ilgak va kumush sharchali osma bezak.\n\n'
            'Neytral ranglar tufayli mebel almashsa ham parda o‘z o‘rnida qoladi.'
        ),
        'sort_order': 2,
    },
    {
        'file': 'photo_2026-08-14_14-25-46 (2)',
        'slug': 'kok-krem-qosh-rangli-parda',
        'title': 'To‘q ko‘k va krem qo‘sh rangli parda',
        'category': 'Kombinatsiya parda',
        'excerpt': 'To‘q ko‘k naqshli mato va krem yon qismlar, oralig‘ida naqshli oq tyul.',
        'description': (
            'Mehmonxona derazasi uchun ikki rangli yechim.\n\n'
            'Mato: to‘q ko‘k naqshli asosiy parda, chetlarida krem rangli qiya '
            'yig‘ilgan qismlar.\n'
            'Tyul: oq, ikki qator naqshli tasma bilan bezatilgan.\n\n'
            'Karniz: oltin bezakli, ikki pog‘onali shiftga o‘rnatilgan — shift '
            'chetidagi LED yoritgich pardani yumshoq yoritadi.\n'
            'Ushlagich: kumush popukli osma bezak.\n\n'
            'To‘q ko‘k rang quyoshni yaxshi to‘sadi, krem qism esa xonani '
            'og‘irlashtirmaydi.'
        ),
        'sort_order': 3,
    },
    {
        'file': 'photo_2026-08-14_14-14-50 (3)',
        'slug': 'boshoqli-tyul-bej-parda',
        'title': 'Boshoqli tyul bilan bej-kulrang parda',
        'category': 'Qo‘sh qatlam parda',
        'excerpt': 'Zich bej-kulrang parda va boshoq naqshli oq tyul — bir-birini to‘ldiruvchi juftlik.',
        'description': (
            'Yotoqxona derazasi uchun ikki qatlamli to‘plam.\n\n'
            'Mato: bej-kulrang, mayin tik chiziqli. Ikki tomonga qiya yig‘ilgan.\n'
            'Tyul: oq, ustki va pastki qismida boshoq naqshi — yorug‘lik tushganda '
            'naqsh yaqqol ko‘rinadi.\n\n'
            'Karniz: oltin bezakli, deraza kengligidan kengroq o‘rnatilgan.\n'
            'Ushlagich: oltin uchli popukli arqon.\n\n'
            'Parda yig‘ilganda deraza to‘liq ochiladi, yopilganda esa yorug‘lik '
            'butunlay to‘siladi.'
        ),
        'sort_order': 4,
    },
    {
        'file': 'photo_2026-08-17_14-26-47',
        'slug': 'yotoqxona-oq-gipyur-toplam',
        'title': 'Yotoqxona uchun oq gipyur to‘plam',
        'category': 'Tyul parda',
        'excerpt': 'Bitta xonadagi deraza va eshik bir xil oq gipyur matoda bezatilgan.',
        'description': (
            'Yotoqxonaning ikki ochilmasi — deraza va eshik — bir uslubda ishlangan.\n\n'
            'Mato: oq gipyur tyul, chetlari bo‘ylab barg naqshi bor. Derazadagi '
            'ichki qatlamda oltin rangli to‘r naqsh.\n\n'
            'Yig‘ilishi: ikkala tomondan yuqoriga qarab tortilgan — xonaga yumshoq '
            'yorug‘lik tushadi.\n\n'
            'Karniz: oltin bezakli, har bir ochilma uchun alohida.\n'
            'Ushlagich: oltin uchli popuk.\n\n'
            'Yengil mato xonani yopiq qilib qo‘ymaydi — kichik yotoqxona uchun '
            'ayni muddao.'
        ),
        'sort_order': 5,
    },
    {
        'file': 'photo_2026-08-14_14-25-46',
        'slug': 'eshik-kok-baxmal-parda',
        'title': 'Eshik uchun to‘q ko‘k baxmal parda',
        'category': 'Eshik pardasi',
        'excerpt': 'To‘q ko‘k baxmal, chetlari oq popuklar bilan bezatilgan eshik pardasi.',
        'description': (
            'Xonalar orasidagi eshik uchun tayyorlangan.\n\n'
            'Mato: to‘q ko‘k baxmal (shenil), mayda tik burmalar bilan tikilgan.\n\n'
            'Bezak: chetlari bo‘ylab oq popuklar tikilgan — to‘q fonda yaqqol '
            'ajralib turadi.\n\n'
            'Karniz: oltin bezakli, eshik ustidan kengroq o‘rnatilgan.\n'
            'Ushlagich: oq popukli arqon.\n\n'
            'Ikki tomonga simmetrik yig‘ilganda eshik ustida uchburchak ochilma '
            'hosil bo‘ladi.'
        ),
        'sort_order': 6,
    },
    {
        'file': 'photo_2026-08-17_14-24-35 (2)',
        'slug': 'balkon-eshigi-kulrang-parda',
        'title': 'Balkon eshigi uchun kulrang parda',
        'category': 'Eshik pardasi',
        'excerpt': 'Kulrang baxmal, chetlari kumush marjonli popuk bezak bilan ishlangan.',
        'description': (
            'Balkonga chiqadigan eshik uchun tayyorlangan.\n\n'
            'Mato: kulrang-lilak baxmal, zich va og‘ir — sovuqni ham to‘sadi.\n\n'
            'Bezak: chetlari bo‘ylab kumush marjonli popuklar tushirilgan.\n\n'
            'Karniz: oltin-kumush bezakli, shiftga yaqin o‘rnatilgan.\n'
            'Ushlagich: naqshli metall ilgak va yirik kumush popuk.\n\n'
            'Ikki tomonga yig‘ilganda eshikka to‘siqsiz chiqiladi.'
        ),
        'sort_order': 7,
    },
    {
        'file': 'photo_2026-08-14_14-14-50',
        'slug': 'kirish-eshigi-bej-parda',
        'title': 'Kirish eshigi uchun bej parda',
        'category': 'Eshik pardasi',
        'excerpt': 'Tik burmali bej parda, o‘rtasidan oltin popukli bezak tushirilgan.',
        'description': (
            'Kirish eshigi uchun tayyorlangan parda.\n\n'
            'Mato: bej-kulrang, mayda tik burmalar bilan tikilgan.\n\n'
            'Bezak: o‘rtadan pastga qarab oltin uchli popuklar tushirilgan — eshik '
            'yopiq turganda ham ko‘rinib turadi.\n\n'
            'Karniz: oltin bezakli, eshik kengligiga moslab o‘rnatilgan.\n'
            'Ushlagich: gulli oltin ilgak va uzun popukli arqon.\n\n'
            'Eshikni butunlay yopadi — sovuq va shovqinni kamaytiradi.'
        ),
        'sort_order': 8,
    },
]


class Command(BaseCommand):
    help = 'Portfolio rasmlarini «Mening ishlarim» bo‘limiga yuklaydi.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir', default=str(DEFAULT_DIR),
            help='Rasmlar turgan papka. Sukut bo‘yicha: seed/works/',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Hech narsa saqlanmaydi, faqat nima bo‘lishini ko‘rsatadi.',
        )
        parser.add_argument(
            '--in-order', action='store_true',
            help='Fayl nomlariga qaramaydi: papkadagi rasmlarni nomi bo‘yicha '
                 'saralab, ro‘yxat tartibida biriktiradi. Avval --dry-run bilan '
                 'moslikni tekshiring.',
        )

    def stem_variants(self, stem):
        """Bir xil rasmning turli nomlari.

        Brauzer yuklab olganda ikkinchi nusxaga «photo (2).jpg» deb nom beradi,
        Django esa saqlaganda uni «photo_2.jpg» ga aylantiradi. Ikkalasini ham
        tanishimiz kerak, aks holda papka almashganda rasm «topilmadi» bo'ladi.
        """
        variants = [stem]
        converted = re.sub(r'\s*\((\d+)\)$', r'_\1', stem)
        if converted != stem:
            variants.append(converted)
        return variants

    def find_image(self, folder, stem):
        for candidate_stem in self.stem_variants(stem):
            for suffix in IMAGE_SUFFIXES:
                for candidate in (folder / (candidate_stem + suffix),
                                  folder / (candidate_stem + suffix.upper())):
                    if candidate.exists():
                        return candidate
        return None

    def images_in_order(self, folder):
        """Papkadagi barcha rasmlar, nomi bo'yicha saralangan."""
        return sorted(
            (path for path in folder.iterdir()
             if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
            key=lambda path: path.name.lower(),
        )

    def handle(self, *args, **options):
        folder = Path(options['dir']).expanduser()
        if not folder.is_dir():
            raise CommandError('Papka topilmadi: %s' % folder)

        dry_run = options['dry_run']
        created = updated = missing = 0

        ordered = self.images_in_order(folder) if options['in_order'] else []
        if options['in_order']:
            if not ordered:
                raise CommandError('Papkada rasm topilmadi: %s' % folder)
            self.stdout.write('Tartib bo‘yicha biriktirilmoqda '
                              '(%d ta rasm, %d ta yozuv):' % (len(ordered), len(WORKS)))

        for index, item in enumerate(WORKS):
            if options['in_order']:
                image_path = ordered[index] if index < len(ordered) else None
            else:
                image_path = self.find_image(folder, item['file'])
            if image_path is None:
                missing += 1
                self.stderr.write(self.style.WARNING(
                    'Rasm topilmadi: %s.(jpg|jpeg|png) — «%s» o‘tkazib yuborildi.'
                    % (item['file'], item['title'])
                ))
                continue

            if dry_run:
                self.stdout.write('  [sinov] %s  <-  %s' % (item['title'], image_path.name))
                continue

            work, is_new = Work.objects.get_or_create(
                slug=item['slug'],
                defaults={'title': item['title'], 'image': 'works/%s' % image_path.name},
            )
            work.title = item['title']
            work.category = item['category']
            work.excerpt = item['excerpt']
            work.description = item['description']
            work.sort_order = item['sort_order']
            work.is_active = True

            # Django bir xil nomli fayl bo‘lsa `_a1b2c3` qo‘shib YANGI nusxa
            # yaratadi — buyruq qayta ishga tushirilganda `media/works/` papkasi
            # nusxalar bilan to‘lib ketardi. Nom barqaror qolishi uchun avval
            # eski faylni (va o‘sha manzildagi yetimni) o‘chiramiz.
            storage = work.image.storage
            target = 'works/%s' % image_path.name
            for stale in {work.image.name, target}:
                if stale and storage.exists(stale):
                    storage.delete(stale)
            with image_path.open('rb') as handle:
                work.image.save(image_path.name, File(handle), save=False)
            work.save()

            created += is_new
            updated += not is_new
            self.stdout.write(self.style.SUCCESS(
                '  %s  %s' % ('+' if is_new else '~', item['title'])
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Yangi: %d · Yangilandi: %d · Rasmi topilmadi: %d' % (created, updated, missing)
        ))
        if missing:
            self.stdout.write('Kutilgan fayl nomlari: %s'
                              % ', '.join(item['file'] for item in WORKS))
