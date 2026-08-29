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

## Panel yordamchisi (AI agent)

Boshqaruv panelida **✦ Yordamchi** bo‘limi bor — menejer va administrator
uchun. Uch ishni qiladi:

1. **Savolga javob beradi.** «Bugun nechta buyurtma keldi?», «Qaysi
   mahsulotning ombori tugayapti?» — raqamlar bazadan real vaqtda olinadi.
2. **Qo‘shishda yordam beradi.** Mahsulot, kategoriya yoki portfolio ishi
   uchun matn tuzib beradi va uni yozib qo‘yishni **taklif qiladi**.
3. **Nazorat qilib turadi.** Sahifa tepasida kutayotgan suhbat, javobsiz
   so‘rov, tugagan ombor ko‘rinadi va har daqiqada yangilanadi.

Suhbat yordamchisi bilan bir xil Gemini kalitidan foydalanadi
(`GEMINI_API_KEY`). Kalit bo‘lmasa bo‘lim ochiladi, faqat javob bermaydi.

### Nega u o‘zi hech narsa yozmaydi

Agent xodim nomidan bazaga yozadi, shuning uchun yozish yo‘li ataylab tor:

| To‘siq | Qayerda |
|---|---|
| Rol tekshiruvi (faqat menejer va administrator) | `dashboard/views.py` |
| Amallarning **oq ro‘yxati** | `dashboard/agent.py` → `ACTIONS` |
| Ro‘yxatdan tashqari maydonlar tashlanadi | `parse_action` |
| **Tasdiqlash** — tugma bosilmaguncha baza o‘zgarmaydi | `agent_run_pending` |
| Yozuv panelning o‘z formasidan o‘tadi | `dashboard/agent_run.py` |
| Har bir amal jurnalga tushadi (kim, qachon, nima) | `AgentAction` modeli |

**O‘chirish amali umuman yo‘q** va qo‘shilmasligi kerak — buni test
qo‘riqlaydi. Menejer administratorgina kiradigan bo‘limlarga (banner,
sozlamalar) yozolmaydi.

Yordamchini butunlay o‘chirish: `AI_AGENT=False`.

### Javob kelmasa

Xodimga **sababi** ko'rsatiladi, umumiy «javob bera olmadi» emas:

| Sabab | Xabar |
|---|---|
| Kvota/limit (HTTP 429, 5xx) | «Yordamchi band — yarim daqiqadan keyin qayta yuboring». Avval bir marta o'zi qayta urinadi. |
| Javob kechikdi | «Savolni qisqaroq qilib qayta yuboring» |
| Javob chegaraga sig'madi (`MAX_TOKENS`) | «Savolni bo'lib-bo'lib so'rang» |
| Kalit yo'q, tarmoq yo'q | «Keyinroq urinib ko'ring» |

Har bir nosozlik server jurnaliga Gemini qaytargan kod va matn bilan
yoziladi — sababni keyin topsa bo'ladi.

Testlar: `dashboard/tests_agent.py` (61 ta, hech biri tarmoqqa chiqmaydi).

## Qidiruv tizimlari uchun

| Manzil | Nima |
|---|---|
| `/robots.txt` | Robotlarga yo'l ko'rsatadi; panel va savat indeksga tushmaydi. Sitemap manzili **joriy domendan** olinadi — domen almashsa qo'lda tahrirlash kerak emas. |
| `/sitemap.xml` | Bosh sahifa, katalog, kategoriyalar, mahsulotlar, portfolio — ikkala tilda (`pages/sitemaps.py`). Nofaol yozuvlar chiqmaydi. |
| `/favicon.ico` | Brend belgisi. Ilgari yo'q edi va jurnalga sahifa ochilgani sayin 404 tushardi. Ildizdagi manzil statik faylga yo'naltiradi — brauzer uni aynan shu yerdan so'raydi. |

Ikkala manzil ham **til prefiksisiz** (`i18n_patterns` dan tashqarida):
robotlar ularni aynan saytning ildizidan qidiradi.

> ⚠️ **`ensure_site` buyrug'i Pre-deploy Command da turishi shart.**
> `sitemap.xml` manzillarni `django.contrib.sites` jadvalidan quradi va
> u yerda o'rnatilganda `example.com` yozilgan bo'ladi — tegilmasa butun
> xarita yaroqsiz chiqadi. Buyruq domenni `SITE_DOMAIN` yoki
> `RAILWAY_PUBLIC_DOMAIN` dan olib yangilaydi.

