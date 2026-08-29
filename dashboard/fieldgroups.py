"""Forma maydonlarini mazmuniga qarab guruhlarga ajratadi.

Nima uchun
----------
Ilgari mahsulot formasi 15 dan ortiq maydonni bitta uzun ustunga
tizib qo'yardi: nomi, slug, narx, ombor, tavsif, rasm, belgilar —
hammasi aralash. Yangi xodim nimadan boshlashni ham bilmasdi.

Bu yerda maydonlar NOMI bo'yicha guruhlanadi, ya'ni har bir model uchun
alohida sozlash shart emas — yangi model qo'shilsa ham ishlayveradi.
Tanish bo'lmagan maydon oxirgi guruhga tushadi, ya'ni hech biri
yo'qolmaydi.
"""

# (guruh nomi, izoh, maydon nomlari)
GROUPS = [
    ('Asosiy ma’lumot', 'Ro‘yxatda va sayt sahifasida shu ko‘rinadi.', (
        'name', 'title', 'author', 'slug', 'category', 'icon', 'key', 'sku',
    )),
    ('Narx va ombor', 'Narxni so‘mda, faqat raqam bilan yozing.', (
        'price', 'old_price', 'stock', 'unit',
    )),
    ('Matnlar', 'Ruscha variantini tizim o‘zi tarjima qiladi.', (
        'excerpt', 'short_description', 'description', 'body', 'text',
        'tagline', 'subtitle', 'lead',
    )),
    ('Rasm', 'Eng yaxshi natija: keng (gorizontal) surat, 1200px dan katta.', (
        'image', 'photo', 'logo', 'cover',
    )),
    ('Havolalar', '', (
        'url', 'link', 'button_url', 'button_text',
    )),
    ('Ko‘rsatish', 'Saytda qayerda va qanday tartibda chiqishini boshqaradi.', (
        'sort_order', 'is_active', 'is_featured', 'show_on_home', 'rating',
    )),
]

# Oxirgi guruh: yuqoridagilarga tushmagan maydonlar.
OTHER_TITLE = 'Qo‘shimcha'


def group_fields(form):
    """Formani `[{'title', 'note', 'fields': [...]}, ...]` ko'rinishida beradi.

    Bo'sh guruhlar tashlab yuboriladi. Ruscha (`_ru`) maydonlar avtomatik
    to'ldirilgani uchun o'z guruhida emas, tarjimasi bilan yonma-yon turadi.
    """
    remaining = {field.name: field for field in form}
    result = []

    for title, note, names in GROUPS:
        picked = []
        for name in names:
            for candidate in (name, name + '_ru'):
                field = remaining.pop(candidate, None)
                if field is not None:
                    picked.append(field)
        if picked:
            result.append({'title': title, 'note': note, 'fields': picked})

    if remaining:
        result.append({'title': OTHER_TITLE, 'note': '',
                       'fields': list(remaining.values())})
    return result
