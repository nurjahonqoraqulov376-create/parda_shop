"""Demo kontent bilan bazani to'ldiradi (bir necha marta ishga tushirish xavfsiz)."""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from accounts.roles import ensure_roles
from catalog.models import Category, Product
from pages.models import (
    Advantage, Article, Banner, Client, ContentBlock, FaqItem, Service, SiteSettings, Testimonial,
)
from parda_shop import mt

CONTACT_PHONE = '+998 99 986 71 99'

# Kategoriya rasmlari kod bilan birga keladi: serverdagi `media/` disk
# tozalanishi mumkin, `seed/` esa har joylashtirishda qaytadan yetkaziladi.
SEED_CATEGORY_DIR = Path(settings.BASE_DIR) / 'seed' / 'categories'

# `add_arguments` ichida sinf maydoniga murojaat qilib bo'lmaydi.
SAFE_PARTS_KEYS = ('advantages', 'banners', 'categories', 'content', 'services')

# (slug, nomi, nomi_ru, ikon, bosh sahifada, tavsif, tavsif_ru)
CATEGORIES = [
    ('plisse-jalyuzi', 'Plisse jalyuzi', 'Плиссе жалюзи', '▤', True,
     'Burmali mato — derazani teshmasdan o‘rnatiladi va nostandart shakldagi derazalarga ham moslashadi.',
     'Плиссированная ткань — крепится без сверления и подходит даже для нестандартных окон.'),
    ('rulon-pardalar', 'Rulon pardalar', 'Рулонные шторы', '▥', True,
     'Valga o‘raladigan eng amaliy yechim: kam joy egallaydi, oson tozalanadi, har qanday xonaga mos.',
     'Самое практичное решение на валу: занимает мало места, легко чистится, подходит любой комнате.'),
    ('kun-tun-combo', 'Kun-tun combo jalyuzi', 'Жалюзи день-ночь', '◫', True,
     'Ikki qatlamli mato yorug‘likni bir harakat bilan kerakli darajaga sozlash imkonini beradi.',
     'Двухслойная ткань позволяет одним движением настроить нужный уровень света.'),
    ('zamonaviy-pardalar', 'Zamonaviy pardalar', 'Современные шторы', '❋', True,
     'Minimalistik interyer uchun to‘q va yengil matolar: baxmal, zig‘ir, ikki qatlamli to‘plamlar.',
     'Плотные и лёгкие ткани для минималистичного интерьера: велюр, лён, двухслойные комплекты.'),
    ('rim-pardalari', 'Rim pardalari', 'Римские шторы', '▦', False,
     'Ko‘tarilganda tekis burmalar hosil qiladi — kichik va o‘rta derazalar uchun nafis yechim.',
     'При подъёме собирается в ровные складки — изящное решение для небольших и средних окон.'),
    ('klassik-pardalar', 'Klassik pardalar', 'Классические шторы', '❖', False,
     'Tul, portyera va lambreken: mehmonxona va yotoqxonaga tantanavor ko‘rinish beradi.',
     'Тюль, портьера и ламбрекен: придают гостиной и спальне торжественный вид.'),
    ('tekstil-jalyuzi', 'Tekstil (vertikal) jalyuzilar', 'Текстильные вертикальные жалюзи', '▩', False,
     'Vertikal lamellar keng va baland derazalar hamda ofis xonalari uchun eng qulay variant.',
     'Вертикальные ламели — удобный вариант для широких и высоких окон и офисов.'),
    ('yogoch-jalyuzi', 'Yog‘och jalyuzilar', 'Деревянные жалюзи', '▨', False,
     'Tabiiy lipa va bambukdan: xonaga issiq, qimmatbaho ko‘rinish beradi.',
     'Из натуральной липы и бамбука: придают комнате тёплый, дорогой вид.'),
    ('alyuminiy-jalyuzi', 'Alyuminiy gorizontal jalyuzilar', 'Алюминиевые горизонтальные жалюзи', '▤', False,
     'Namlik va haroratga chidamli, oshxona, vanna va ofis uchun eng arzon yechim.',
     'Устойчивы к влаге и температуре — самое доступное решение для кухни, ванной и офиса.'),
    ('bambuk-jalyuzi', 'Bambuk jalyuzilar', 'Бамбуковые жалюзи', '⌗', False,
     'Tabiiy bambuk to‘qimasi yorug‘likni yumshoq tarqatadi va eko-uslubga mos keladi.',
     'Натуральное плетение бамбука мягко рассеивает свет и подходит эко-стилю.'),
    ('plastik-deraza-jalyuzi', 'Plastik derazalar uchun jalyuzi', 'Жалюзи для пластиковых окон', '▣', False,
     'To‘g‘ridan-to‘g‘ri stvorkaga o‘rnatiladi — deraza tokchasi bo‘sh qoladi, ochilishga xalaqit bermaydi.',
     'Крепятся прямо на створку — подоконник остаётся свободным, окно открывается свободно.'),
    ('logotipli-jalyuzi', 'Logotipli jalyuzilar', 'Жалюзи с логотипом', '◍', False,
     'Kompaniya logotipi bosilgan jalyuzilar — ofis, salon va do‘konlar uchun brend elementi.',
     'Жалюзи с печатью логотипа — элемент бренда для офиса, салона и магазина.'),
    ('fotosuratli-jalyuzi', 'Fotosuratli jalyuzilar', 'Фотожалюзи', '◪', False,
     'Yuqori aniqlikdagi bosma: tayyor manzaralar yoki o‘zingiz yuborgan rasm.',
     'Печать высокого разрешения: готовые сюжеты или ваше собственное изображение.'),
    ('moskit-torlari', 'Moskit to‘rlari', 'Москитные сетки', '▧', False,
     'Chivin va changdan himoya: ramkali, rulonli, plisse va magnitli variantlar.',
     'Защита от насекомых и пыли: рамочные, рулонные, плиссе и магнитные варианты.'),
]

