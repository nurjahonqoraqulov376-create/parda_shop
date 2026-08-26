"""Kategoriya, mahsulot, banner, xizmat va maqolalar uchun rasm generatsiya qiladi.

Rasmlar Pillow bilan chiziladi — internet yoki tashqi fayl talab qilinmaydi.
Har bir kategoriya o'z turiga mos uslubda chiziladi (plisse burmali, zebra yo'lli,
yog'och lamelli va hokazo), rang esa mahsulot nomidagi kalit so'zlardan olinadi.

Buyruq bir necha marta ishga tushirilishi xavfsiz: eski fayllar o'chirilib qayta yoziladi.
"""

import io
import math

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from catalog.models import Category, Product, ProductImage
from pages.models import Article, Banner, Client, Service, Testimonial

W, H = 1000, 750          # mahsulot/kategoriya rasmi
BANNER_W, BANNER_H = 1600, 900

# Deraza o'rni (parda shu to'rtburchak ichida chiziladi)
BOX = (90, 55, 910, 660)

WALL = (238, 234, 228)
SILL = (222, 216, 208)
FRAME = (250, 249, 246)

# Mahsulot nomidagi kalit so'z -> asosiy rang
KEYWORD_COLORS = [
    (('blackout', 'nero', 'notte', 'grafit'), (58, 60, 64)),
    (('bordo',), (118, 42, 48)),
    (('velvet',), (46, 84, 70)),
    (('grey', 'gray', 'office', 'silver', 'metallic'), (140, 145, 148)),
    (('walnut', 'tropic'), (96, 64, 44)),
    (('oak', 'basswood'), (196, 168, 134)),
    (('bamboo', 'bambuk'), (188, 150, 96)),
    (('aqua',), (176, 198, 202)),
    (('gold', 'royal', 'barokko', 'shantung'), (196, 166, 106)),
    (('linen', 'lino', 'natural', 'cream', 'bianco', 'beige', 'perla'), (222, 209, 188)),
    (('ombre',), (170, 158, 190)),
    (('kids',), (170, 196, 210)),
    (('eco',), (150, 168, 140)),
]

# Kalit so'z topilmasa — kategoriya bo'yicha bazaviy ranglar
PALETTE = [
    (214, 202, 184), (186, 190, 186), (200, 178, 156), (170, 176, 178),
    (226, 214, 196), (162, 150, 140), (196, 186, 170), (150, 158, 156),
]

# Kategoriya slug -> chizish uslubi
STYLES = {
    'plisse-jalyuzi': 'plisse',
    'rulon-pardalar': 'roller',
    'kun-tun-combo': 'zebra',
    'zamonaviy-pardalar': 'drape',
    'rim-pardalari': 'roman',
    'klassik-pardalar': 'classic',
    'tekstil-jalyuzi': 'vertical',
    'yogoch-jalyuzi': 'wood',
    'alyuminiy-jalyuzi': 'alu',
    'bambuk-jalyuzi': 'bamboo',
    'plastik-deraza-jalyuzi': 'cassette',
    'logotipli-jalyuzi': 'logo',
    'fotosuratli-jalyuzi': 'photo',
    'moskit-torlari': 'mesh',
}


# ---------------------------------------------------------------- yordamchilar
def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def tone(color, f):
    """Yorug'lik/soya: f > 0 — oqqa, f < 0 — qoraga aralashtiradi.

    Ko'paytirishdan farqli o'laroq to'q ranglarda ham kontrast yo'qolmaydi —
    blackout matolar tekis dog' bo'lib qolmaydi.
    """
    return mix(color, (255, 255, 255), f) if f >= 0 else mix(color, (0, 0, 0), -f)


