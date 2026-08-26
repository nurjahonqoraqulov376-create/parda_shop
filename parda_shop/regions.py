# Surxondaryo viloyati — sayt faqat shu hudud bo'ylab ishlaydi.

from django.utils.translation import get_language

REGION = 'Surxondaryo viloyati'
REGION_RU = 'Сурхандарьинская область'

# (qiymat, o'zbekcha, ruscha) — qiymat bazaga yoziladi va o'zgarmaydi.
DISTRICTS = [
    ('termiz-shahri', 'Termiz shahri', 'город Термез'),
    ('denov-shahri', 'Denov shahri', 'город Денау'),
    ('angor', 'Angor tumani', 'Ангорский район'),
    ('bandixon', 'Bandixon tumani', 'Бандиханский район'),
    ('boysun', 'Boysun tumani', 'Байсунский район'),
    ('denov', 'Denov tumani', 'Денауский район'),
    ('jarqorgon', 'Jarqo‘rg‘on tumani', 'Джаркурганский район'),
    ('muzrabot', 'Muzrabot tumani', 'Музрабадский район'),
    ('oltinsoy', 'Oltinsoy tumani', 'Алтынсайский район'),
    ('qiziriq', 'Qiziriq tumani', 'Кизирикский район'),
    ('qumqorgon', 'Qumqo‘rg‘on tumani', 'Кумкурганский район'),
    ('sariosiyo', 'Sariosiyo tumani', 'Сариасийский район'),
    ('sherobod', 'Sherobod tumani', 'Шерабадский район'),
    ('shorchi', 'Sho‘rchi tumani', 'Шурчинский район'),
    ('termiz', 'Termiz tumani', 'Термезский район'),
    ('uzun', 'Uzun tumani', 'Узунский район'),
]

# Model uchun — `get_region_display` o'zbekcha nomni qaytaradi.
DISTRICT_CHOICES = [(value, name) for value, name, _ru in DISTRICTS]

DEFAULT_DISTRICT = 'termiz-shahri'


def _is_ru(language=None):
    return (language or get_language() or '').startswith('ru')


def region_name(language=None):
    """Viloyat nomi joriy tilda."""
    return REGION_RU if _is_ru(language) else REGION


def district_choices(language=None):
    """`(qiymat, nom)` juftliklari — formadagi select uchun."""
    ru = _is_ru(language)
    return [(value, name_ru if ru else name) for value, name, name_ru in DISTRICTS]


def district_label(value, language=None):
    """Bitta tumanning joriy tildagi nomi. Topilmasa qiymatning o'zi qaytadi."""
    ru = _is_ru(language)
    for key, name, name_ru in DISTRICTS:
        if key == value:
            return name_ru if ru else name
    return value or ''