# slug -> mahsulotlar ro'yxati
PRODUCTS = {
    'plisse-jalyuzi': [
        dict(slug='plisse-bianco', name='Plisse «Bianco»', name_ru='Плиссе «Bianco»',
             short='Sutdek oq burmali mato — yorug‘likni tarqatadi, lekin ko‘chadan ko‘rinishni to‘sadi.',
             short_ru='Молочно-белая плиссе — рассеивает свет, но закрывает вид с улицы.',
             desc='Eng ommabop bazaviy model. Mato zichligi o‘rtacha, shuning uchun xona kun bo‘yi yorug‘ '
                  'qoladi, ammo qo‘shni derazalardan ichkarisi ko‘rinmaydi.\n\n'
                  'Yuqori va pastki profil stvorkaga qisqich orqali mahkamlanadi — plastik derazani teshish shart emas.',
             desc_ru='Самая популярная базовая модель. Плотность средняя, поэтому днём в комнате светло, '
                     'но с соседних окон ничего не видно.\n\n'
                     'Верхний и нижний профиль крепятся на створку клипсами — сверлить пластик не нужно.',
             price=107_950, stock=24, featured=True),
        dict(slug='plisse-perla', name='Plisse «Perla» sadaf', name_ru='Плиссе «Perla» перламутр',
             short='Sadaf tovlanishli yarim shaffof mato, mehmonxona va oshxona uchun.',
             short_ru='Полупрозрачная ткань с перламутровым отливом для гостиной и кухни.',
             desc='Matoning yuzasi yorug‘likda mayin tovlanadi va xonaga jonli tus beradi. '
                  'Oq, bej va kulrang tovlanishlar mavjud.\n\n'
                  'Qattiq changni ushlamaydigan qoplamasi bor — nam mato bilan artib turish yetarli.',
             desc_ru='Поверхность ткани мягко переливается на свету и оживляет интерьер. '
                     'Доступны белый, бежевый и серый отливы.\n\n'
                     'Есть покрытие, не удерживающее пыль — достаточно протирать влажной салфеткой.',
             price=124_500, old=139_000, stock=18),
        dict(slug='plisse-notte-blackout', name='Plisse «Notte» blackout', name_ru='Плиссе «Notte» блэкаут',
             short='Yorug‘likni deyarli to‘liq to‘sadi — yotoqxona va bolalar xonasi uchun.',
             short_ru='Почти полностью перекрывает свет — для спальни и детской.',
             desc='Ichki tomoni kumushrang qoplamali blackout mato yorug‘likning 95% dan ortig‘ini to‘sadi '
                  'va yozda xonani issiqdan ham himoya qiladi.\n\n'
                  'Kunduzi uxlaydigan yoki proyektor ishlatadigan xonalar uchun tanlanadi.',
             desc_ru='Ткань блэкаут с серебристым покрытием изнутри задерживает более 95% света '
                     'и защищает комнату от жары летом.\n\n'
                     'Выбирают для комнат, где спят днём или используют проектор.',
             price=168_000, stock=12, featured=True),
        dict(slug='plisse-arco', name='Plisse «Arco» arkasimon', name_ru='Плиссе «Arco» арочное',
             short='Uchburchak, trapetsiya va arkasimon derazalar uchun maxsus tayyorlanadi.',
             short_ru='Изготавливается специально для треугольных, трапециевидных и арочных окон.',
             desc='Nostandart deraza uchun har bir burchak alohida o‘lchanadi va shablon bo‘yicha tikiladi. '
                  'Mansard va tom oynalariga ham mos.\n\n'
                  'Buyurtma tayyorlash muddati odatdagidan 2–3 kun uzunroq, chunki mato individual bichiladi.',
             desc_ru='Для нестандартного окна каждый угол измеряется отдельно и шьётся по шаблону. '
                     'Подходит и для мансардных окон.\n\n'
                     'Срок изготовления на 2–3 дня дольше обычного, так как ткань кроится индивидуально.',
             price=214_000, stock=6),
        dict(slug='plisse-termo', name='Plisse «Termo» sotali', name_ru='Плиссе «Termo» сотовое',
             short='Ari uyasi tuzilishi issiqlikni ushlaydi — qishda isitish xarajatini kamaytiradi.',
             short_ru='Сотовая структура удерживает тепло — снижает расходы на отопление зимой.',
             desc='Ikki qavat mato orasidagi havo qatlami issiqlik to‘sig‘i vazifasini bajaradi. '
                  'Qishda issiqni ichkarida, yozda esa jaziramani tashqarida ushlaydi.\n\n'
                  'Shovqinni ham biroz kamaytiradi — yo‘lga qaragan derazalar uchun foydali.',
             desc_ru='Воздушная прослойка между двумя слоями ткани работает как тепловой барьер. '
                     'Зимой держит тепло внутри, летом — жару снаружи.\n\n'
                     'Также немного снижает шум — полезно для окон, выходящих на дорогу.',
             price=236_500, old=262_000, stock=9),
    ],
    'rulon-pardalar': [
        dict(slug='rulon-lino', name='Rulon «Lino» zig‘ir tuzilishli', name_ru='Рулонная «Lino» под лён',
             short='Tabiiy zig‘irni eslatuvchi to‘qima, iliq bej tuslarda.',
             short_ru='Фактура, напоминающая натуральный лён, в тёплых бежевых тонах.',
             desc='Mato tabiiy zig‘ir ko‘rinishiga ega, lekin polyester asosda — shuning uchun cho‘kmaydi '
                  'va rangini yo‘qotmaydi.\n\n'
                  'Yorug‘likni yumshoq tarqatadi, mehmonxona va yotoqxona uchun universal tanlov.',
             desc_ru='Ткань выглядит как натуральный лён, но на полиэфирной основе — поэтому не садится '
                     'и не выгорает.\n\nМягко рассеивает свет, универсальный выбор для гостиной и спальни.',
             price=129_024, stock=30, featured=True),
        dict(slug='rulon-blackout-nero', name='Rulon «Blackout Nero»', name_ru='Рулонная «Blackout Nero»',
             short='Yorug‘likni 100% to‘sadi, yon tomonlarga yo‘naltiruvchi profil bilan.',
             short_ru='Перекрывает свет на 100%, с боковыми направляющими профилями.',
             desc='To‘liq qorong‘ilik uchun mato yon profillar ichida harakatlanadi — yon tomonlardan '
                  'yorug‘lik o‘tmaydi.\n\n'
                  'Yotoqxona, kinozal va smenali ishlaydigan xodimlar xonasi uchun buyurtma qilinadi.',
             desc_ru='Для полного затемнения полотно движется внутри боковых профилей — свет не проходит по краям.\n\n'
                     'Заказывают для спальни, домашнего кинозала и комнат сменных работников.',
             price=172_000, stock=22),
        dict(slug='rulon-aqua', name='Rulon «Aqua» namlikka chidamli', name_ru='Рулонная «Aqua» влагостойкая',
             short='Oshxona va vanna uchun: yog‘ va namlikni yutmaydigan qoplama.',
             short_ru='Для кухни и ванной: покрытие не впитывает жир и влагу.',
             desc='Mato maxsus qoplama bilan ishlangan, shuning uchun bug‘ va yog‘ tomchilari yuzasida qoladi '
                  'va nam shimgich bilan oson artiladi.\n\n'
                  'Zamburug‘ va hidga qarshi ishlov berilgan — nam xonalar uchun mos.',
             desc_ru='Ткань обработана специальным покрытием, поэтому пар и капли жира остаются на поверхности '
                     'и легко стираются влажной губкой.\n\n'
                     'Есть обработка против плесени и запаха — подходит для влажных помещений.',
             price=158_000, old=174_000, stock=15),
        dict(slug='rulon-mini', name='Rulon «Mini» stvorkaga', name_ru='Рулонная «Mini» на створку',
             short='Eng ixcham model — deraza tokchasi to‘liq bo‘sh qoladi.',
             short_ru='Самая компактная модель — подоконник остаётся полностью свободным.',
             desc='Val to‘g‘ridan-to‘g‘ri stvorkaga o‘rnatiladi, mato esa oynaga taqalib turadi. '
                  'Deraza ochilganda parda u bilan birga harakatlanadi.\n\n'
                  'Kichik oshxona va balkon derazalari uchun eng arzon yechim.',
             desc_ru='Вал крепится прямо на створку, полотно прилегает к стеклу. При открывании окна штора '
                     'двигается вместе с ним.\n\nСамое доступное решение для небольшой кухни и балкона.',
             price=96_000, stock=40),
        dict(slug='rulon-zebra-light', name='Rulon «Zebra Light»', name_ru='Рулонная «Zebra Light»',
             short='Ochiq to‘qima zebra — yorug‘likni pardani ko‘tarmasdan sozlaysiz.',
             short_ru='Открытое плетение зебра — свет регулируется без подъёма шторы.',
             desc='Shaffof va zich yo‘llar navbatma-navbat joylashgan; ularni siljitib xonadagi yorug‘likni '
                  'bosqichma-bosqich o‘zgartirasiz.\n\n'
                  'Kunduzi ishlaydigan ish stoli yoniga eng qulay variant.',
             desc_ru='Прозрачные и плотные полосы чередуются; сдвигая их, вы плавно меняете освещённость.\n\n'
                     'Самый удобный вариант для рабочего стола при дневной работе.',
             price=189_000, stock=11, featured=True),
    ],
    'kun-tun-combo': [
        dict(slug='combo-duo-classic', name='Combo «Duo Classic»', name_ru='Комбо «Duo Classic»',
             short='Klassik oq-bej kombinatsiya, ochiq val mexanizmi bilan.',
             short_ru='Классическая бело-бежевая комбинация с открытым механизмом.',
             desc='Eng arzon kun-tun modeli: mato ochiq valga o‘raladi, zanjir o‘ngga yoki chapga o‘rnatiladi.\n\n'
                  'Uy va kichik ofis uchun kundalik yechim.',
             desc_ru='Самая доступная модель день-ночь: полотно наматывается на открытый вал, цепочка ставится '
                     'справа или слева.\n\nПовседневное решение для дома и небольшого офиса.',
             price=132_300, stock=26, featured=True),
        dict(slug='combo-duo-blackout', name='Combo «Duo Blackout»', name_ru='Комбо «Duo Blackout»',
             short='Zich yo‘llari yorug‘likni deyarli to‘liq to‘sadi.',
             short_ru='Плотные полосы почти полностью перекрывают свет.',
             desc='Odatdagi kun-tun matosidan farqli o‘laroq zich qatlam blackout tolasidan tikilgan — '
                  'yopilganda xona sezilarli qorayadi.\n\n'
                  'Yotoqxona uchun kun-tun qulayligini saqlagan holda qorong‘ilik beradi.',
             desc_ru='В отличие от обычной ткани день-ночь плотный слой сшит из блэкаут-нити — в закрытом '
                     'положении комната заметно темнеет.\n\nДаёт затемнение для спальни, сохраняя удобство день-ночь.',
             price=186_000, stock=14),
        dict(slug='combo-duo-grey', name='Combo «Duo Grey» kulrang', name_ru='Комбо «Duo Grey» серое',
             short='To‘q kulrang tuslar — zamonaviy loft va minimalizm uchun.',
             short_ru='Тёмно-серые тона — для современного лофта и минимализма.',
             desc='Grafit va tuman-kulrang yo‘llar oq devorlar fonida aniq chiziq hosil qiladi.\n\n'
                  'Metall karniz va qora ramkali derazalar bilan uyg‘un ko‘rinadi.',
             desc_ru='Графитовые и дымчато-серые полосы дают чёткую линию на фоне белых стен.\n\n'
                     'Хорошо сочетается с металлическим карнизом и окнами в чёрных рамах.',
             price=149_000, old=165_000, stock=19),
        dict(slug='combo-duo-cassette', name='Combo «Duo Cassette» kasetali', name_ru='Комбо «Duo Cassette» кассетное',
             short='Val yopiq kasetada — chang o‘tirmaydi, ko‘rinishi tugallangan.',
             short_ru='Вал в закрытой кассете — не собирает пыль, вид законченный.',
             desc='Alyuminiy kaseta mexanizmni to‘liq yopadi, yon yo‘naltiruvchilar esa matoni oynaga taqab turadi.\n\n'
                  'Deraza ochilganda ham parda osilib qolmaydi — plastik derazalar uchun eng toza yechim.',
             desc_ru='Алюминиевая кассета полностью закрывает механизм, а боковые направляющие прижимают полотно '
                     'к стеклу.\n\nПри открывании окна штора не провисает — самое аккуратное решение для пластиковых окон.',
             price=218_000, stock=8, featured=True),
        dict(slug='combo-duo-wide', name='Combo «Duo Wide» keng deraza', name_ru='Комбо «Duo Wide» для широких окон',
             short='3 metrgacha kenglik uchun kuchaytirilgan val va mexanizm.',
             short_ru='Усиленный вал и механизм для ширины до 3 метров.',
             desc='Panorama derazalar uchun qalinlashtirilgan val ishlatiladi — mato o‘z og‘irligidan egilmaydi.\n\n'
                  'Kerak bo‘lsa bitta karnizga ikki yoki uch bo‘lim qilib bo‘lib beriladi.',
             desc_ru='Для панорамных окон используется утолщённый вал — полотно не провисает под своим весом.\n\n'
                     'При необходимости на один карниз делим два-три отдельных полотна.',
             price=245_000, stock=7),
    ],
    'zamonaviy-pardalar': [
        dict(slug='parda-velvet-touch', name='Parda «Velvet Touch» baxmal', name_ru='Штора «Velvet Touch» велюр',
             short='Qalin baxmal mato: shovqinni yutadi va xonaga chuqur tus beradi.',
             short_ru='Плотный велюр: поглощает шум и придаёт комнате глубокий тон.',
             desc='Baxmalning zichligi 280 g/m² — mato go‘zal to‘kiladi va yorug‘likni sezilarli kamaytiradi.\n\n'
                  'Zumrad, marsala va grafit ranglari mavjud; lentali yoki halqali osma tanlanadi.',
             desc_ru='Плотность велюра 280 г/м² — ткань красиво драпируется и заметно снижает освещённость.\n\n'
                     'Есть изумрудный, марсала и графитовый; крепление на ленте или люверсах.',
             price=385_000, stock=12, featured=True),
        dict(slug='parda-milano-duo', name='Parda «Milano» ikki qatlamli', name_ru='Штора «Milano» двухслойная',
             short='Tul va zich portyera to‘plami — bitta karnizda tayyor komplekt.',
             short_ru='Комплект из тюля и плотной портьеры на одном карнизе.',
             desc='To‘plamga yengil tul va blackout portyera kiradi, ikkalasi bir uslubda tanlangan.\n\n'
                  'Kunduzi tul, kechqurun portyera — xonani alohida bezashning hojati yo‘q.',
             desc_ru='В комплект входят лёгкий тюль и портьера блэкаут, подобранные в одном стиле.\n\n'
                     'Днём тюль, вечером портьера — отдельно подбирать ничего не нужно.',
             price=640_000, old=715_000, stock=9),
        dict(slug='parda-linen-natural', name='Parda «Linen Natural» zig‘ir', name_ru='Штора «Linen Natural» лён',
             short='100% tabiiy zig‘ir — nafas oladi, yorug‘likni mayin tarqatadi.',
             short_ru='100% натуральный лён — дышит и мягко рассеивает свет.',
             desc='Tabiiy tola tufayli mato biroz notekis to‘qilgan — bu zig‘irning o‘ziga xos belgisi.\n\n'
                  'Skandinaviya va eko uslubdagi xonalarga eng mos variant.',
             desc_ru='Из-за натурального волокна плетение слегка неровное — это особенность льна.\n\n'
                     'Лучший вариант для комнат в скандинавском и эко-стиле.',
             price=470_000, stock=16),
        dict(slug='parda-grafit', name='Parda «Grafit» to‘q kulrang', name_ru='Штора «Grafit» тёмно-серая',
             short='Bir tekis to‘q rang — televizor va ish zonasi uchun aksni kamaytiradi.',
             short_ru='Ровный тёмный тон — снижает блики для телевизора и рабочей зоны.',
             desc='Matoning teskari tomoni oq, shuning uchun tashqaridan barcha derazalar bir xil ko‘rinadi.\n\n'
                  'Zichligi o‘rtacha-yuqori: to‘liq qorong‘ilik bermaydi, lekin quyoshni sezilarli to‘sadi.',
             desc_ru='Изнанка ткани белая, поэтому снаружи все окна выглядят одинаково.\n\n'
                     'Плотность средне-высокая: полного затемнения не даёт, но солнце заметно приглушает.',
             price=520_000, stock=10),
        dict(slug='parda-ombre', name='Parda «Ombre» gradient', name_ru='Штора «Ombre» градиент',
             short='Yuqoridan pastga rang o‘tishi bilan — dizayner yechim.',
             short_ru='С переходом цвета сверху вниз — дизайнерское решение.',
             desc='Rang tepadan pastga qarab asta yorishadi; o‘tish chizig‘i deraza balandligiga moslab hisoblanadi.\n\n'
                  'Har bir buyurtma alohida bo‘yaladi, shuning uchun tayyorlash 5–7 kun oladi.',
             desc_ru='Цвет плавно светлеет сверху вниз; линия перехода рассчитывается под высоту окна.\n\n'
                     'Каждый заказ окрашивается отдельно, поэтому изготовление занимает 5–7 дней.',
             price=690_000, stock=5, featured=True),
    ],
    'rim-pardalari': [
        dict(slug='rim-kanvas', name='Rim «Kanvas» paxta', name_ru='Римская «Kanvas» хлопок',
             short='Qalin paxta mato, ko‘tarilganda bir tekis burmalar hosil qiladi.',
             short_ru='Плотный хлопок, при подъёме собирается в ровные складки.',
             desc='Ichiga tikilgan ko‘ndalang chiziqlar tufayli burmalar har safar bir xil chiqadi.\n\n'
                  'Zanjirli mexanizm 10 kg gacha og‘irlikni ko‘taradi — keng derazalarga ham mos.',
             desc_ru='Благодаря вшитым поперечным рейкам складки каждый раз ложатся одинаково.\n\n'
                     'Цепочный механизм выдерживает до 10 кг — подходит и для широких окон.',
             price=781_200, stock=8, featured=True),
        dict(slug='rim-shantung', name='Rim «Shantung» ipak effekti', name_ru='Римская «Shantung» под шёлк',
             short='Ipakka o‘xshash yaltiroq yuza, mehmonxona uchun tantanavor ko‘rinish.',
             short_ru='Блестящая поверхность под шёлк, торжественный вид для гостиной.',
             desc='Shantung to‘qimasi yorug‘likda mayin yaltiraydi va burmalarni yanada aniq ko‘rsatadi.\n\n'
                  'Klassik va neoklassik interyerlarda karniz bilan birga buyurtma qilinadi.',
             desc_ru='Плетение шантунг мягко бликует на свету и делает складки выразительнее.\n\n'
                     'В классических и неоклассических интерьерах заказывают вместе с карнизом.',
             price=869_000, old=941_850, stock=6),
        dict(slug='rim-blackout-cream', name='Rim «Blackout Cream»', name_ru='Римская «Blackout Cream»',
             short='Krem rangli blackout astar bilan — yotoqxona uchun.',
             short_ru='Кремовая с подкладкой блэкаут — для спальни.',
             desc='Bezakli yuza mato ostiga qorong‘ilashtiruvchi astar tikiladi, shuning uchun tashqi ko‘rinish '
                  'yengil, ammo yorug‘lik to‘siladi.\n\n'
                  'Astarni keyinchalik alohida almashtirish mumkin.',
             desc_ru='Под декоративную ткань подшивается затемняющая подкладка: вид лёгкий, а свет перекрыт.\n\n'
                     'Подкладку впоследствии можно заменить отдельно.',
             price=905_000, stock=7),
        dict(slug='rim-bamboo-line', name='Rim «Bamboo Line» tabiiy', name_ru='Римская «Bamboo Line» натуральная',
             short='Bambuk chiviqlaridan to‘qilgan rim pardasi, eko uslub uchun.',
             short_ru='Римская штора из бамбуковой соломки для эко-стиля.',
             desc='Yupqa bambuk chiviqlari ip bilan to‘qilgan — yorug‘lik oralardan mayin o‘tadi.\n\n'
                  'Ayvon, veranda va yozgi oshxona uchun ko‘p tanlanadi.',
             desc_ru='Тонкая бамбуковая соломка переплетена нитью — свет мягко проходит между планками.\n\n'
                     'Часто выбирают для веранды, террасы и летней кухни.',
             price=812_000, stock=5),
        dict(slug='rim-mini-kitchen', name='Rim «Mini Kitchen»', name_ru='Римская «Mini Kitchen»',
             short='Kichik oshxona derazasi uchun ixcham o‘lcham, yuviladigan mato.',
             short_ru='Компактный размер для кухонного окна, ткань можно стирать.',
             desc='Eni 120 sm gacha bo‘lgan derazalar uchun yengil mexanizm ishlatiladi.\n\n'
                  'Mato yechib olinadi va 30° da mashinada yuviladi — oshxona uchun muhim.',
             desc_ru='Для окон шириной до 120 см используется облегчённый механизм.\n\n'
                     'Полотно снимается и стирается в машине при 30° — важно для кухни.',
             price=615_000, stock=12),
    ],
    'klassik-pardalar': [
        dict(slug='klassik-jakkard-royal', name='Klassik «Jakkard Royal»', name_ru='Классика «Jakkard Royal»',
             short='Jakkard naqshli portyera, oltin va bej tuslarda.',
             short_ru='Портьера с жаккардовым узором в золотых и бежевых тонах.',
             desc='Naqsh matoning o‘ziga to‘qilgan, bosilmagan — shuning uchun yuvishdan keyin ham yo‘qolmaydi.\n\n'
                  'Mehmonxona va katta yotoqxona uchun tantanavor yechim.',
             desc_ru='Узор вплетён в саму ткань, а не напечатан — поэтому не исчезает после стирки.\n\n'
                     'Торжественное решение для гостиной и большой спальни.',
             price=465_000, stock=10, featured=True),
        dict(slug='klassik-barokko-gold', name='Klassik «Barokko Gold» lambrekenli', name_ru='Классика «Barokko Gold» с ламбрекеном',
             short='Lambreken, svag va bandolar bilan to‘liq bezak to‘plami.',
             short_ru='Полный декоративный комплект с ламбрекеном, свагами и бандо.',
             desc='To‘plam dizayner eskizi asosida tikiladi: lambreken, ikki portyera va tul.\n\n'
                  'Baland shiftli xonalar uchun mo‘ljallangan, o‘lchov mutaxassis tomonidan olinadi.',
             desc_ru='Комплект шьётся по эскизу дизайнера: ламбрекен, две портьеры и тюль.\n\n'
                     'Рассчитан на комнаты с высокими потолками, замер выполняет специалист.',
             price=890_000, old=980_000, stock=4),
        dict(slug='klassik-tul-organza', name='Klassik «Tul Organza»', name_ru='Классика «Тюль органза»',
             short='Yengil shaffof organza — portyera ostiga bazaviy qatlam.',
             short_ru='Лёгкая прозрачная органза — базовый слой под портьеру.',
             desc='Organza deyarli vaznsiz, yorug‘likni to‘sib qo‘ymaydi va xonani kengroq ko‘rsatadi.\n\n'
                  'Alohida yoki portyera bilan birga osiladi.',
             desc_ru='Органза почти невесома, не перекрывает свет и визуально расширяет комнату.\n\n'
                     'Вешается отдельно или вместе с портьерой.',
             price=265_000, stock=20),
        dict(slug='klassik-portyera-bordo', name='Klassik «Portyera Bordo»', name_ru='Классика «Портьера Бордо»',
             short='To‘q bordo rang, zich mato — kechqurun to‘liq yopiladi.',
             short_ru='Глубокий бордовый цвет, плотная ткань — вечером закрывает полностью.',
             desc='Zichligi yuqori mato yorug‘likni deyarli to‘liq to‘sadi va issiqlikni ushlab qoladi.\n\n'
                  'Yog‘och mebel va issiq yorug‘lik bilan uyg‘un.',
             desc_ru='Ткань высокой плотности почти полностью перекрывает свет и удерживает тепло.\n\n'
                     'Сочетается с деревянной мебелью и тёплым освещением.',
             price=610_000, stock=8),
        dict(slug='klassik-duet-set', name='Klassik «Duet» to‘plam', name_ru='Классика «Duet» комплект',
             short='Tul + ikki portyera + karniz — bitta buyurtmada tayyor yechim.',
             short_ru='Тюль + две портьеры + карниз — готовое решение одним заказом.',
             desc='To‘plamda ranglari mos tanlangan tul va portyeralar hamda ikki qatorli karniz bor.\n\n'
                  'Yangi ko‘chib kelganlar uchun eng tez variant — bir kunda o‘rnatiladi.',
             desc_ru='В комплекте подобранные по цвету тюль и портьеры, а также двухрядный карниз.\n\n'
                     'Самый быстрый вариант при переезде — монтаж за один день.',
             price=745_000, stock=6),
    ],
    'tekstil-jalyuzi': [
        dict(slug='vertikal-line-89', name='Vertikal «Line 89» oq', name_ru='Вертикальные «Line 89» белые',
             short='89 mm lamel, klassik oq — ofis va uy uchun bazaviy model.',
             short_ru='Ламель 89 мм, классический белый — базовая модель для офиса и дома.',
             desc='Lamellar burilib yorug‘likni bosqichma-bosqich sozlaydi, kerak bo‘lsa bir chetga yig‘iladi.\n\n'
                  'Shift yoki devorga o‘rnatiladi — baland derazalar uchun qulay.',
             desc_ru='Ламели поворачиваются и плавно регулируют свет, при необходимости сдвигаются в сторону.\n\n'
                     'Монтаж к потолку или стене — удобно для высоких окон.',
             price=154_000, stock=25, featured=True),
        dict(slug='vertikal-office-grey', name='Vertikal «Office Grey»', name_ru='Вертикальные «Office Grey»',
             short='Kulrang antistatik mato — monitor aksini kamaytiradi.',
             short_ru='Серая антистатическая ткань — снижает блики на мониторе.',
             desc='Antistatik ishlov changni kamaytiradi, bu ko‘p kompyuterli xonalarda seziladi.\n\n'
                  'Yong‘inga chidamlilik sertifikati bor — ofis binolari talabiga javob beradi.',
             desc_ru='Антистатическая обработка снижает пыль, что заметно в помещениях с множеством компьютеров.\n\n'
                     'Есть сертификат огнестойкости — соответствует требованиям офисных зданий.',
             price=168_000, stock=18),
        dict(slug='vertikal-blackout', name='Vertikal «Blackout Vert»', name_ru='Вертикальные «Blackout Vert»',
             short='Qorong‘ilashtiruvchi lamellar — konferens-zal va yotoqxona uchun.',
             short_ru='Затемняющие ламели — для конференц-зала и спальни.',
             desc='Lamellar bir-birining ustiga kelib yopiladi, shuning uchun oralaridan yorug‘lik o‘tmaydi.\n\n'
                  'Proyektor bilan ishlaydigan xonalar uchun tanlanadi.',
             desc_ru='Ламели заходят одна на другую, поэтому свет между ними не проходит.\n\n'
                     'Выбирают для помещений с проектором.',
             price=198_000, old=219_000, stock=10),
        dict(slug='vertikal-skyline', name='Vertikal «Skyline» arkali', name_ru='Вертикальные «Skyline» арочные',
             short='Qiya va arkasimon derazalar uchun maxsus karniz bilan.',
             short_ru='Со специальным карнизом для наклонных и арочных окон.',
             desc='Har bir lamel alohida uzunlikda bichiladi va egri karnizga o‘rnatiladi.\n\n'
                  'Panoramali zinapoya va vitrajlarda ishlatiladi.',
             desc_ru='Каждая ламель кроится по своей длине и крепится на криволинейный карниз.\n\n'
                     'Применяются на панорамных лестницах и витражах.',
             price=232_000, stock=6),
        dict(slug='vertikal-soft-beige', name='Vertikal «Soft Beige»', name_ru='Вертикальные «Soft Beige»',
             short='Iliq bej tus, yumshoq to‘qima — uy sharoiti uchun.',
             short_ru='Тёплый бежевый тон, мягкое плетение — для дома.',
             desc='Mato ofisga xos qattiq ko‘rinishga ega emas, shuning uchun mehmonxonaga ham mos.\n\n'
                  'Pastki og‘irliklar va zanjir bir xil rangda beriladi.',
             desc_ru='Ткань не выглядит по-офисному строго, поэтому подходит и для гостиной.\n\n'
                     'Нижние грузики и цепочка идут в тон ткани.',
             price=161_000, stock=22),
    ],
    'yogoch-jalyuzi': [
        dict(slug='yogoch-basswood-50', name='Yog‘och «Basswood 50»', name_ru='Дерево «Basswood 50»',
             short='50 mm tabiiy lipa lamel — eng ommabop premium model.',
             short_ru='Ламель 50 мм из натуральной липы — самая популярная премиум-модель.',
             desc='Lipa yengil va deformatsiyaga chidamli; lamellar qo‘lda silliqlanib lak bilan qoplanadi.\n\n'
                  'Har bir jalyuzi individual bichiladi, shuning uchun deraza o‘lchamiga aniq mos tushadi.',
             desc_ru='Липа лёгкая и устойчива к деформации; ламели шлифуются вручную и покрываются лаком.\n\n'
                     'Каждое изделие кроится индивидуально и точно садится по размеру окна.',
             price=2_193_408, stock=4, featured=True),
        dict(slug='yogoch-walnut-25', name='Yog‘och «Walnut 25» yong‘oq', name_ru='Дерево «Walnut 25» орех',
             short='25 mm tor lamel, to‘q yong‘oq tusi — kabinet uchun.',
             short_ru='Узкая ламель 25 мм, тёмный орех — для кабинета.',
             desc='Tor lamel yig‘ilganda kam joy egallaydi va kichik derazalarda nafis ko‘rinadi.\n\n'
                  'To‘q rang yog‘och mebel va charm bilan yaxshi uyg‘unlashadi.',
             desc_ru='Узкая ламель в собранном виде занимает мало места и изящно смотрится на небольших окнах.\n\n'
                     'Тёмный тон хорошо сочетается с деревянной мебелью и кожей.',
             price=1_780_000, stock=5),
        dict(slug='yogoch-white-oak', name='Yog‘och «White Oak» oq eman', name_ru='Дерево «White Oak» белый дуб',
             short='Oqartirilgan eman tuzilishi — yorug‘ Skandinaviya interyeri uchun.',
             short_ru='Фактура выбеленного дуба — для светлого скандинавского интерьера.',
             desc='Yog‘och tomirlari ko‘rinib turadi, ustidan matlashgan oq lak surtilgan.\n\n'
                  'Oq devor va och rangli parket bilan bitta ohangda ishlaydi.',
             desc_ru='Текстура дерева просматривается, сверху нанесён матовый белый лак.\n\n'
                     'Работает в одном тоне с белыми стенами и светлым паркетом.',
             price=1_950_000, old=2_150_000, stock=3),
        dict(slug='yogoch-bamboo-wood', name='Yog‘och «Bamboo Wood»', name_ru='Дерево «Bamboo Wood»',
             short='Bambuk lamel — yog‘ochdan yengilroq va namlikka chidamliroq.',
             short_ru='Бамбуковая ламель — легче дерева и устойчивее к влаге.',
             desc='Bambuk zichligi yuqori, shuning uchun lamel ingichka bo‘lsa ham egilmaydi.\n\n'
                  'Namlik o‘zgarishiga lipa va emandan ko‘ra chidamliroq.',
             desc_ru='Плотность бамбука высокая, поэтому даже тонкая ламель не гнётся.\n\n'
                     'Переносит перепады влажности лучше липы и дуба.',
             price=1_420_000, stock=6),
        dict(slug='yogoch-cornice', name='Yog‘och «Cornice» karnizli', name_ru='Дерево «Cornice» с карнизом',
             short='Dekorativ yog‘och karniz mexanizmni to‘liq yashiradi.',
             short_ru='Декоративный деревянный карниз полностью скрывает механизм.',
             desc='Yuqori qismga lamel bilan bir xil rangdagi yog‘och karniz o‘rnatiladi.\n\n'
                  'Interyer loyihalarida tugallangan ko‘rinish uchun buyurtma qilinadi.',
             desc_ru='Сверху устанавливается деревянный карниз в цвет ламелей.\n\n'
                     'Заказывают в интерьерных проектах для законченного вида.',
             price=2_480_000, stock=2),
    ],
    'alyuminiy-jalyuzi': [
        dict(slug='alyuminiy-standart-25', name='Alyuminiy «Standart 25»', name_ru='Алюминий «Standart 25»',
             short='Eng arzon gorizontal jalyuzi — 25 mm oq lamel.',
             short_ru='Самые доступные горизонтальные жалюзи — белая ламель 25 мм.',
             desc='Yengil alyuminiy lamel, plastik burovchi tayoqcha va zanjir bilan.\n\n'
                  'Ijaraga beriladigan xonalar va vaqtinchalik yechimlar uchun ko‘p olinadi.',
             desc_ru='Лёгкая алюминиевая ламель с пластиковым поворотным стержнем и цепочкой.\n\n'
                     'Часто берут для сдаваемых квартир и временных решений.',
             price=98_000, stock=45, featured=True),
        dict(slug='alyuminiy-metallic-silver', name='Alyuminiy «Metallic Silver»', name_ru='Алюминий «Metallic Silver»',
             short='Kumush metallik yuza — quyosh nurini qaytaradi.',
             short_ru='Серебристая металлик-поверхность — отражает солнечные лучи.',
             desc='Yaltiroq qoplama issiqlikning bir qismini qaytaradi, shuning uchun janubga qaragan '
                  'derazalarda foydali.\n\nOfis va ishlab chiqarish binolarida ko‘p ishlatiladi.',
             desc_ru='Блестящее покрытие отражает часть тепла, что полезно на южных окнах.\n\n'
                     'Часто применяется в офисах и производственных помещениях.',
             price=116_000, stock=30),
        dict(slug='alyuminiy-perfo', name='Alyuminiy «Perfo» teshikli', name_ru='Алюминий «Perfo» перфорированные',
             short='Mayda teshikli lamel — yorug‘lik kiradi, lekin ko‘z qamashmaydi.',
             short_ru='Ламель с микроперфорацией — свет проходит, но не слепит.',
             desc='Teshiklar tashqaridagi manzarani qisman saqlab qoladi va xonani zulmatga aylantirmaydi.\n\n'
                  'Kompyuterli ish joylari uchun qulay yechim.',
             desc_ru='Перфорация частично сохраняет вид из окна и не превращает комнату в тёмную.\n\n'
                     'Удобное решение для компьютерных рабочих мест.',
             price=134_000, old=148_000, stock=16),
        dict(slug='alyuminiy-color-16', name='Alyuminiy «Color 16» rangli', name_ru='Алюминий «Color 16» цветные',
             short='16 mm tor lamel, 12 xil rangda — bolalar xonasi uchun ham.',
             short_ru='Узкая ламель 16 мм в 12 цветах — подойдёт и для детской.',
             desc='Tor lamel kichik derazalarda ixcham ko‘rinadi; ranglar RAL katalogidan tanlanadi.\n\n'
                  'Rangli va oq lamellarni aralashtirib chiziqli naqsh qilish mumkin.',
             desc_ru='Узкая ламель компактна на небольших окнах; цвета подбираются по каталогу RAL.\n\n'
                     'Можно чередовать цветные и белые ламели, получая полосатый рисунок.',
             price=108_000, stock=28),
        dict(slug='alyuminiy-kitchen-pro', name='Alyuminiy «Kitchen Pro»', name_ru='Алюминий «Kitchen Pro»',
             short='Oshxona uchun: yog‘ va bug‘dan qo‘rqmaydigan qoplama.',
             short_ru='Для кухни: покрытие не боится жира и пара.',
             desc='Lamel yuzasi silliq va gidrofob, shuning uchun yog‘ dog‘lari yuvish vositasi bilan oson ketadi.\n\n'
                  'Zanglamaydigan mexanizm nam muhitda uzoq xizmat qiladi.',
             desc_ru='Поверхность ламели гладкая и гидрофобная, поэтому жирные пятна легко смываются.\n\n'
                     'Нержавеющий механизм долго служит во влажной среде.',
             price=125_000, stock=20),
    ],
    'bambuk-jalyuzi': [
        dict(slug='bambuk-natural-roll', name='Bambuk «Natural Roll»', name_ru='Бамбук «Natural Roll»',
             short='Tabiiy rangdagi bambuk rulon — yorug‘likni iliq tusda tarqatadi.',
             short_ru='Бамбуковый рулон натурального цвета — рассеивает свет в тёплом тоне.',
             desc='Chiviqlar tabiiy holida qoldirilgan, faqat himoya lak bilan qoplangan.\n\n'
                  'Yorug‘lik oralardan o‘tganda xonaga iliq oltin tus beradi.',
             desc_ru='Соломка оставлена в натуральном виде и покрыта только защитным лаком.\n\n'
                     'Проходя между планками, свет придаёт комнате тёплый золотистый оттенок.',
             price=340_000, stock=12, featured=True),
        dict(slug='bambuk-tropic', name='Bambuk «Tropic» to‘q', name_ru='Бамбук «Tropic» тёмный',
             short='Kuydirilgan to‘q bambuk — kontrastli interyer uchun.',
             short_ru='Обожжённый тёмный бамбук — для контрастного интерьера.',
             desc='Chiviqlar issiqlik bilan ishlanib to‘q jigarrang tus olgan, bu ularni mustahkamroq ham qiladi.\n\n'
                  'Oq devorlar fonida aniq grafik ko‘rinish beradi.',
             desc_ru='Соломка обработана термически и приобрела тёмно-коричневый тон, что делает её прочнее.\n\n'
                     'На фоне белых стен даёт чёткий графичный вид.',
             price=395_000, stock=9),
        dict(slug='bambuk-rim', name='Bambuk «Rim Bamboo»', name_ru='Бамбук «Rim Bamboo»',
             short='Rim pardasi ko‘rinishida yig‘iladigan bambuk.',
             short_ru='Бамбук, собирающийся по типу римской шторы.',
             desc='Ko‘tarilganda tekis burmalar hosil qiladi — oddiy rulon variantidan ko‘ra bezakliroq.\n\n'
                  'Astar qo‘shilsa, yorug‘likni ancha kuchli to‘sadi.',
             desc_ru='При подъёме образует ровные складки — декоративнее обычного рулонного варианта.\n\n'
                     'С подкладкой заметно сильнее перекрывает свет.',
             price=460_000, old=505_000, stock=6),
        dict(slug='bambuk-light-screen', name='Bambuk «Light Screen»', name_ru='Бамбук «Light Screen»',
             short='Yupqa va yengil to‘qima — kichik derazalar uchun.',
             short_ru='Тонкое лёгкое плетение — для небольших окон.',
             desc='Ingichka chiviqlar tufayli mahsulot yengil, mexanizmga yuk tushmaydi.\n\n'
                  'Yorug‘likni kam to‘sadi — shimolga qaragan xonalar uchun mos.',
             desc_ru='Из-за тонкой соломки изделие лёгкое, нагрузки на механизм нет.\n\n'
                     'Слабо перекрывает свет — подходит для комнат, выходящих на север.',
             price=312_000, stock=14),
        dict(slug='bambuk-veranda', name='Bambuk «Veranda» keng', name_ru='Бамбук «Veranda» широкий',
             short='Ayvon va terrasalar uchun 3 metrgacha kenglikda.',
             short_ru='Для веранд и террас, шириной до 3 метров.',
             desc='Kuchaytirilgan val va qalinroq chiviqlar shamolga chidamlilikni oshiradi.\n\n'
                  'Yozgi oshxona va ochiq ayvonlarda quyoshdan himoya sifatida ishlatiladi.',
             desc_ru='Усиленный вал и более толстая соломка повышают устойчивость к ветру.\n\n'
                     'Используется как защита от солнца на летней кухне и открытой веранде.',
             price=540_000, stock=5),
    ],
    'plastik-deraza-jalyuzi': [
        dict(slug='plastik-kassetli-uni', name='«Kassetli Uni» stvorkaga', name_ru='«Kassetli Uni» на створку',
             short='Universal kaseta — plastik derazaning har qanday stvorkasiga.',
             short_ru='Универсальная кассета — на любую створку пластикового окна.',
             desc='Kaseta shtapikka o‘rnatiladi, yon yo‘naltiruvchilar matoni oynaga taqab turadi.\n\n'
                  'Deraza to‘liq ochiladi va parda osilib qolmaydi.',
             desc_ru='Кассета ставится на штапик, боковые направляющие прижимают полотно к стеклу.\n\n'
                     'Окно открывается полностью, штора не провисает.',
             price=112_000, stock=35, featured=True),
        dict(slug='plastik-kassetli-blackout', name='«Kassetli Blackout»', name_ru='«Kassetli Blackout»',
             short='Kasetali konstruksiya + qorong‘ilashtiruvchi mato.',
             short_ru='Кассетная конструкция + затемняющая ткань.',
             desc='Yon yo‘naltiruvchilar tufayli chetlardan yorug‘lik sizib chiqmaydi — bu oddiy rulon '
                  'pardadan asosiy farqi.\n\nYotoqxona derazalari uchun eng samarali kasetali variant.',
             desc_ru='Благодаря боковым направляющим свет не пробивается по краям — главное отличие от обычной '
                     'рулонной шторы.\n\nСамый эффективный кассетный вариант для окон спальни.',
             price=152_000, stock=20),
        dict(slug='plastik-teshiksiz-klips', name='«Teshiksiz Klips»', name_ru='«Без сверления, на клипсах»',
             short='Burg‘ulashsiz o‘rnatish — ijaradagi kvartira uchun ideal.',
             short_ru='Монтаж без сверления — идеально для съёмной квартиры.',
             desc='Metall qisqichlar stvorka ramasiga kiydiriladi, hech qanday teshik qolmaydi.\n\n'
                  'Ko‘chib ketganda jalyuzi olib ketiladi va deraza jarohatsiz qoladi.',
             desc_ru='Металлические клипсы надеваются на раму створки, отверстий не остаётся.\n\n'
                     'При переезде жалюзи снимаются, окно остаётся без повреждений.',
             price=129_000, old=142_000, stock=25),
        dict(slug='plastik-balkon-set', name='«Balkon Set» to‘plam', name_ru='«Балконный комплект»',
             short='Balkon bloki uchun: eshik va deraza pardalari bir uslubda.',
             short_ru='Для балконного блока: шторы на дверь и окно в одном стиле.',
             desc='To‘plamda balkon eshigi uchun uzun va deraza uchun kalta parda bor, ikkalasi bir matodan.\n\n'
                  'Eshik pardasi pastki mahkamlagich bilan — eshik ochilganda tebranmaydi.',
             desc_ru='В комплекте длинная штора на балконную дверь и короткая на окно из одной ткани.\n\n'
                     'Дверная штора с нижним фиксатором — не болтается при открывании.',
             price=268_000, stock=10),
        dict(slug='plastik-termo-kasseta', name='«Termo Kasseta»', name_ru='«Термо-кассета»',
             short='Issiqlik qaytaruvchi qatlam bilan — yozda salqin, qishda iliq.',
             short_ru='Со светоотражающим слоем — летом прохладно, зимой тепло.',
             desc='Matoning tashqi tomoni kumushrang — quyosh energiyasining sezilarli qismini qaytaradi.\n\n'
                  'Konditsioner yukini kamaytiradi, janubiy va g‘arbiy derazalar uchun tavsiya etiladi.',
             desc_ru='Внешняя сторона полотна серебристая — отражает заметную часть солнечной энергии.\n\n'
                     'Снижает нагрузку на кондиционер, рекомендуется для южных и западных окон.',
             price=176_000, stock=12),
    ],
    'logotipli-jalyuzi': [
        dict(slug='logo-print-roll', name='«Logo Print Roll» rulon', name_ru='«Logo Print Roll» рулонная',
             short='Rulon pardaga logotip bosish — reception va ofis uchun.',
             short_ru='Печать логотипа на рулонной шторе — для ресепшена и офиса.',
             desc='Logotip UV-siyoh bilan bosiladi: quyoshda so‘lmaydi va nam mato bilan artilganda ketmaydi.\n\n'
                  'Maket PDF yoki vektor formatda qabul qilinadi, tasdiqlash bepul.',
             desc_ru='Логотип печатается УФ-чернилами: не выгорает на солнце и не стирается влажной салфеткой.\n\n'
                     'Макет принимается в PDF или в векторе, согласование бесплатное.',
             price=275_000, stock=15, featured=True),
        dict(slug='logo-vertical', name='«Logo Vertical» vertikal', name_ru='«Logo Vertical» вертикальные',
             short='Logotip bir necha lamel bo‘ylab bo‘lib bosiladi.',
             short_ru='Логотип печатается с разбивкой по нескольким ламелям.',
             desc='Rasm lamellarga mos ravishda bo‘linadi va yopilganda yaxlit tasvir hosil qiladi.\n\n'
                  'Keng ofis derazalarida brend elementi sifatida yaxshi ishlaydi.',
             desc_ru='Изображение разбивается по ламелям и в закрытом положении складывается в целую картинку.\n\n'
                     'Хорошо работает как элемент бренда на широких офисных окнах.',
             price=298_000, stock=10),
        dict(slug='logo-blackout', name='«Logo Blackout» to‘q fon', name_ru='«Logo Blackout» тёмный фон',
             short='To‘q fonda yorqin logotip — kechqurun ham aniq ko‘rinadi.',
             short_ru='Яркий логотип на тёмном фоне — заметен и вечером.',
             desc='Blackout mato fon sifatida ishlaydi, logotip esa ochiq rangda bosiladi.\n\n'
                  'Ichkaridan yoritilganda tashqaridan reklama panelidek ko‘rinadi.',
             desc_ru='Ткань блэкаут работает как фон, логотип печатается светлым.\n\n'
                     'При подсветке изнутри снаружи выглядит как рекламная панель.',
             price=330_000, old=365_000, stock=8),
        dict(slug='logo-reception', name='«Logo Reception» keng', name_ru='«Logo Reception» широкая',
             short='Reception zonasining keng derazasi uchun yaxlit bosma.',
             short_ru='Цельная печать для широкого окна зоны ресепшена.',
             desc='Kengligi 3 metrgacha bitta polotnoda bosiladi — chok va uzilish bo‘lmaydi.\n\n'
                  'Kompaniya rangi Pantone bo‘yicha aniq moslashtiriladi.',
             desc_ru='Печать до 3 метров ширины на едином полотне — без швов и стыков.\n\n'
                     'Фирменный цвет точно подгоняется по Pantone.',
             price=412_000, stock=5),
        dict(slug='logo-eco', name='«Logo Eco» ekologik mato', name_ru='«Logo Eco» эко-ткань',
             short='Qayta ishlangan toladan tayyorlangan mato — eko-sertifikatli brendlar uchun.',
             short_ru='Ткань из переработанного волокна — для брендов с эко-сертификатом.',
             desc='Mato qayta ishlangan PET tolasidan tayyorlangan va tegishli sertifikatga ega.\n\n'
                  'Bosma uchun suv asosidagi siyoh ishlatiladi — hidsiz.',
             desc_ru='Ткань произведена из переработанного PET-волокна и имеет соответствующий сертификат.\n\n'
                     'Для печати используются чернила на водной основе — без запаха.',
             price=289_000, stock=12),
    ],
    'fotosuratli-jalyuzi': [
        dict(slug='foto-city', name='«Foto City» shahar manzarasi', name_ru='«Foto City» городской вид',
             short='Tunki shahar panoramasi — yotoqxona va zal uchun.',
             short_ru='Панорама ночного города — для спальни и зала.',
             desc='Tayyor katalogdan tanlanadigan yuqori aniqlikdagi manzara, 1440 dpi bosma.\n\n'
                  'Rasm deraza o‘lchamiga moslab qirqiladi, muhim qismlari kesilib qolmaydi.',
             desc_ru='Готовый сюжет из каталога в высоком разрешении, печать 1440 dpi.\n\n'
                     'Изображение подгоняется под размер окна, важные части не обрезаются.',
             price=298_000, stock=14, featured=True),
        dict(slug='foto-nature', name='«Foto Nature» tabiat', name_ru='«Foto Nature» природа',
             short='O‘rmon, dengiz va tog‘ manzaralari — 40 dan ortiq syujet.',
             short_ru='Лес, море и горы — более 40 сюжетов.',
             desc='Yashil va ko‘k tuslar xonani vizual ravishda tinchlantiradi.\n\n'
                  'Derazasiz devorga ham panel sifatida o‘rnatish mumkin.',
             desc_ru='Зелёные и синие тона визуально успокаивают интерьер.\n\n'
                     'Можно установить как панель даже на стену без окна.',
             price=312_000, stock=12),
        dict(slug='foto-kids', name='«Foto Kids» bolalar xonasi', name_ru='«Foto Kids» детская',
             short='Multfilm qahramonlari va samolyotlar — bolalar uchun syujetlar.',
             short_ru='Герои мультфильмов и самолёты — сюжеты для детей.',
             desc='Bosmada bolalar uchun xavfsiz, hidsiz siyoh ishlatiladi.\n\n'
                  'Mato yuvish mumkin bo‘lgan qoplamali — bo‘yoq dog‘lari oson ketadi.',
             desc_ru='В печати используются безопасные для детей чернила без запаха.\n\n'
                     'Ткань с моющимся покрытием — следы красок легко удаляются.',
             price=285_000, old=315_000, stock=16),
        dict(slug='foto-custom', name='«Foto Custom» o‘z rasmingiz', name_ru='«Foto Custom» ваше изображение',
             short='O‘zingiz yuborgan foto yoki dizayn bosiladi.',
             short_ru='Печатаем присланное вами фото или дизайн.',
             desc='Fayl kamida 150 dpi bo‘lishi kerak; sifatni bepul tekshirib beramiz.\n\n'
                  'Bosishdan oldin elektron maket tasdiqlash uchun yuboriladi.',
             desc_ru='Файл должен быть не менее 150 dpi; качество проверяем бесплатно.\n\n'
                     'Перед печатью отправляем электронный макет на согласование.',
             price=345_000, stock=20),
        dict(slug='foto-panorama', name='«Foto Panorama» keng deraza', name_ru='«Foto Panorama» для широкого окна',
             short='Panorama derazaga bir butun tasvir — chokssiz bosma.',
             short_ru='Цельное изображение на панорамное окно — печать без швов.',
             desc='Bir necha bo‘limli derazada tasvir bo‘limlar bo‘ylab davom etadigan qilib hisoblanadi.\n\n'
                  'Har bir bo‘lim alohida boshqariladi, lekin birgalikda yaxlit manzara hosil qiladi.',
             desc_ru='На окне из нескольких секций изображение рассчитывается так, чтобы продолжаться по секциям.\n\n'
                     'Каждая секция управляется отдельно, но вместе они образуют цельный вид.',
             price=480_000, stock=6),
    ],
    'moskit-torlari': [
        dict(slug='moskit-ramkali-standart', name='Moskit «Ramkali Standart»', name_ru='Москитная «Рамочная стандарт»',
             short='Alyuminiy ramkali klassik to‘r — plastik derazaning tashqi tomoniga.',
             short_ru='Классическая сетка в алюминиевой раме — снаружи пластикового окна.',
             desc='Ramka deraza o‘lchamiga aniq yig‘iladi va Z-shaklidagi mahkamlagichlar bilan o‘rnatiladi.\n\n'
                  'Qish oldidan yechib qo‘yish mumkin — to‘r uzoqroq xizmat qiladi.',
             desc_ru='Рама собирается точно по размеру окна и ставится на Z-образные крепления.\n\n'
                     'Перед зимой можно снять — сетка прослужит дольше.',
             price=260_000, stock=30, featured=True),
        dict(slug='moskit-plisse-door', name='Moskit «Plisse Door» eshik uchun', name_ru='Москитная «Plisse Door» на дверь',
             short='Burmali to‘r — balkon va ayvon eshigi uchun, yon tomonga yig‘iladi.',
             short_ru='Плиссированная сетка для балконной и террасной двери, сдвигается вбок.',
             desc='To‘r plisse kabi yig‘iladi va pastki yo‘naltiruvchi bo‘ylab siljiydi — ostona balandligi minimal.\n\n'
                  'Ochiq eshikdan bemalol o‘tiladi, to‘r esa o‘z-o‘zidan yopiladi.',
             desc_ru='Сетка складывается гармошкой и движется по нижней направляющей — порог минимальный.\n\n'
                     'Через открытую дверь легко проходить, сетка закрывается сама.',
             price=430_000, stock=8),
        dict(slug='moskit-anti-cat', name='Moskit «Anti-Cat» mushukbardosh', name_ru='Москитная «Anti-Cat» антикошка',
             short='Kuchaytirilgan to‘qima — uy hayvoni tirnog‘iga chidaydi.',
             short_ru='Усиленное полотно — выдерживает когти домашних животных.',
             desc='To‘r polyester tolasidan qalin to‘qilgan va oddiy to‘rdan bir necha barobar mustahkam.\n\n'
                  'Ramkasi ham kuchaytirilgan — hayvon suyanganda chiqib ketmaydi.',
             desc_ru='Полотно плотно соткано из полиэфирного волокна и в несколько раз прочнее обычного.\n\n'
                     'Рама тоже усилена — не выпадает, если животное на неё опирается.',
             price=340_000, old=375_000, stock=12),
        dict(slug='moskit-roll', name='Moskit «Roll» rulonli', name_ru='Москитная «Roll» рулонная',
             short='Kerak bo‘lganda tushiriladi, keraksizda valga o‘raladi.',
             short_ru='Опускается при необходимости, в остальное время скручена на вал.',
             desc='To‘r yuqoridagi kasetada saqlanadi, shuning uchun quyosh va changdan himoyalangan.\n\n'
                  'Qish uchun yechib olish shart emas — bu uzoq muddat xizmat qilishini ta’minlaydi.',
             desc_ru='Сетка хранится в верхней кассете, поэтому защищена от солнца и пыли.\n\n'
                     'На зиму снимать не нужно — это продлевает срок службы.',
             price=385_000, stock=10),
        dict(slug='moskit-magnit', name='Moskit «Magnit» magnitli parda', name_ru='Москитная «Магнит» на магнитах',
             short='Eshik uchun eng arzon variant — magnitlar o‘zi yopadi.',
             short_ru='Самый доступный вариант для двери — магниты закрывают сами.',
             desc='Ikki polotno o‘rtasidagi magnitlar o‘tib bo‘lgach avtomatik yopiladi.\n\n'
                  'O‘rnatish uchun asbob kerak emas — yopishqoq lenta bilan mahkamlanadi.',
             desc_ru='Магниты между двумя полотнами закрываются автоматически после прохода.\n\n'
                     'Для монтажа не нужен инструмент — крепится на липкую ленту.',
             price=165_000, stock=25),
    ],
}