def lum(color):
    """0..1 oralig'idagi yorqinlik."""
    return (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255


def pick_color(slug, index):
    low = slug.lower()
    for keys, color in KEYWORD_COLORS:
        if any(k in low for k in keys):
            return color
    return PALETTE[index % len(PALETTE)]


def base_canvas(w=W, h=H):
    """Devor, deraza tokchasi va romdan iborat fon."""
    img = Image.new('RGB', (w, h), WALL)
    d = ImageDraw.Draw(img)
    # devorda yumshoq yorug'lik
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=mix(WALL, shade(WALL, 0.90), t))
    x0, y0, x1, y1 = BOX
    # rom
    d.rectangle((x0 - 16, y0 - 16, x1 + 16, y1 + 16), fill=FRAME)
    # tokcha
    d.rectangle((x0 - 40, y1 + 16, x1 + 40, y1 + 40), fill=SILL)
    d.rectangle((x0 - 40, y1 + 40, x1 + 40, y1 + 48), fill=shade(SILL, 0.88))
    return img, d


def fabric(d, box, color, period=46, depth=0.20, phase=0.0):
    """Vertikal burmali mato: har bir ustunga sinus bo'yicha soya beriladi."""
    x0, y0, x1, y1 = box
    for x in range(x0, x1):
        w = math.cos(2 * math.pi * (x - x0) / period + phase)   # -1..1
        d.line((x, y0, x, y1), fill=tone(color, depth * w))


def light_overlay(img, box, strength=0.35):
    """Yuqoridan pastga tushadigan yorug'lik gradienti."""
    x0, y0, x1, y1 = box
    overlay = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    hh = y1 - y0
    for y in range(hh):
        a = int(strength * 255 * (y / hh) ** 1.6)
        od.line((0, y, x1 - x0, y), fill=(20, 18, 16, a))
    img.paste(Image.alpha_composite(
        img.crop(box).convert('RGBA'), overlay).convert('RGB'), (x0, y0))


def finish(img):
    """Yengil yumshatish va vinyetka."""
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    w, h = img.size
    vig = Image.new('L', (w, h), 0)
    ImageDraw.Draw(vig).ellipse((-w * 0.25, -h * 0.35, w * 1.25, h * 1.35), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(140))
    dark = Image.new('RGB', (w, h), (26, 24, 22))
    return Image.composite(img, Image.blend(img, dark, 0.30), vig)


def to_jpeg(img, quality=84):
    buf = io.BytesIO()
    img.convert('RGB').save(buf, 'JPEG', quality=quality, optimize=True)
    return buf.getvalue()


