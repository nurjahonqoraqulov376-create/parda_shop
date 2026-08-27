# Sevara Design — zamonaviy pardalar va jalyuzilar

Django asosidagi katalog + savat + buyurtma sayti. Interfeys o‘zbek va rus tillarida.
**Mijozlar uchun ro‘yxatdan o‘tish yo‘q** — buyurtma login talab qilmaydi. Kirish faqat
saytni boshqaradigan xodimlar uchun: `/boshqaruv/kirish/`.

## Ishga tushirish

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py manage.py migrate
py manage.py seed_demo          # demo kategoriya, mahsulot va kontent
py manage.py createsuperuser    # birinchi administrator
py manage.py runserver
```

Sayt: `http://127.0.0.1:8000/uz/` (yoki `/ru/`). Boshqaruv paneli: `/uz/boshqaruv/`.

`.env` da to‘ldirish kerak bo‘lgan yagona narsa — suhbat yordamchisining kaliti
(`GEMINI_API_KEY`, [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
bepul). Qolgani ishlaydigan qiymatlar bilan keladi. **Kalit bo‘sh bo‘lsa ham sayt
to‘liq ishlaydi** — shunchaki suhbatda AI o‘rniga darhol operator chaqiriladi.

### Probniy havola (boshqalarga ko'rsatish uchun)

Saytni internetga vaqtincha ochib, havolasini boshqalarga yuborish uchun
`share.bat` faylini ikki marta bosing (yoki `.\share.ps1`).

```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

ko'rinishidagi havola chiqadi — o'shani nusxalab yuboring.

| | |
|---|---|
| Port | 8765 (`run.bat` ning 8000-porti bilan to'qnashmaydi) |
| Rejim | `DEBUG=False` — xatolarda kod va mijoz ma'lumotlari ko'rinmasligi uchun |
| Qancha ishlaydi | faqat oyna ochiq turganda; yopilsa havola o'chadi |
| Havola | har safar ishga tushirganda **yangi** bo'ladi |

Kerakli `cloudflared.exe` `tools/` papkasida (git'ga kirmaydi).

> Havola ochiq turganda saytga istalgan odam kira oladi — jumladan
> `/uz/boshqaruv/` sahifasiga ham. Kuchli parol qo'ying va ishingiz
> tugagach oynani yoping.

## Sayt tuzilishi

| Bo‘lim | Manzil |
|---|---|
| Bosh sahifa | `/uz/` |
| Katalog / kategoriya | `/uz/katalog/`, `/uz/katalog/<slug>/` |
| Mahsulot | `/uz/mahsulot/<slug>/` |
| Qidiruv | `/uz/qidiruv/?q=...` |
| Savat va rasmiylashtirish | `/uz/savat/`, `/uz/rasmiylashtirish/` |
| Biz haqimizda / Aloqa | `/uz/biz-haqimizda/`, `/uz/aloqa/` |
| Mening ishlarim (portfolio) | `/uz/ishlarimiz/`, `/uz/ishlarimiz/<slug>/` |
| Xodim kirishi | `/uz/boshqaruv/kirish/` |
| Boshqaruv paneli | `/uz/boshqaruv/` |
| Django admin | `/uz/admin/` |

Bosh sahifa bloklari: hero slayder → kategoriyalar → kategoriya bo‘limlari → buyurtma
formasi → 6 ta afzallik → ommabop mahsulotlar → 10% chegirma → yangi mahsulotlar →
mijozlar fikri → hamkorlar → mening ishlarim → bepul konsultatsiya → SEO matn
bloklari → footer.

**Mening ishlarim** — bajarilgan pardalar portfoliosi (`pages.Work`). Yangi ish
boshqaruv panelidagi «Mening ishlarim» bo‘limidan qo‘shiladi: sarlavha, turi
(masalan «Zebra parda»), qisqacha tavsif, to‘liq tavsif va rasm. Ruscha
maydonlar saqlashda avtomatik to‘ladi.

Buyurtma mehmon sifatida beriladi: savat sessiyada saqlanadi, checkout'da ism, telefon va
manzil so‘raladi. Buyurtmalar va callback arizalari boshqaruv panelida ko‘rinadi.

## Suhbat yordamchisi va support roli

Saytning har bir sahifasida o‘ng pastda suhbat oynasi bor. Mijozga birinchi
bo‘lib **sun’iy intellekt** (Google Gemini, bepul tarif) javob beradi.

**Jonli operatorga o‘tish** ikki yo‘l bilan bo‘ladi:

1. Mijoz «jonli operator kerak» (yoki «нужен оператор» va shunga o‘xshash)
   deb yozsa — kalit ibora bo‘yicha darhol. Bu AI o‘chiq bo‘lsa ham ishlaydi.
2. AI javob bera olmasa — o‘zi operatorni chaqiradi.

Shundan keyin **support** rolidagi xodimlarga (va administratorlarga) email
ketadi, panelda esa «Suhbatlar» yonida qizil hisoblagich paydo bo‘ladi.
Operator javob yozgan zahoti AI o‘sha suhbatga aralashmaydi.

### Support roli

`Xodimlar → Yangi xodim → Rol: Support (suhbatlar)`.

Support xodimi **faqat suhbatlarni** ko‘radi — buyurtmalar, mijoz telefonlari,
mahsulot va sozlamalarga ruxsati yo‘q. Kirgandan keyin to‘g‘ridan-to‘g‘ri
suhbatlar sahifasiga tushadi.

### Sozlash

| O‘zgaruvchi | Vazifasi |
|---|---|
| `GEMINI_API_KEY` | Kalit: https://aistudio.google.com/apikey . **Bo‘sh bo‘lsa** AI o‘chadi va mijoz to‘g‘ridan-to‘g‘ri operatorga ulanadi — sayt baribir ishlaydi |
| `GEMINI_MODEL` | Odatiy: `gemini-3.5-flash-lite`. Model nomi o‘zgarsa shu yerdan almashtiriladi |
| `AI_SUPPORT` | `False` qilinsa AI butunlay o‘chadi |
| `EMAIL_*` | Xabar yuborish uchun SMTP. `DEBUG=True` da xat konsolga chiqadi |
| `SUPPORT_NOTIFY_EMAILS` | Xodim profilidagi emaildan tashqari qo‘shimcha manzillar |

### AI nimalarni biladi va nimani qilmaydi

Tizim ko‘rsatmasiga do‘kon nomi, telefoni, ish vaqti, aktiv kategoriyalar va
ularning eng arzon narxi, yetkazib berish tumanlari va saytdan foydalanish
tartibi joylanadi (`support/ai.py`).

AI **faqat shu do‘kon va sayt mavzusida** gaplashadi. Boshqa mavzu (ob-havo,
siyosat, dasturlash, uy vazifasi) so‘ralsa muloyim rad etadi va mavzuni
qaytaradi. Aniq narx yoki o‘lchov so‘ralsa o‘ylab topmaydi — operatorni chaqiradi.
Mijozdan telefon raqami so‘ramaydi.

> **Maxfiylik:** bepul tarifda Google yuborilgan matnni xizmatni yaxshilash
> uchun ishlatishi mumkin. Shuning uchun Gemini’ga yuborishdan oldin matndagi
> telefon raqamlari `[telefon]` bilan niqoblanadi — bazada esa to‘liq saqlanadi
> va operator ko‘radi.

## Hudud — Surxondaryo viloyati

Sayt faqat Surxondaryo bo‘ylab ishlaydi. Tumanlar ro‘yxati bitta joyda —
`parda_shop/regions.py` (`DISTRICTS`: 14 tuman + Termiz va Denov shaharlari, har biri
uchun o‘zbekcha va ruscha nom). Yangi tuman qo‘shish yoki nomni o‘zgartirish uchun
faqat shu faylni tahrirlash kifoya.

- Checkout'dagi «Tuman / shahar» — ochiluvchi ro‘yxat (`Order.region`, `choices`).
  Bazaga `sherobod` kabi qiymat yoziladi, ekranda esa joriy tildagi nom ko‘rinadi.
- Shablonda ko‘rsatish uchun `{{ order.region|district }}` filtri (`site_extras`).
- Manzil va xarita — boshqaruv paneli → **Sozlamalar**dagi «Manzil» va «Xarita
  havolasi» maydonlari (footer va Aloqa sahifasida chiqadi). Xarita uchun Google yoki
  Yandex xaritasining **embed** havolasini kiriting.

## Bildirishnoma (popup)

Sahifa ochilgandan **25 soniya** keyin markazda modal chiqib, telefon raqam
so‘raydi. Bir seansda **bir marta** chiqadi — yopilsa ham qaytmaydi
(`sessionStorage`, kalit `sd-promo-submitted`). Ilgari har 15 soniyada
qayta chiqardi, bu telefonda o‘qishga imkon bermasdi.

- Markup: `templates/base.html` dagi `#modal-promo` (ichida `includes/lead_form.html`).
- Mantiq: `static/js/main.js` — «Bildirishnoma» bo‘limi.
- Matn: `parda_shop/translations.py` dagi `popup.title` va `popup.text`.
- Vaqtni o‘zgartirish: `main.js` dagi `PROMO_DELAY` (millisekund).
- Arizalar panelda **«Bildirishnoma»** turi bilan tushadi (`Lead.TYPES` → `popup`),
  `/uz/boshqaruv/sorovlar/?type=popup` orqali filtrlanadi.

## Dizayn tizimi

Butun ommaviy sayt bitta faylga tayanadi — `static/css/style.css`. Uning boshidagi
`:root` blokida **semantik tokenlar** turadi: sirtlar (`--bg`, `--surface`, `--surface-2`,
`--deep`), matn (`--ink`, `--muted`, `--on-deep`), aksent (`--accent`, `--accent-strong`,
`--accent-soft`), shkalalar (`--r`, `--r-lg`, `--sh-1..3`, `--ease`, `--dur`, `--z-*`).
Rangni o‘zgartirish uchun faqat shu blokni tahrirlang — butun sayt ergashadi.

Eski nomlar (`--soft`, `--radius`, `--shadow`, `--accent-dark`) alias sifatida saqlangan,
shuning uchun eski qoidalar ham ishlaydi.

### Tungi rejim

Topbar’dagi ☀/☾ tugmasi orqali almashadi, tanlov `localStorage['sd-theme']` da saqlanadi.
Tugma bosilmagan bo‘lsa qurilma sozlamasiga ergashadi (`prefers-color-scheme`).

Chaqnashning oldini olish uchun `templates/base.html` `<head>` ida CSS’dan **oldin** kichik
inline skript turadi — u `<html data-theme="…">` ni sahifa chizilishidan avval qo‘yadi.
Bu skriptni CSS linkidan pastga tushirmang.

Yangi rang qo‘shsangiz, uni **uch joyda** aniqlang: `:root`, `:root[data-theme="dark"]` va
`@media (prefers-color-scheme: dark)` bloki. `#fff` kabi to‘g‘ridan-to‘g‘ri rang yozmang —
`var(--surface)` ishlating, aks holda tungi rejimda oq bo‘lib qoladi.

### Animatsiya

`static/js/motion.js` — barcha skroll va kursor effektlari (`main.js` esa menyu, modal,
slayder, galereya kabi UI mexanikasi bilan shug‘ullanadi).

- **Shablonlarga animatsiya atributi yozilmaydi.** `motion.js` mavjud klasslarni
  (`.section-head`, `.card`, `.cat-tile`, `.adv-item`, `.tst-item` …) o‘zi topib
  `IntersectionObserver` ga ulaydi. Yangi bo‘lim qo‘shsangiz — hech narsa qilish shart emas.
- Effektlar: skroll reveal (ketma-ket), hero parallaksi va so‘zma-so‘z sarlavha, kartochkada
  3D tilt + kursor ortidagi yorug‘lik, raqam sanagich, yopishqoq header, skroll progressi,
  sahifalar orasida fade.
- **`prefers-reduced-motion: reduce`** bo‘lsa `motion.js` butunlay chiqib ketadi va
  `<html data-motion="off">` qo‘yadi. Reveal holati faqat `data-motion="on"` da yashiradi,
  ya’ni **JS o‘chiq bo‘lsa ham kontent ko‘rinib turadi**.
- 3D tilt faqat `(hover: hover) and (pointer: fine)` qurilmalarda — telefonlarda yoqilmaydi.

Yangi rasm qo‘shsangiz `width`/`height` atributlarini yozing (kontent sakramasligi uchun);
`img { height: auto }` global qoidasi nisbatni saqlaydi.

## Rollar va kirish

Kirish huquqi **xodim profili** (`accounts.Profile`) orqali beriladi. Profil yaratilishi
bilan signal foydalanuvchini mos Django guruhiga qo‘shadi va `is_staff` ni yoqadi; profil
o‘chirilsa, huquq ham qaytarib olinadi (`accounts/signals.py`).

| Bo‘lim | Support | Menejer | Administrator |
|---|---|---|---|
| Suhbatlar (chat) — ko‘rish va javob berish | ✓ | ✓ | ✓ |
| Umumiy statistika, buyurtmalar, so‘rovlar | — | ✓ | ✓ |
| Mahsulot, kategoriya, ish (portfolio) qo‘shish/tahrirlash | — | ✓ | ✓ |
| Yozuvni o‘chirish | — | — | ✓ |
| Banner, afzallik, mijozlar fikri, hamkor, kontent bloklari | — | — | ✓ |
| Xodimlar (qo‘shish, rol, o‘chirish) va sayt sozlamalari | — | — | ✓ |

**Support** eng tor rol: mijoz bilan yozishadi, xolos. Buyurtma, mijoz telefoni,
mahsulot va sozlamalarga urinsa 403 oladi. Kirgandan keyin to‘g‘ridan-to‘g‘ri
suhbatlar sahifasiga tushadi.

Superuser doim `admin` huquqiga ega. Yangi xodim `/uz/boshqaruv/foydalanuvchilar/yangi/`
sahifasidan qo‘shiladi — login, parol va rol o‘sha yerda beriladi. Guruh ruxsatlarini qayta
yaratish uchun: `py manage.py setup_roles`.

Xodim bo‘lmagan foydalanuvchi login sahifasida to‘g‘ri parol kiritsa ham
"Sizda boshqaruv paneliga ruxsat yo‘q" xatosini oladi (`accounts/forms.py`).

## Tillar (uz / ru)

- URL prefiksi `i18n_patterns` orqali: `/uz/...` va `/ru/...`; headerdagi tugmalar
  `set_language` view’iga POST qiladi.
- **Interfeys matnlari** `parda_shop/translations.py` dagi `UI` lug‘atida, shablonlarda
  `{% t "nav.catalog" %}` tagi orqali chiqariladi. Bu tanlov ataylab: muhitda GNU gettext
  (`msgfmt`) yo‘q, shuning uchun `.po/.mo` kompilyatsiya qilinmaydi.
- **Kontent tarjimasi** modellardagi `_ru` maydonlarda: `name`/`name_ru` va h.k.
  Shablonda `{% tf product "name" %}` joriy tilga mos qiymatni beradi (ruscha bo‘sh bo‘lsa
  o‘zbekchasi ko‘rsatiladi).

### Avtomatik tarjima (uz → ru)

Boshqaruv panelida o‘zbekcha maydonni to‘ldirib saqlaganingizda `_ru` maydoni
**avtomatik tarjima qilinadi** — banner, xizmat, ish (portfolio), mahsulot va sozlamalarda.
Shuning uchun formada `_ru` maydonlari faqat ko‘rish uchun ochiq: har safar saqlaganda
o‘zbekcha matndan qayta yoziladi.

Qanday ishlaydi (`parda_shop/mt.py`):

- Google'ning ochiq `translate_a` endpointi — API kalit ham, qo‘shimcha paket ham kerak emas.
- Natijalar 30 kun keshlanadi, ya'ni o‘zgarmagan matn qayta so‘ralmaydi.
- HTML kontentda (`ContentBlock.body`) teglar tegilmaydi, faqat matn tarjima qilinadi.
- `UI` lug‘atidagi tasdiqlangan iboralar ustuvor: «Batafsil» → «Подробнее» (mashina tarjimasi
  bunday qisqa so‘zlarni kontekstsiz xato o‘giradi).
- **Tarmoq bo‘lmasa maydon o‘zgarishsiz qoladi** — mavjud tarjima yo‘qolmaydi, sayt esa
  ruscha versiya bo‘sh bo‘lsa o‘zbekchasini ko‘rsatadi.

Sozlamalar (`.env`):

| Kalit | Standart | Vazifasi |
|---|---|---|
| `AUTO_TRANSLATE` | `True` | `False` qilinsa avtomatik tarjima butunlay o‘chadi |
| `AUTO_TRANSLATE_TIMEOUT` | `4.0` | Bitta so‘rov uchun soniyada kutish vaqti |

Mavjud yozuvlarni to‘ldirish uchun:

```powershell
py manage.py translate_content --missing   # faqat bo‘sh ruscha maydonlar
py manage.py translate_content             # hammasini qayta tarjima qiladi
py manage.py translate_content --model Banner FaqItem
```

Kodda tarjimani vaqtincha to‘xtatish kerak bo‘lsa (import, seed va h.k.):

```python
from parda_shop import mt

with mt.suspend():
    ...  # bu yerdagi save() lar tarjima qilmaydi
```

## Demo ma'lumot

`py manage.py seed_demo` — 14 kategoriya va har biriga 5 tadan o‘ziga xos mahsulot (jami 70),
har birining nomi, qisqa va to‘liq tavsifi, narxi hamda ombordagi soni alohida yozilgan.
Buyruq idempotent: qayta ishga tushirilsa yozuvlarni yangilaydi va eskirgan demo
mahsulotlarni tozalaydi (buyurtmada ishlatilgani o‘chirilmay, nofaol qilinadi).
Sizning qo‘lda qo‘shgan kategoriya va mahsulotlaringizga tegilmaydi.

## Xavfsizlik

### Git'ga hech qachon tushmaydigan narsalar

`.gitignore` quyidagilarni yopadi — **ularni commit qilmang**:

| Fayl | Nega |
|---|---|
| `.env` | `SECRET_KEY`, Gemini kaliti, SMTP paroli |
| `db.sqlite3` va nusxalari | mijoz buyurtmalari, telefon raqamlari, suhbat yozishmalari |
| `media/` | yuklangan rasmlar (13 MB+) |
| `cookies.txt` | sessiya cookie'lari |
| `tools/`, `*.exe` | binar yordamchilar |

Kod ichida hech qanday sir yo‘q: hamma narsa `env('...')` orqali muhitdan olinadi.
Yangi serverda `.env` ni qo‘lda yaratasiz.

Commit qilishdan oldin tekshirish:

```bash
git status --short           # .env yoki db.sqlite3 ro'yxatda bo'lmasin
git diff --cached --name-only | grep -E '\.env$|sqlite3|cookies'   # hech narsa chiqmasin
```

### Ishlab chiqarish rejimidagi himoya

`DEBUG=False` bo‘lganda avtomatik yoqiladi: `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS=DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`,
`SECURE_REFERRER_POLICY`. HTTPS majburlash va HSTS **ataylab o‘chiq** — cloudflare
tunneli orqasida ular havolani ishdan chiqaradi. Haqiqiy domenga o‘tganda `.env` ga:

```
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

### Boshqa muhim joylar

- **Buyurtma sahifasi** (`/buyurtma/<id>/rahmat/`) faqat egasiga ochiq — raqamni
  almashtirib begona mijozning ma’lumotini ko‘rib bo‘lmaydi.
- **Ombor** buyurtma vaqtida tranzaksiya ichida tekshiriladi va `F()` bilan ayiriladi.
- **Savat** buzilgan sessiyada ham yiqilmaydi — yaroqsiz qatorlar tashlanadi.
- **Xodim parollari** uchun Django validatorlari yoqilgan (kamida 8 belgi).
- **Suhbat** matni Gemini'ga yuborilishidan oldin telefon raqamlari niqoblanadi.

## Testlar

```bash
py manage.py test              # 115 ta test
py manage.py test support      # faqat suhbat tizimi
py manage.py check --deploy    # xavfsizlik sozlamalari
```

Har bir test bir marta topilgan aniq xatoni qo‘riqlaydi — nomlari o‘zbekcha va
nima tekshirilayotgani yozilgan. Testlar **hech qachon tarmoqqa chiqmaydi**:
`AUTO_TRANSLATE` va `AI_SUPPORT` o‘chiriladi, Gemini javobi soxtalashtiriladi.
Shuning uchun `.env` da haqiqiy kalit tursa ham testlar tez va bepul.

Qamrov: savat va buyurtma oqimi, ombor, ruxsatlar, eskalatsiya, AI qatlami,
tarjima lug‘ati, mobil moslashuv, panel bo‘limlari.

`.github/workflows/tests.yml` — har `git push` da GitHub o‘zi `check`,
`makemigrations --check` va barcha testlarni ishga tushiradi.

## Loyiha tuzilishi

```
accounts/    Profile (rol), login formasi, rol guruhlari, ruxsat dekoratorlari
catalog/     Category, Product, ProductImage + katalog/qidiruv view'lari
orders/      sessiyadagi Cart, Order/OrderItem, Lead (ariza formalari)
pages/       SiteSettings, Banner, Advantage, Testimonial, Client, Work, ContentBlock
support/     Conversation, Message + ai.py (Gemini), escalation.py, notifications.py
dashboard/   /boshqaruv/ paneli (registry asosidagi generic CRUD + buyurtma/lead/xodim/chat)
templates/   base.html, includes/, pages/, catalog/, orders/, dashboard/
static/      css/style.css (sayt), css/dashboard.css (panel), js/main.js, js/support.js
```

## Production

Serverga qo‘yishdan oldin:

1. `.env` ni **qo‘lda yarating** (git'da yo‘q) va to‘ldiring:
   `DEBUG=False`, kuchli `SECRET_KEY`, haqiqiy `ALLOWED_HOSTS` va
   `CSRF_TRUSTED_ORIGINS`, `GEMINI_API_KEY`, `EMAIL_*`, `SITE_BASE_URL`.
2. `py manage.py migrate` — bo‘sh bazada ham ishlaydi (migratsiya tartibi
   `run_before` bilan majburlangan).
3. `py manage.py setup_roles` — Support / Menejer / Administrator guruhlari.
4. `py manage.py createsuperuser` — birinchi administrator.
5. `py manage.py collectstatic`.
6. `py manage.py check --deploy` — ogohlantirishlarni ko‘rib chiqing.

Statik va media fayllarni nginx bersin (`SERVE_MEDIA=False`), bazani SQLite'dan
PostgreSQL'ga ko‘chiring, HTTPS uchun `SECURE_SSL_REDIRECT=True` va
`SECURE_HSTS_SECONDS=31536000` qo‘shing.

> Suhbat yozishmalari bazada saqlanadi va mijoz telefon raqamini yozgan bo‘lishi
> mumkin — baza nusxalarini himoyalangan joyda saqlang.