ADVANTAGES = [
    ('🧵', 'Sifatli material', 'Качественный материал',
     'Yevropa va Turkiya matolari, rangini yo‘qotmaydigan mexanizmlar.',
     'Европейские и турецкие ткани, механизмы, которые не теряют вид.'),
    ('📏', 'Bepul o‘lchov', 'Бесплатный замер',
     'Mutaxassisimiz sizga qulay vaqtda kelib, aniq o‘lchov oladi.',
     'Наш специалист приедет в удобное время и снимет точные размеры.'),
    ('🎨', 'Dizayner yordami', 'Помощь дизайнера',
     'Interyeringizga mos rang va matoni birga tanlaymiz.',
     'Подберём цвет и ткань под ваш интерьер.'),
    ('🚚', 'Tez yetkazib berish', 'Быстрая доставка',
     'Termiz va Denovga 1 kunda, Surxondaryoning barcha tumanlariga 1–2 kunda yetkazamiz.',
     'По Термезу и Денау за 1 день, во все районы Сурхандарьи — за 1–2 дня.'),
    ('🔧', 'Professional o‘rnatish', 'Профессиональный монтаж',
     'Ustalarimiz derazani teshmasdan ham o‘rnatish variantini taklif qiladi.',
     'Мастера предложат вариант монтажа даже без сверления окна.'),
    ('💳', 'Qulay to‘lov', 'Удобная оплата',
     'Naqd, plastik karta va bo‘lib to‘lash imkoniyati mavjud.',
     'Наличные, карта и возможность рассрочки.'),
]