Google'ga qo'shish: [Search Console](https://search.google.com/search-console)
→ saytni qo'shing → **Sitemaps** → `sitemap.xml` ni yuboring.

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

## Panel telefonda

Yon menyu tor ekranda (≤820px) **yig'ilib** turadi: tepada faqat brend va
☰ tugmasi qoladi, kontent esa darhol ekranning tepasida ko'rinadi.

Ilgari menyu bir ustunga tushib, o'nlab havolasi bilan butun tepani
egallardi — «Buyurtmalar» ga bosgan odam sahifa o'rniga yana o'sha
menyuni ko'rar, kerakli jadval esa ancha pastda qolardi.

- Bo'limga o'tilganda menyu o'zi yopiladi
- Joriy bo'lim menyuda belgilanadi (`.is-current`)
- Bosish maydonlari 44px — barmoq uchun qulay o'lcham
- Yon panel tepada yopishib turadi, ya'ni menyu doim qo'l ostida

Tekshiruv: `dashboard/tests_mobile.py` (15 ta test).

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

### Panelga qayerdan kiriladi

Sarlavhaning o‘ng tomonidagi **Kirish** tugmasi orqali, yoki to‘g‘ridan-to‘g‘ri
`/uz/boshqaruv/kirish/` manzilidan. Kirgan xodimga bu tugma o‘rniga
**Panel** va **Chiqish** ko‘rinadi.
Tekshiruv: `pages/tests_smoke.py` → `HeaderLoginLinkTests`.

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

`py manage.py seed_demo --categories-only` — faqat 14 kategoriya (rasmi bilan),
demo mahsulotlarsiz. Ishlab turgan saytni to‘ldirish uchun shu variant ishlatiladi:
o‘ylab topilgan narx mijozni chalg‘itmasligi kerak.

`py manage.py import_works` — `seed/works/` dagi 8 ta portfolio rasmini
«Mening ishlarim» bo‘limiga yuklaydi. Yozuvlar slug bo‘yicha yangilanadi,
takror yaratilmaydi.

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

## Railway'ga joylashtirish — qadamma-qadam

Loyiha Railway uchun tayyorlab qo'yilgan: `Procfile`, `railway.json`,
WhiteNoise (statik fayllar), PostgreSQL qo'llab-quvvatlash va konsolga
loglar. Quyidagi qadamlarni ketma-ket bajaring.

### 0-qadam. Kerakli narsalar

- GitHub'dagi repozitoriy (bor: `nurjahonqoraqulov376-create/parda_shop`)
- Railway hisobi — https://railway.app , GitHub bilan kiriladi
- Gemini kaliti — https://aistudio.google.com/apikey (bepul)

### 1-qadam. `SECRET_KEY` yaratib olish

Terminalda:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(50))"
```

Chiqqan satrni nusxalab qo'ying — 3-qadamda kerak bo'ladi.

> Bu kalitni **hech kimga bermang va git'ga qo'ymang**. U sessiya va parol
> tiklash tokenlarini imzolaydi. Mahalliy `.env` dagi kalitdan boshqa,
> yangi kalit bo'lsin.

### 2-qadam. Loyihani Railway'ga ulash

1. https://railway.app → **New Project**
2. **Deploy from GitHub repo** → `parda_shop` ni tanlang
3. Railway o'zi Python loyihasini tanib, qura boshlaydi

Birinchi qurish **xato bilan tugaydi** — bu normal, hali `SECRET_KEY` va
baza yo'q. Keyingi qadamlarda qo'shamiz.

### 3-qadam. PostgreSQL qo'shish

Loyiha ichida: **+ New** → **Database** → **Add PostgreSQL**

Railway `DATABASE_URL` o'zgaruvchisini o'zi yaratadi va ilovaga ulaydi —
qo'lda hech narsa yozish shart emas.

> **SQLite Railway'da yaramaydi.** Fayl tizimi har qayta joylashda
> tozalanadi, ya'ni butun baza — buyurtmalar, mijozlar, suhbatlar —
> yo'qoladi. Shuning uchun PostgreSQL majburiy.

### 4-qadam. O'zgaruvchilarni kiritish

Ilova xizmatini bosing → **Variables** → **New Variable**. Quyidagilarni
qo'shing:

| Nomi | Qiymati |
|---|---|
| `SECRET_KEY` | 1-qadamda chiqqan satr |
| `DEBUG` | `False` |
| `GEMINI_API_KEY` | AI Studio'dagi kalit |
| `AUTO_TRANSLATE` | `True` |

Email uchun (support xabarnomalari kerak bo'lsa):

| Nomi | Qiymati |
|---|---|
| `EMAIL_HOST` | masalan `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | pochta manzilingiz |
| `EMAIL_HOST_PASSWORD` | ilova paroli (oddiy parol emas!) |
| `DEFAULT_FROM_EMAIL` | pochta manzilingiz |
| `SITE_BASE_URL` | `https://<domeningiz>.up.railway.app` |

