"""Portfolio rasmlarini «Mening ishlarim» bo'limiga yuklaydi.

Ishlatish:
    py manage.py import_works --dir "C:\\Users\\Админ\\Desktop\\parda-rasmlar"

Papkadagi fayllar quyidagi nomlar bilan bo'lishi kerak (kengaytmasi ixtiyoriy:
.jpg, .jpeg, .png). Har bir nom uchun sarlavha, turi va tavsif shu faylda
oldindan yozilgan.

Buyruq qayta ishga tushirilsa yozuvlarni yangilaydi (slug bo'yicha), takror
yaratmaydi.
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from pages.models import Work

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')

# Fayl nomi -> yozuv ma'lumotlari. Ruscha maydonlar saqlashda avtomatik
# tarjima qilinadi (`TranslatableMixin`), shuning uchun bu yerda yozilmaydi.
WORKS = [
    {
        'file': 'mehmonxona-baxmal',
        'slug': 'mehmonxona-baxmal-parda',
        'title': 'Mehmonxona uchun jigarrang baxmal parda',
        'category': 'Baxmal parda',
        'excerpt': 'Keng mehmonxona derazasi uchun qo‘sh qatlam: zich baxmal parda '
                   'va yengil oq tyul.',
        'description': (
            'Mehmonxonaning butun devorini egallagan keng deraza uchun tayyorlangan.\n\n'
            'Mato: jigarrang-kulrang tusdagi zich baxmal. Ichki qatlam — naqshli oq tyul, '
            'u kunduzi yorug‘likni yumshatib o‘tkazadi.\n\n'
            'Karniz: oltin rangli bezakli, shift bo‘ylab butun devor uzunligida.\n'
            'Ushlagich: oltin sharchali osma bezak.\n\n'
            'Parda shiftdan polgacha tushirilgan — bu xonani balandroq ko‘rsatadi.'
        ),
        'sort_order': 1,
    },
    {
        'file': 'eshik-popukli',
        'slug': 'eshik-popukli-bej-parda',
        'title': 'Eshik uchun popukli bej parda',
        'category': 'Eshik pardasi',
        'excerpt': 'Ikki tomonga yig‘iladigan bej parda, chetlari popukli bezak bilan '
                   'ishlangan.',
        'description': (
            'Xonalar orasidagi eshik uchun tayyorlangan bezakli parda.\n\n'
            'Mato: bej-kulrang baxmal, tik burmalar bilan tikilgan.\n\n'
            'Bezak: chetlari bo‘ylab oltin uchli oq popuklar — pardaning asosiy '
            'ko‘rki shu.\n\n'
            'Ushlagich: devorga o‘rnatilgan oltin gulli ilgak va uzun popukli arqon.\n\n'
            'Ikki tomonga simmetrik yig‘ilganda eshik ustida uchburchak ochilma hosil '
            'bo‘ladi.'
        ),
        'sort_order': 2,
    },
    {
        'file': 'kok-jakkard',
        'slug': 'kok-jakkard-parda',
        'title': 'To‘q ko‘k naqshli jakkard parda',
        'category': 'Jakkard parda',
        'excerpt': 'To‘q ko‘k jakkard mato, oq va ko‘k popuklar bilan bezatilgan.',
        'description': (
            'To‘q ko‘k rangdagi jakkard parda — mato ustida oq mayin naqsh bor.\n\n'
            'Osma turi: halqali (lyuvers) — oltin halqalar karnizga o‘tkazilgan, '
            'burmalar bir tekis tushadi.\n\n'
            'Bezak: chetlari bo‘ylab ko‘k va oq popuklar navbat bilan tikilgan.\n\n'
            'Orqa qatlam: naqshli bej tyul.\n\n'
            'To‘q rang xonani quyoshdan yaxshi to‘saydi — yotoqxona uchun mos.'
        ),
        'sort_order': 3,
    },
    {
        'file': 'bej-kulrang',
        'slug': 'bej-kulrang-qosh-parda',
        'title': 'Bej va kulrang qo‘sh rangli parda',
        'category': 'Kombinatsiya parda',
        'excerpt': 'Ikki rang birga: chetlari bej, o‘rtasi kulrang, oralig‘ida gulli '
                   'oq tyul.',
        'description': (
            'Ikki rangli kombinatsiya: to‘q kulrang asosiy parda va bej rangli '
            'yon qismlar.\n\n'
            'Tyul: oq, o‘rtasidan gul-novda naqshi o‘tgan — yorug‘lik tushganda naqsh '
            'yaqqol ko‘rinadi.\n\n'
            'Karniz: oltin bezakli, shift plintusi bilan uyg‘un.\n'
            'Ushlagich: metall ilgak va kumush sharchali osma bezak.\n\n'
            'Bej qism yuqoridan pastga qiya yig‘ilgan — bu deraza balandligini '
            'cho‘zib ko‘rsatadi.'
        ),
        'sort_order': 4,
    },
    {
        'file': 'yotoqxona-tyul',
        'slug': 'yotoqxona-gipyur-tyul',
        'title': 'Yotoqxona uchun oq gipyur tyul',
        'category': 'Tyul parda',
        'excerpt': 'Yengil oq gipyur tyul — bitta xonadagi deraza va eshik uchun '
                   'bir uslubda.',
        'description': (
            'Yotoqxonaning ikki ochilmasi — deraza va eshik — bir xil matoda '
            'bezatilgan.\n\n'
            'Mato: oq gipyur tyul, chetlari bo‘ylab barg naqshi bor.\n\n'
            'Karniz: oltin bezakli, ikkala ochilma uchun alohida o‘rnatilgan.\n'
            'Ushlagich: oltin uchli popukli arqon.\n\n'
            'Yengil mato xonani yopiq qilib qo‘ymaydi — kichik yotoqxona uchun ayni '
            'muddao.'
        ),
        'sort_order': 5,
    },
    {
        'file': 'eshik-bej',
        'slug': 'eshik-bej-parda',
        'title': 'Xona eshigi uchun bej parda',
        'category': 'Eshik pardasi',
        'excerpt': 'Tik burmali bej parda, o‘rtasidan oltin popukli bezak tushirilgan.',
        'description': (
            'Kirish eshigi uchun tayyorlangan parda.\n\n'
            'Mato: bej-kulrang, mayda tik burmalar bilan tikilgan.\n\n'
            'Bezak: o‘rtadan pastga qarab oltin uchli popuklar tushirilgan.\n\n'
            'Karniz: oltin bezakli, eshik kengligiga moslab o‘rnatilgan.\n'
            'Ushlagich: gulli oltin ilgak va popukli arqon.\n\n'
            'Eshikni butunlay yopadi — sovuq va shovqinni ham kamaytiradi.'
        ),
        'sort_order': 6,
    },
]


class Command(BaseCommand):
    help = 'Portfolio rasmlarini «Mening ishlarim» bo‘limiga yuklaydi.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir', required=True,
            help='Rasmlar turgan papka (fayl nomlari quyida ko‘rsatilgan).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Hech narsa saqlanmaydi, faqat nima bo‘lishini ko‘rsatadi.',
        )

    def find_image(self, folder, stem):
        for suffix in IMAGE_SUFFIXES:
            for candidate in (folder / (stem + suffix), folder / (stem + suffix.upper())):
                if candidate.exists():
                    return candidate
        return None

    def handle(self, *args, **options):
        folder = Path(options['dir']).expanduser()
        if not folder.is_dir():
            raise CommandError('Papka topilmadi: %s' % folder)

        dry_run = options['dry_run']
        created = updated = missing = 0

        for item in WORKS:
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