# DIQQAT: quyidagi sharhlar — namuna (demo) matnlar, haqiqiy mijoz fikri emas.
# Saytni ishga tushirishdan oldin boshqaruv panelidan haqiqiylari bilan almashtiring.
# (ism, kim/shahar, kim_ru, matn, matn_ru, baho)
TESTIMONIALS = [
    ('Dilnoza', 'Termiz', 'Термез',
     'Mehmonxona uchun kun-tun parda oldik. O‘lchovga o‘z vaqtida kelishdi, '
     'o‘rnatish yarim soat ham olmadi. Rangi xuddi katalogdagidek chiqdi.',
     'Заказали шторы день-ночь для гостиной. На замер приехали вовремя, монтаж занял меньше получаса. '
     'Цвет точно такой, как в каталоге.', 5),
    ('Sardor', 'Ofis rahbari', 'Руководитель офиса',
     'Ofisimizning 14 ta derazasiga vertikal jalyuzi qo‘ydirdik. '
     'Hammasi bir kunda tugadi, ishchilar orqasidan tozalab ham ketishdi.',
     'Поставили вертикальные жалюзи на 14 окон офиса. Всё закончили за один день, '
     'после себя убрали.', 5),
    ('Nigora', 'Denov', 'Денау',
     'Yotoqxonaga blackout parda tanlashda dizayner yordam berdi. '
     'Endi kunduzi ham xona qorong‘i — bolam bemalol uxlayapti.',
     'Дизайнер помог подобрать блэкаут для спальни. Теперь днём в комнате темно — '
     'ребёнок спокойно спит.', 5),
]