`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PORT`, `DATABASE_URL` —
**yozmang**, Railway domenidan avtomatik olinadi.

### 5-qadam. Rasmlar uchun Volume (MUHIM)

Railway fayl tizimi vaqtinchalik: har qayta joylashda tozalanadi. Volume
qo'shmasangiz **yuklangan barcha rasmlar yo'qoladi**.

Ilova xizmati → **Settings** → **Volumes** → **New Volume**

- Mount path: `/app/media`
- Hajm: 1 GB yetadi (hozircha rasmlar 1.5 MB)

### 6-qadam. Domen ochish

**Settings** → **Networking** → **Generate Domain**

`https://parda-shop-production-xxxx.up.railway.app` ko'rinishida havola
chiqadi. Shu domen `ALLOWED_HOSTS` ga o'zi qo'shiladi.

### 7-qadam. Qayta joylashtirish

**Deployments** → oxirgisining yonidagi uch nuqta → **Redeploy**

Buyruqlar Railway'ning **Settings** bo'limida qo'lda yoziladi
(`railway.json` 2026-08-28 dan keyingi yangi xizmatlarda ishlamaydi):

| Qayerda | Nima yoziladi |
|---|---|
| Settings → Build → **Custom Build Command** | `python manage.py collectstatic --noinput` |
| Settings → Deploy → **Custom Start Command** | `python manage.py restore_media; gunicorn parda_shop.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile - --error-logfile -` |
| Settings → Deploy → **Pre-deploy Command** | `python manage.py migrate --noinput && python manage.py setup_roles && python manage.py ensure_admin && python manage.py ensure_site` |

> ⚠️ **Migratsiyani `Procfile` ning `release:` qatoriga YOZMANG.** Nixpacks
> uni QURISH bosqichiga qo'shadi, u yerda esa Railway'ning ichki tarmog'i hali
> yo'q — `postgres.railway.internal` topilmaydi va qurish
> «failed to resolve host» xatosi bilan to'xtaydi. Migratsiya faqat
> **Pre-deploy Command** da bo'lishi kerak: u ishlash paytida bajariladi va
> bazaga ulana oladi.

### 8-qadam. Birinchi administrator

Railway'da brauzerdan terminal ochib bo‘lmaydi (**Shell** SSH kalit so‘raydi),
shuning uchun administrator hisobi **muhit o‘zgaruvchilari** orqali yaratiladi.
Buning uchun `ensure_admin` buyrug‘i bor — u 7-qadamdagi **Pre-deploy Command**
ichida turadi.

**Variables** bo‘limiga ikkita o‘zgaruvchi qo‘shing:

| Nomi | Qiymati |
|---|---|
| `ADMIN_USERNAME` | o‘zingiz tanlagan login |
| `ADMIN_PASSWORD` | kuchli parol (kamida 12 belgi) |

Saqlaganingizda Railway o‘zi qayta joylashtiradi. Loglarda quyidagi qator
ko‘rinadi:

```
ensure_admin: <login> — yaratildi (administrator)
```

Endi kirish mumkin: `https://<domen>/uz/boshqaruv/kirish/`

> 🔒 **Kirgandan keyin `ADMIN_PASSWORD` ni Variables'dan O‘CHIRIB TASHLANG.**
> Parol o‘zgaruvchilarda ochiq matnda turishi kerak emas — u bazaga
> shifrlangan holda saqlanib bo‘ldi. `ensure_admin` o‘zgaruvchilar yo‘q
> bo‘lsa hech narsa qilmaydi, shuning uchun uni Pre-deploy'da qoldirish xavfsiz.
>
> Parolni keyin almashtirish uchun `ADMIN_PASSWORD` ni yangi qiymat bilan
> qaytadan qo‘ying — buyruq mavjud hisobning parolini yangilaydi.

### 9-qadam. Kontentni to'ldirish