# ------------------------------------------------------------------- uslublar
def draw_plisse(d, box, color, phase=0.0):
    """Akkordeon burmalar — gorizontal zigzag soyalar."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=color)
    step = 17
    for i, y in enumerate(range(y0, y1, step)):
        # burma qirrasi yorug', ichi soyada
        d.rectangle((x0, y, x1, min(y + step, y1)), fill=tone(color, -0.16 if i % 2 else 0.16))
    # yuqori va pastki profil
    d.rectangle((x0, y0, x1, y0 + 14), fill=tone(color, -0.34))
    d.rectangle((x0, y1 - 14, x1, y1), fill=tone(color, -0.34))


def draw_roller(d, box, color, phase=0.0):
    """Rulon parda: tekis mato va tepada val."""
    x0, y0, x1, y1 = box
    fabric(d, (x0, y0 + 26, x1, y1), color, period=150, depth=0.10, phase=phase)
    d.rectangle((x0 - 6, y0, x1 + 6, y0 + 26), fill=shade(color, 0.55))
    d.rectangle((x0, y1 - 12, x1, y1), fill=shade(color, 0.68))   # pastki og'irlik
    d.line((x1 - 30, y0 + 26, x1 - 30, y1 - 80), fill=shade(color, 0.5), width=3)


def draw_zebra(d, box, color, phase=0.0):
    """Kun-tun: shaffof va zich yo'llar navbatlashadi."""
    x0, y0, x1, y1 = box
    light = mix(color, (255, 255, 255), 0.55)
    d.rectangle(box, fill=light)
    step = 34
    for y in range(y0 + 26, y1, step):
        d.rectangle((x0, y, x1, min(y + step // 2, y1)), fill=color)
    d.rectangle((x0 - 6, y0, x1 + 6, y0 + 26), fill=shade(color, 0.55))
    d.rectangle((x0, y1 - 12, x1, y1), fill=shade(color, 0.68))


def draw_drape(d, box, color, phase=0.0):
    """Zamonaviy parda: ikki chetda qalin burmali panellar, o'rtada tul."""
    x0, y0, x1, y1 = box
    tul = mix(color, (255, 255, 255), 0.72)
    fabric(d, (x0, y0, x1, y1), tul, period=30, depth=0.10, phase=phase)
    wpanel = int((x1 - x0) * 0.30)
    fabric(d, (x0, y0, x0 + wpanel, y1), color, period=44, depth=0.30, phase=phase)
    fabric(d, (x1 - wpanel, y0, x1, y1), color, period=44, depth=0.30, phase=phase + 1.1)
    d.rectangle((x0 - 10, y0 - 8, x1 + 10, y0 + 12), fill=(120, 110, 100))  # karniz


def draw_roman(d, box, color, phase=0.0):
    """Rim pardasi: pastda yig'ilgan tekis burmalar."""
    x0, y0, x1, y1 = box
    fabric(d, box, color, period=200, depth=0.08, phase=phase)
    fold_h = 30
    y = y1
    i = 0
    while y > y0 + 150:
        d.rectangle((x0, y - fold_h, x1, y), fill=tone(color, -0.13 if i % 2 else 0.13))
        d.line((x0, y - fold_h, x1, y - fold_h), fill=tone(color, -0.30), width=2)
        y -= fold_h
        i += 1
    d.rectangle((x0, y0, x1, y0 + 12), fill=shade(color, 0.6))


def draw_classic(d, box, color, phase=0.0):
    """Klassika: lambreken, ikki portyera va o'rtada tul."""
    x0, y0, x1, y1 = box
    tul = mix(color, (255, 255, 255), 0.78)
    fabric(d, (x0, y0, x1, y1), tul, period=26, depth=0.09, phase=phase)
    wpanel = int((x1 - x0) * 0.34)
    fabric(d, (x0, y0, x0 + wpanel, y1), color, period=52, depth=0.34, phase=phase)
    fabric(d, (x1 - wpanel, y0, x1, y1), color, period=52, depth=0.34, phase=phase + 0.9)
    # lambreken — pastki chekkasi to'lqinli
    lam = y0 + 78
    d.rectangle((x0 - 12, y0 - 10, x1 + 12, lam), fill=shade(color, 1.05))
    for x in range(x0 - 12, x1 + 12):
        dy = int(18 * (0.5 + 0.5 * math.sin(2 * math.pi * (x - x0) / 150)))
        d.line((x, lam, x, lam + dy), fill=shade(color, 1.05))


def draw_vertical(d, box, color, phase=0.0):
    """Vertikal lamellar."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=shade(color, 0.94))
    lam = 44
    for i, x in enumerate(range(x0, x1, lam)):
        d.rectangle((x, y0 + 16, min(x + lam - 4, x1), y1),
                    fill=tone(color, 0.12 if i % 2 else -0.12))
    d.rectangle((x0 - 8, y0, x1 + 8, y0 + 16), fill=(206, 204, 200))   # karniz


def _slats(d, box, color, thickness, gap, grain=False):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(214, 214, 210))
    for i, y in enumerate(range(y0 + 18, y1, thickness + gap)):
        yy = min(y + thickness, y1)
        d.rectangle((x0, y, x1, yy), fill=tone(color, 0.10 if i % 2 else -0.10))
        d.line((x0, yy - 1, x1, yy - 1), fill=tone(color, -0.34))
        if grain:
            for gx in range(x0 + 20, x1, 90):
                d.line((gx, y + 2, gx + 40, yy - 2), fill=tone(color, -0.18))
    # ko'taruvchi iplar
    for tx in (x0 + int((x1 - x0) * 0.25), x0 + int((x1 - x0) * 0.75)):
        d.line((tx, y0 + 18, tx, y1), fill=tone(color, -0.42), width=2)
    d.rectangle((x0 - 6, y0, x1 + 6, y0 + 18), fill=tone(color, -0.30))


def draw_wood(d, box, color, phase=0.0):
    _slats(d, box, color, thickness=26, gap=6, grain=True)


def draw_alu(d, box, color, phase=0.0):
    _slats(d, box, color, thickness=12, gap=4)


def draw_bamboo(d, box, color, phase=0.0):
    _slats(d, box, color, thickness=9, gap=3, grain=True)


def draw_cassette(d, box, color, phase=0.0):
    """Kasetali rulon: yon yo'naltiruvchilar bilan."""
    x0, y0, x1, y1 = box
    fabric(d, (x0 + 18, y0 + 30, x1 - 18, y1), color, period=160, depth=0.10, phase=phase)
    d.rectangle((x0 - 10, y0, x1 + 10, y0 + 30), fill=(228, 228, 226))     # kaseta
    d.rectangle((x0 - 10, y0, x0 + 18, y1), fill=(232, 232, 230))          # chap profil
    d.rectangle((x1 - 18, y0, x1 + 10, y1), fill=(232, 232, 230))          # o'ng profil
    d.rectangle((x0 + 18, y1 - 12, x1 - 18, y1), fill=shade(color, 0.7))


def draw_logo(d, box, color, phase=0.0):
    """Logotipli rulon parda."""
    draw_roller(d, box, color, phase)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    ink = mix(color, (255, 255, 255), 0.85) if sum(color) < 330 else shade(color, 0.45)
    d.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), outline=ink, width=12)
    d.polygon([(cx - 34, cy + 40), (cx, cy - 46), (cx + 34, cy + 40)], fill=ink)
    d.rectangle((cx - 120, cy + 112, cx + 120, cy + 128), fill=ink)


def draw_photo(d, box, color, phase=0.0):
    """Fotosuratli parda: bosma manzara (osmon, quyosh, tepaliklar)."""
    x0, y0, x1, y1 = box
    sky_top, sky_bot = (86, 122, 168), (236, 196, 152)
    for y in range(y0, y1):
        t = (y - y0) / (y1 - y0)
        d.line((x0, y, x1, y), fill=mix(sky_top, sky_bot, t ** 0.8))
    d.ellipse((x1 - 300, y0 + 80, x1 - 160, y0 + 220), fill=(250, 226, 178))
    horizon = y0 + int((y1 - y0) * 0.62)
    for k, (col, off) in enumerate([((92, 104, 96), 0), ((66, 78, 74), 55)]):
        pts = [(x0, y1), (x0, horizon + off)]
        for x in range(x0, x1 + 1, 40):
            pts.append((x, horizon + off - int(70 * abs(math.sin(x / 220.0 + k)))))
        pts += [(x1, horizon + off), (x1, y1)]
        d.polygon(pts, fill=col)
    d.rectangle((x0 - 6, y0, x1 + 6, y0 + 26), fill=(210, 208, 204))
    d.rectangle((x0, y1 - 12, x1, y1), fill=(180, 178, 174))


def draw_mesh(d, box, color, phase=0.0):
    """Moskit to'ri: ramka va mayda to'r."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        t = (y - y0) / (y1 - y0)
        d.line((x0, y, x1, y), fill=mix((208, 220, 214), (170, 184, 178), t))
    for x in range(x0, x1, 7):
        d.line((x, y0, x, y1), fill=shade(color, 0.72))
    for y in range(y0, y1, 7):
        d.line((x0, y, x1, y), fill=shade(color, 0.80))
    d.rectangle((x0, y0, x1, y1), outline=shade(color, 0.5), width=14)


def load_font(size):
    """Tizimdagi shriftni topadi; topilmasa PIL ning bazaviy shriftiga qaytadi."""
    for path in (r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\arial.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_avatar(letter, color, size=320):
    """Sharh muallifi uchun neytral avatar: yumshoq fon va siluet."""
    img = Image.new('RGB', (size, size), tone(color, 0.55))
    d = ImageDraw.Draw(img)
    silhouette = tone(color, -0.12)
    d.ellipse((size * 0.32, size * 0.20, size * 0.68, size * 0.56), fill=silhouette)   # bosh
    d.ellipse((size * 0.16, size * 0.60, size * 0.84, size * 1.30), fill=silhouette)   # yelka
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    # bosh harf
    d = ImageDraw.Draw(img)
    font = load_font(int(size * 0.30))
    box = d.textbbox((0, 0), letter, font=font)
    d.text(((size - box[2] + box[0]) / 2, size * 0.06), letter,
           font=font, fill=tone(color, 0.85))
    return img


def render_logo(name, w=440, h=170):
    """Hamkor uchun sodda vordmark: emblema va nom."""
    img = Image.new('RGB', (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ink = (110, 118, 116)
    # emblema
    cx, cy, r = 62, h // 2, 34
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ink, width=6)
    d.rectangle((cx - 15, cy - 15, cx + 15, cy + 15), fill=ink)
    # nom (uzun bo'lsa ikki qatorga bo'linadi)
    font = load_font(26)
    words, lines, cur = name.split(), [], ''
    for word in words:
        probe = f'{cur} {word}'.strip()
        if d.textlength(probe, font=font) > w - 130 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = probe
    lines.append(cur)
    y = cy - (len(lines) * 32) // 2
    for line in lines:
        d.text((118, y), line, font=font, fill=ink)
        y += 32
    return img


DRAWERS = {
    'plisse': draw_plisse, 'roller': draw_roller, 'zebra': draw_zebra,
    'drape': draw_drape, 'roman': draw_roman, 'classic': draw_classic,
    'vertical': draw_vertical, 'wood': draw_wood, 'alu': draw_alu,
    'bamboo': draw_bamboo, 'cassette': draw_cassette, 'logo': draw_logo,
    'photo': draw_photo, 'mesh': draw_mesh,
}


def render(style, color, phase=0.0):
    img, d = base_canvas()
    DRAWERS.get(style, draw_roller)(d, BOX, color, phase)
    # To'q matoda soya gradienti kuchsizroq — aks holda tafsilotlar yo'qoladi.
    light_overlay(img, BOX, strength=0.10 + 0.24 * lum(color))
    return finish(img)


def render_wide(curtain, wall):
    """Banner uchun keng sahna: yorug' deraza va ikki chetda burmali pardalar."""
    W_, H_ = BANNER_W, BANNER_H
    img = Image.new('RGB', (W_, H_), wall)
    d = ImageDraw.Draw(img)

    # devor — yuqoridan pastga yengil qorayish
    for y in range(H_):
        d.line((0, y, W_, y), fill=mix(tone(wall, 0.06), tone(wall, -0.12), y / H_))

    # deraza o'rni va undan tushayotgan yorug'lik
    wx0, wy0, wx1, wy1 = int(W_ * 0.18), int(H_ * 0.10), int(W_ * 0.82), int(H_ * 0.86)
    d.rectangle((wx0 - 18, wy0 - 18, wx1 + 18, wy1 + 18), fill=(250, 249, 246))
    sky_t, sky_b = (206, 220, 232), (244, 232, 210)
    for y in range(wy0, wy1):
        d.line((wx0, y, wx1, y), fill=mix(sky_t, sky_b, ((y - wy0) / (wy1 - wy0)) ** 0.8))
    # rom taqsimoti
    d.line(((wx0 + wx1) // 2, wy0, (wx0 + wx1) // 2, wy1), fill=(246, 245, 242), width=14)

    # ikki chetdagi parda panellari
    panel = int(W_ * 0.26)
    for x0, ph in ((0, 0.0), (W_ - panel, 1.2)):
        for x in range(x0, x0 + panel):
            w = math.cos(2 * math.pi * (x - x0) / 96 + ph)
            # chetdan derazaga qarab parda yupqalashadi
            edge = min(1.0, (panel - abs(x - (x0 + panel / 2)) * 2) / panel + 0.55)
            d.line((x, 0, x, H_), fill=tone(curtain, 0.16 * w - 0.10 * (1 - edge)))

    # karniz va tokcha
    d.rectangle((0, 0, W_, 54), fill=tone(curtain, -0.42))
    d.rectangle((wx0 - 60, wy1 + 18, wx1 + 60, wy1 + 46), fill=SILL)
    return finish(img.filter(ImageFilter.GaussianBlur(1.0)))


# -------------------------------------------------------------------- command
class Command(BaseCommand):
    help = "Kategoriya, mahsulot, banner, xizmat va maqolalar uchun rasm yaratadi."

    def add_arguments(self, parser):
        parser.add_argument('--gallery', type=int, default=2,
                            help="Har bir mahsulot uchun qo'shimcha galereya rasmlari soni (default 2).")

    def handle(self, *args, **options):
        n_gallery = max(0, options['gallery'])

        # --- kategoriyalar ---
        cats = 0
        for i, category in enumerate(Category.objects.all()):
            style = STYLES.get(category.slug, 'roller')
            color = pick_color(category.slug, i)
            if category.image:
                category.image.delete(save=False)
            category.image.save(f'{category.slug}.jpg',
                                ContentFile(to_jpeg(render(style, color))), save=True)
            cats += 1
        self.stdout.write(f'  kategoriya rasmlari: {cats}')

        # --- mahsulotlar ---
        prods = gallery = 0
        for i, product in enumerate(Product.objects.select_related('category')):
            slug = product.category.slug if product.category else ''
            style = STYLES.get(slug, 'roller')
            color = pick_color(product.slug, i)

            if product.image:
                product.image.delete(save=False)
            product.image.save(f'{product.slug}.jpg',
                               ContentFile(to_jpeg(render(style, color))), save=True)
            prods += 1

            for old in product.images.all():
                old.image.delete(save=False)
                old.delete()
            for g in range(n_gallery):
                shot = render(style, shade(color, 1.0 - 0.07 * (g + 1)), phase=1.3 * (g + 1))
                photo = ProductImage(product=product, sort_order=g)
                photo.image.save(f'{product.slug}-{g + 1}.jpg',
                                 ContentFile(to_jpeg(shot)), save=True)
                gallery += 1
        self.stdout.write(f'  mahsulot rasmlari: {prods} (+{gallery} galereya)')

        # --- bannerlar ---
        b = 0
        for i, banner in enumerate(Banner.objects.all()):
            if banner.image:
                banner.image.delete(save=False)
            # (parda rangi, devor rangi)
            pair = [((186, 164, 136), (238, 234, 228)), ((122, 138, 130), (234, 232, 226))][i % 2]
            banner.image.save(f'banner-{banner.pk}.jpg',
                              ContentFile(to_jpeg(render_wide(*pair))), save=True)
            b += 1
        self.stdout.write(f'  banner rasmlari: {b}')

        # --- xizmat va maqolalar ---
        s = 0
        for i, service in enumerate(Service.objects.all()):
            if service.image:
                service.image.delete(save=False)
            service.image.save(f'{service.slug}.jpg', ContentFile(
                to_jpeg(render(['roman', 'roller', 'drape'][i % 3], PALETTE[i % len(PALETTE)]))), save=True)
            s += 1
        a = 0
        for i, article in enumerate(Article.objects.all()):
            if article.image:
                article.image.delete(save=False)
            article.image.save(f'{article.slug}.jpg', ContentFile(
                to_jpeg(render(['drape', 'zebra', 'classic'][i % 3], PALETTE[(i + 3) % len(PALETTE)]))), save=True)
            a += 1
        self.stdout.write(f'  xizmat rasmlari: {s}, maqola rasmlari: {a}')

        # --- mijozlar fikri va hamkorlar ---
        t = 0
        for i, item in enumerate(Testimonial.objects.all()):
            if item.photo:
                item.photo.delete(save=False)
            avatar = render_avatar((item.author or '?')[:1].upper(), PALETTE[(i + 1) % len(PALETTE)])
            item.photo.save(f'testimonial-{item.pk}.jpg', ContentFile(to_jpeg(avatar)), save=True)
            t += 1
        cl = 0
        for client in Client.objects.all():
            if client.logo:
                client.logo.delete(save=False)
            client.logo.save(f'client-{client.pk}.jpg',
                             ContentFile(to_jpeg(render_logo(client.name), quality=90)), save=True)
            cl += 1
        self.stdout.write(f'  sharh avatarlari: {t}, hamkor logotiplari: {cl}')

        self.stdout.write(self.style.SUCCESS(
            f'Tayyor: {cats} kategoriya, {prods} mahsulot (+{gallery} galereya), '
            f'{b} banner, {s} xizmat, {a} maqola, {t} avatar, {cl} logotip.'))