# Namuna hamkorlar — haqiqiy brendlar emas, o'z mijozlaringiz bilan almashtiring.
# (nomi, tartib)
CLIENTS = [
    ('Interyer studiyasi', 1),
    ('Mebel saloni', 2),
    ('Biznes markazi', 3),
    ('Mehmonxona tarmog‘i', 4),
    ('Qurilish kompaniyasi', 5),
    ('Ofis markazi', 6),
]

FAQS = [
    ('Buyurtma qancha vaqtda tayyor bo‘ladi?', 'Сколько времени занимает изготовление?',
     'O‘lchov olingandan so‘ng odatda 2–5 ish kuni ichida tayyorlanadi va o‘rnatiladi.',
     'После замера изделие изготавливается и устанавливается обычно за 2–5 рабочих дней.'),
    ('O‘lchov xizmati pulli mi?', 'Замер платный?',
     'Yo‘q, Surxondaryo viloyati bo‘ylab o‘lchov va konsultatsiya bepul.',
     'Нет, замер и консультация по Сурхандарьинской области бесплатные.'),
    ('Derazani teshmasdan o‘rnatish mumkinmi?', 'Можно ли установить без сверления окна?',
     'Ha, ba’zi parda turlari uchun profilga qisqich orqali o‘rnatish varianti bor.',
     'Да, для некоторых видов штор есть вариант крепления на профиль клипсами — без сверления окна.'),
    ('Kafolat bormi?', 'Есть ли гарантия?',
     'Mexanizmga 12 oy kafolat beriladi, mato uchun almashtirish sharti alohida kelishiladi.',
     'На механизм даётся гарантия 12 месяцев, условия по ткани обсуждаются отдельно.'),
    ('Pardalarni qanday tozalash kerak?', 'Как чистить шторы?',
     'Ko‘pchilik matolarni nam mato bilan artish yetarli; chuqur tozalash xizmatimiz ham bor.',
     'Большинство тканей достаточно протереть влажной салфеткой; есть услуга глубокой чистки.'),
    ('Tumanlarga yetkazasizmi?', 'Доставляете ли в районы?',
     'Ha, Surxondaryoning barcha 14 tumani va Termiz, Denov shaharlariga yetkazib beramiz — '
     'uzoq tumanlar uchun o‘lchovni telefon orqali tushuntiramiz.',
     'Да, доставляем во все 14 районов Сурхандарьи, а также в Термез и Денау — '
     'для дальних районов объясняем замер по телефону.'),
]