> ⚠️ **Ikki xil saqlash joyi.** Baza — Postgres'da, rasmlar — alohida
> ulanadigan diskda (volume). **Pre-deploy buyruqlari disk ULANMAGAN
> konteynerda ishlaydi.** Ya'ni pre-deploy'da rasm saqlasangiz, bazaga yozuv
> tushadi, fayl esa yo'qoladi — saytda barcha `/media/...` manzillari 404
> beradi. Bu xato bir marta yuz bergan.
>
> Shu sababli loyihada **`restore_media`** buyrug'i bor va u **ishga tushirish
> buyrug'ida** turadi (7-qadamdagi Custom Start Command). U `seed/` dagi
> nusxalardan faqat **yo'q** fayllarni tiklaydi — paneldan yuklangan
> rasmga tegmaydi.

Yozuvlarni yaratish uchun **Pre-deploy Command** ga vaqtincha qo'shing,
so'ng olib tashlang:

| Nima | Buyruq |
|---|---|
| Kategoriya tuzilmasi, afzalliklar, xizmatlar | `python manage.py seed_demo --only categories advantages services content` |
| «Mening ishlarim» portfolio (8 ta) | `python manage.py import_works` |

Rasm fayllarini keyingi ishga tushishda `restore_media` o'zi joyiga qo'yadi.

> ⚠️ **`seed_demo` ni bayroqsiz ishlatmang.** To'liq variant uchta
> narsani yaratadi va ular haqiqiy do'konda turishi mumkin emas: o'ylab
> topilgan nom va narxli 70 ta mahsulot, soxta mijoz sharhlari va soxta
> hamkorlar ro'yxati. `--only` bularga yo'l bermaydi — unga faqat
> do'konning o'zi haqidagi ma'lumot va tuzilma kiradi:
> `advantages`, `banners`, `categories`, `content`, `services`, `settings`.
>
> `settings` faqat **bo'sh** maydonlarni to'ldiradi — paneldan kiritgan
> matningizni qayta yozmaydi. Email va ijtimoiy tarmoq havolalariga umuman
> tegmaydi: demo qiymatlari haqiqiy emas, ularni o'zingiz kiritasiz.

Mahsulotlarni panelga kirib qo'lda qo'shasiz:
`/uz/boshqaruv/mahsulotlar/` → **Qo'shish**.
Portfolio ham shu yerda: `/uz/boshqaruv/ishlarimiz/`.


### 10-qadam. Tekshirish

| Nima | Kutilgan |
|---|---|
| `https://<domen>/` | `/uz/` ga yo'naltiradi |
| Sahifa ko'rinishi | css ishlaydi (WhiteNoise) |
| `/uz/boshqaruv/kirish/` | kirish sahifasi |
| Suhbat oynasi | savol yozilganda AI javob beradi |
| `http://` bilan kirish | avtomatik `https://` ga o'tadi |

Xato bo'lsa: **Deployments** → **View Logs**. Barcha xatolar konsolga
yoziladi (`LOGGING` shunga sozlangan).

---

### Keyingi yangilanishlar

```powershell
git add -A
git commit -m "o'zgarish tavsifi"
git push
```

Railway `push` ni sezib, o'zi qayta quradi va joylaydi. Migratsiyalar ham
avtomatik bajariladi.

### Tez-tez uchraydigan xatolar

| Xato | Sabab va yechim |
|---|---|
| `Set the SECRET_KEY environment variable` | 4-qadam bajarilmagan |
| `DisallowedHost` | Domen hali yaratilmagan (6-qadam) yoki o'z domeningizni `ALLOWED_HOSTS` ga qo'shish kerak |
| Sahifa bor, lekin uslubsiz (oq) | `collectstatic` o'tmagan — qurish loglarini ko'ring |
| Rasmlar qayta joylashdan keyin yo'qoldi | Volume ulanmagan (5-qadam) |
| `CSRF verification failed` | O'z domeningizni ishlatsangiz `CSRF_TRUSTED_ORIGINS` ga `https://domen.uz` qo'shing |
| Suhbatda AI javob bermaydi | `GEMINI_API_KEY` yo'q yoki noto'g'ri — sayt buzilmaydi, operatorga ulaydi |

### Narx haqida

Railway'ning bepul tarifi cheklangan (oyiga ~$5 kredit). Kichik sayt uchun
odatda yetadi, lekin trafik oshsa to'lov kerak bo'ladi. PostgreSQL va
Volume ham shu kreditdan yeydi. Sarfni **Usage** bo'limida kuzatasiz.