SERVICES = [
    ('tamirlash', '🔧', 'Parda ta’miri', 'Ремонт штор',
     'Karniz, halqa va mexanizmlarni almashtiramiz.', 'Меняем карниз, кольца и механизмы.',
     'Ishlamay qolgan karniz yoki g‘ildirakchalarni, uzilgan ip yoki halqalarni almashtiramiz. '
     'Usta uyingizga kelib joyida ta’mirlaydi.',
     'Заменим неисправный карниз или ролики, порванный шнур или кольца. '
     'Мастер приедет и отремонтирует на месте.'),
    ('tozalash', '🧼', 'Professional tozalash', 'Профессиональная чистка',
     'Matoni shikastlamasdan chuqur tozalash.', 'Глубокая чистка без вреда для ткани.',
     'Pardalarni yechib olib, maxsus vositalar bilan tozalaymiz va qayta o‘rnatib beramiz.',
     'Снимаем шторы, чистим специальными средствами и устанавливаем обратно.'),
    ('dizayn-yangilash', '🎨', 'Dizaynni yangilash', 'Обновление дизайна',
     'Eski konstruksiyaga yangi mato.', 'Новая ткань на старую конструкцию.',
     'Mexanizm butun bo‘lsa, faqat matoni almashtirib interyerni yangilash mumkin — bu arzonroq yechim.',
     'Если механизм цел, можно заменить только ткань — это дешевле полной замены.'),
]

ARTICLES = [
    ('qanday-parda-tanlash', 'Qanday parda tanlash kerak?', 'Как выбрать шторы?',
     'Xona vazifasi, yorug‘lik va interyer uslubiga qarab tanlash bo‘yicha qo‘llanma.',
     'Руководство по выбору в зависимости от назначения комнаты, света и стиля.',
     'Yotoqxona uchun blackout, mehmonxona uchun yengil tul, oshxona uchun esa oson tozalanadigan '
     'rulon pardalar mos keladi. Rangni devor va mebel bilan bir ohangda tanlang.',
     'Для спальни подойдёт блэкаут, для гостиной — лёгкий тюль, для кухни — рулонные шторы, '
     'которые легко чистить. Цвет подбирайте в тон стенам и мебели.'),
    ('parda-matosini-tanlash', 'Parda matosini qanday tanlash kerak', 'Как выбрать ткань для штор',
     'Xona turi, yorug‘lik va tozalash qulayligiga qarab mato tanlash bo‘yicha maslahatlar.',
     'Советы по выбору ткани в зависимости от типа комнаты, освещения и удобства ухода.',
     'Yotoqxona uchun quyuq va og‘ir matolar (baxmal, blackout) tavsiya etiladi — ular yorug‘likni yaxshi '
     'to‘sadi va tovushni yutadi.\n\nMehmonxona va oshxona uchun esa yengil, tez quriydigan va yuviladigan '
     'matolar qulayroq: polyester yoki zig‘ir aralashmasi.\n\nBolalar xonasi uchun gipoallergen, chang '
     'tutmaydigan matolarni tanlang va ularni tez-tez yuvib turing.',
     'Для спальни рекомендуются плотные и тяжёлые ткани (велюр, блэкаут) — они хорошо блокируют свет и '
     'поглощают звук.\n\nДля гостиной и кухни удобнее лёгкие, быстросохнущие и моющиеся ткани: полиэстер '
     'или смесовый лён.\n\nДля детской выбирайте гипоаллергенные ткани, не собирающие пыль, и стирайте их '
     'регулярно.'),
    ('olchov-qollanma', 'Derazani qanday o‘lchash kerak', 'Как правильно замерить окно',
     'Uzoq tumanlardagi mijozlar uchun oddiy o‘lchov qo‘llanmasi.',
     'Простая инструкция по замеру для клиентов из дальних районов.',
     'Kenglikni ramaning ichki qismidan uch joyda o‘lchang va eng kichik qiymatni oling. '
     'Balandlikni ham xuddi shunday o‘lchab, bizga yuboring.',
     'Измерьте ширину внутри рамы в трёх местах и возьмите наименьшее значение. '
     'Высоту измерьте так же и отправьте нам.'),
]

CONTENT_BLOCKS = [
    ('parda-turlari', 'Parda turlari', 'Виды штор',
     '<p>Zamonaviy pardalar assortimentida tyul, portyera, rim pardalar, rulon pardalar va '
     'kombinatsiyalangan (kun-tun) to‘plamlar eng ommabop hisoblanadi. Har biri yorug‘likni boshqarish '
     'darajasi, tozalash qulayligi va narxi bilan farq qiladi.</p>'
     '<p>Yotoqxona uchun yorug‘likni to‘liq to‘sadigan blackout matolar, mehmonxona uchun esa '
     'yorug‘likni yumshoq tarqatadigan yengil tyul tavsiya etiladi.</p>',
     '<p>В ассортименте современных штор самыми популярными считаются тюль, портьеры, римские шторы, '
     'рулонные шторы и комбинированные комплекты день-ночь. Они отличаются степенью светозащиты, '
     'простотой ухода и ценой.</p>'
     '<p>Для спальни рекомендуем ткани блэкаут, полностью перекрывающие свет, для гостиной — лёгкий '
     'тюль, мягко рассеивающий свет.</p>'),
    ('materiallar', 'Materiallar va ularning xususiyatlari', 'Материалы и их особенности',
     '<p><b>Polyester</b> — arzon, oson tozalanadi, rangi uzoq saqlanadi.<br>'
     '<b>Zig‘ir (len)</b> — tabiiy ko‘rinish, yorug‘likni yumshoq tarqatadi.<br>'
     '<b>Baxmal</b> — qalin va qimmatbaho ko‘rinish, shovqinni yutadi.<br>'
     '<b>Blackout</b> — yorug‘likni 100% to‘sadi, yotoqxona uchun ideal.<br>'
     '<b>Organza / tyul</b> — yengil va shaffof, kunduzi xonani yoritadi.</p>',
     '<p><b>Полиэстер</b> — недорогой, легко чистится, долго держит цвет.<br>'
     '<b>Лён</b> — натуральный вид, мягко рассеивает свет.<br>'
     '<b>Велюр</b> — плотный и дорогой вид, поглощает шум.<br>'
     '<b>Блэкаут</b> — задерживает 100% света, идеален для спальни.<br>'
     '<b>Органза / тюль</b> — лёгкая и прозрачная, днём наполняет комнату светом.</p>'),
]


class Command(BaseCommand):
    help = 'Sayt uchun demo kategoriya, mahsulot va kontent yaratadi.'

    # Ishlab turgan saytga chiqarish MUMKIN bo'lgan qismlar. Bu yerda
    # o'ylab topilgan narx, soxta mijoz sharhi va soxta hamkor yo'q —
    # faqat do'konning o'zi haqidagi ma'lumot va tuzilma.
    SAFE_PARTS = {
        'categories': '_categories_with_images',
        'advantages': '_advantages',
        'services': '_services',
        'content': '_content_blocks',
        'banners': '_banners',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--only', nargs='+', choices=sorted(SAFE_PARTS_KEYS),
            help='Faqat ko‘rsatilgan qismlar yaratiladi. Demo mahsulot, '
                 'soxta mijoz sharhi va hamkorlar YARATILMAYDI — ishlab '
                 'turgan saytda ular turishi mumkin emas.',
        )
        parser.add_argument(
            '--categories-only', action='store_true',
            help='`--only categories` bilan bir xil (eski nom).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Demo kontentda ruscha matnlar qo'lda yozilgan — avtomatik tarjima ustidan yozmasin.
        parts = list(options.get('only') or [])
        if options.get('categories_only') and 'categories' not in parts:
            parts.append('categories')
        if parts:
            with mt.suspend():
                for part in parts:
                    getattr(self, self.SAFE_PARTS[part])()
            self.stdout.write(self.style.SUCCESS(
                'Tayyor: %s.' % ', '.join(parts)
            ))
            return

        with mt.suspend():
            ensure_roles()
            self._settings()
            self._banners()
            categories = self._categories()
            created = self._products(categories)
            removed = self._cleanup_old_products()
            self._advantages()
            self._testimonials()
            self._clients()
            self._faqs()
            self._services()
            self._articles()
            self._content_blocks()
        self.stdout.write(self.style.SUCCESS(
            f'Tayyor: {len(categories)} kategoriya, {created} mahsulot yangilandi, '
            f'{removed} ta eski mahsulot tozalandi.'
        ))

    # ------------------------------------------------------------------
    def _settings(self):
        settings_obj = SiteSettings.load()
        settings_obj.brand_name = 'Sevara Design'
        settings_obj.tagline = 'Zamonaviy pardalar'
        settings_obj.tagline_ru = 'Современные шторы'
        settings_obj.about_short = (
            'Sevara Design — Surxondaryo viloyatida zamonaviy pardalarni o‘lchov bo‘yicha tayyorlab, '
            'yetkazib berib va o‘rnatib beradigan kompaniya.'
        )
        settings_obj.about_short_ru = (
            'Sevara Design — компания в Сурхандарьинской области, которая изготавливает по размерам, '
            'доставляет и устанавливает современные шторы.'
        )
        settings_obj.about_full = (
            'Biz 2016-yildan beri Angor tumanida uy va ofislar uchun parda tayyorlaymiz.\n\n'
            'Har bir buyurtma bepul o‘lchovdan boshlanadi: mutaxassisimiz kelib deraza o‘lchamini oladi, '
            'interyeringizga mos mato va rangni tanlashda yordam beradi.\n\n'
            'Xizmatimiz Surxondaryoning barcha 14 tumani hamda Termiz va Denov shaharlarini qamrab oladi.\n\n'
            'Standart buyurtmalar 2–5 kunda tayyor bo‘ladi. Karniz va mexanizmlarga 12 oylik kafolat beramiz va '
            'keyinchalik ta’mir hamda tozalash xizmatlarini taklif qilamiz.'
        )
        settings_obj.about_full_ru = (
            'Мы изготавливаем шторы для дома и офиса в Ангорском районе с 2016 года.\n\n'
            'Каждый заказ начинается с бесплатного замера: специалист приезжает, снимает размеры окна '
            'и помогает подобрать ткань и цвет под ваш интерьер.\n\n'
            'Мы работаем во всех 14 районах Сурхандарьинской области, а также в Термезе и Денау.\n\n'
            'Стандартные заказы готовы за 2–5 дней. На карнизы и механизмы даём гарантию 12 месяцев, а также '
            'предлагаем ремонт и чистку.'
        )
        settings_obj.phone_primary = CONTACT_PHONE
        settings_obj.phone_secondary = ''
        settings_obj.email = 'info@sevaradesign.uz'
        # Aniq ko'cha va uy raqamini boshqaruv panelidan kiriting.
        settings_obj.address = 'Surxondaryo viloyati, Angor tumani'
        settings_obj.working_hours = 'Har kuni 9:00 – 19:00'
        settings_obj.working_hours_ru = 'Ежедневно 9:00 – 19:00'
        settings_obj.telegram_url = 'https://t.me/'
        settings_obj.instagram_url = 'https://instagram.com/'
        settings_obj.save()

    def _banners(self):
        data = [
            ('Har bir derazaga o‘ziga xos parda', 'Для каждого окна — своя штора',
             'Matoni birga tanlaymiz, o‘lchov bo‘yicha tikamiz va uyingizga o‘rnatib beramiz.',
             'Подберём ткань вместе, сошьём по размеру и установим у вас дома.',
             'Katalogni ko‘rish', 'Смотреть каталог', '/uz/katalog/', 1),
            ('O‘lchov bo‘yicha zamonaviy pardalar', 'Современные шторы по размеру',
             'Bepul o‘lchov, dizayner yordami va 2–5 kunda o‘rnatish.',
             'Бесплатный замер, помощь дизайнера и монтаж за 2–5 дней.',
             'Katalogni ko‘rish', 'Смотреть каталог', '/uz/katalog/', 2),
        ]
        titles = set()
        for title, title_ru, sub, sub_ru, btn, btn_ru, url, order in data:
            titles.add(title)
            Banner.objects.update_or_create(
                title=title,
                defaults={
                    'title_ru': title_ru, 'subtitle': sub, 'subtitle_ru': sub_ru,
                    'button_text': btn, 'button_text_ru': btn_ru, 'button_url': url,
                    'sort_order': order, 'is_active': True,
                },
            )
        Banner.objects.exclude(title__in=titles).delete()

    def _categories(self):
        categories = {}
        for order, (slug, name, name_ru, icon, on_home, desc, desc_ru) in enumerate(CATEGORIES, start=1):
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name, 'name_ru': name_ru, 'icon': icon,
                    'description': desc, 'description_ru': desc_ru,
                    'sort_order': order, 'is_active': True, 'show_on_home': on_home,
                },
            )
            categories[slug] = category
        return categories

    def _categories_with_images(self):
        categories = self._categories()
        attached = self._category_images(categories)
        self.stdout.write('  %d kategoriya, %d tasiga rasm biriktirildi.'
                          % (len(categories), attached))

    def _category_images(self, categories):
        """`seed/categories/<slug>.jpg` bo'lsa kategoriyaga biriktiradi.

        Rasmi allaqachon bor kategoriya qayta yozilmaydi — paneldan
        yuklangan rasm joylashtirishda yo'qolib ketmasligi kerak.
        """
        attached = 0
        for slug, category in categories.items():
            if category.image:
                continue
            for suffix in ('.jpg', '.jpeg', '.png', '.webp'):
                path = SEED_CATEGORY_DIR / (slug + suffix)
                if not path.exists():
                    continue
                with path.open('rb') as handle:
                    category.image.save(path.name, File(handle), save=True)
                attached += 1
                break
        return attached

    def _products(self, categories):
        created = 0
        for category_slug, items in PRODUCTS.items():
            category = categories[category_slug]
            for order, item in enumerate(items):
                Product.objects.update_or_create(
                    slug=item['slug'],
                    defaults={
                        'category': category,
                        'name': item['name'],
                        'name_ru': item['name_ru'],
                        'sku': f'{category_slug[:3].upper()}-{order + 1:03d}',
                        'short_description': item['short'],
                        'short_description_ru': item['short_ru'],
                        'description': item['desc'],
                        'description_ru': item['desc_ru'],
                        'price': item['price'],
                        'old_price': item.get('old'),
                        'stock': item['stock'],
                        'is_active': True,
                        'is_featured': item.get('featured', False),
                        'sort_order': order,
                    },
                )
                created += 1
        return created

    def _cleanup_old_products(self):
        """Demo kategoriyalardagi eskirgan mahsulotlarni olib tashlaydi.

        Kategoriyasi yo'qolgan eski demo yozuvlari ham hisobga olinadi: ularning
        slug'i `<kategoriya-slug>-...` shaklida bo'ladi. Buyurtmada ishlatilgan
        mahsulot `OrderItem` PROTECT tufayli o'chirilmaydi — u faqat nofaol qilinadi.
        Foydalanuvchi qo'shgan boshqa kategoriyalarga tegilmaydi.
        """
        current_slugs = {item['slug'] for items in PRODUCTS.values() for item in items}

        legacy_slug = Q()
        for category_slug in PRODUCTS:
            legacy_slug |= Q(slug__startswith=f'{category_slug}-')
        condition = Q(category__slug__in=PRODUCTS.keys()) | (Q(category__isnull=True) & legacy_slug)

        # O'chirish paytida kursorning yozuvlarni o'tkazib yuborishiga yo'l qo'ymaslik uchun ro'yxatga o'giriladi.
        stale = list(Product.objects.filter(condition).exclude(slug__in=current_slugs))
        removed = 0
        for product in stale:
            if product.orderitem_set.exists():
                if product.is_active:
                    product.is_active = False
                    product.save(update_fields=['is_active'])
            else:
                product.delete()
                removed += 1
        return removed

    def _advantages(self):
        for order, (icon, title, title_ru, text, text_ru) in enumerate(ADVANTAGES, start=1):
            Advantage.objects.update_or_create(
                title=title,
                defaults={'icon': icon, 'title_ru': title_ru, 'text': text, 'text_ru': text_ru,
                          'sort_order': order, 'is_active': True},
            )

    def _testimonials(self):
        authors = set()
        for order, (author, role, role_ru, text, text_ru, rating) in enumerate(TESTIMONIALS, start=1):
            authors.add(author)
            Testimonial.objects.update_or_create(
                author=author,
                defaults={'role': role, 'role_ru': role_ru, 'text': text, 'text_ru': text_ru,
                          'rating': rating, 'sort_order': order, 'is_active': True},
            )
        Testimonial.objects.exclude(author__in=authors).delete()

    def _clients(self):
        names = set()
        for name, order in CLIENTS:
            names.add(name)
            Client.objects.update_or_create(
                name=name,
                defaults={'sort_order': order, 'is_active': True},
            )
        Client.objects.exclude(name__in=names).delete()

    def _faqs(self):
        questions = set()
        for order, (question, question_ru, answer, answer_ru) in enumerate(FAQS, start=1):
            questions.add(question)
            FaqItem.objects.update_or_create(
                question=question,
                defaults={'question_ru': question_ru, 'answer': answer, 'answer_ru': answer_ru,
                          'sort_order': order, 'is_active': True},
            )
        FaqItem.objects.exclude(question__in=questions).delete()

    def _services(self):
        slugs = set()
        for order, (slug, icon, name, name_ru, short, short_ru, body, body_ru) in enumerate(SERVICES, start=1):
            slugs.add(slug)
            Service.objects.update_or_create(
                slug=slug,
                defaults={'icon': icon, 'name': name, 'name_ru': name_ru,
                          'short_description': short, 'short_description_ru': short_ru,
                          'description': body, 'description_ru': body_ru,
                          'sort_order': order, 'is_active': True},
            )
        Service.objects.exclude(slug__in=slugs).delete()

    def _articles(self):
        slugs = set()
        for slug, title, title_ru, excerpt, excerpt_ru, body, body_ru in ARTICLES:
            slugs.add(slug)
            Article.objects.update_or_create(
                slug=slug,
                defaults={'title': title, 'title_ru': title_ru, 'excerpt': excerpt,
                          'excerpt_ru': excerpt_ru, 'body': body, 'body_ru': body_ru, 'is_active': True},
            )
        Article.objects.exclude(slug__in=slugs).delete()

    def _content_blocks(self):
        keys = set()
        for order, (key, title, title_ru, body, body_ru) in enumerate(CONTENT_BLOCKS, start=1):
            keys.add(key)
            ContentBlock.objects.update_or_create(
                key=key,
                defaults={'title': title, 'title_ru': title_ru, 'body': body, 'body_ru': body_ru,
                          'show_on_home': True, 'sort_order': order, 'is_active': True},
            )
        ContentBlock.objects.exclude(key__in=keys).delete()
