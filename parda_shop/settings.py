from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / '.env')

DEBUG = env('DEBUG')

# Ishlab chiqarishda kalit MAJBURIY. Zaxira qiymat qoldirilsa, `.env` ni
# unutgan holda sayt jimgina hammaga ma'lum kalit bilan ishlab ketardi —
# bu sessiya va parol tiklash tokenlarini soxtalashtirishga yo'l ochadi.
if DEBUG:
    SECRET_KEY = env('SECRET_KEY', default='django-insecure-faqat-ishlab-chiqish-uchun')
else:
    SECRET_KEY = env('SECRET_KEY')  # yo'q bo'lsa server ko'tarilmaydi

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=['http://127.0.0.1:8000', 'http://localhost:8000'],
)

# Railway domenni o'zi beradi — uni qo'lda yozib qo'yish shart emas.
RAILWAY_DOMAIN = env('RAILWAY_PUBLIC_DOMAIN', default='')
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append('https://%s' % RAILWAY_DOMAIN)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'accounts',
    'catalog',
    'orders',
    'pages',
    'dashboard',
    'support',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serverda nginx yo'q — css/js ni WhiteNoise beradi. SecurityMiddleware'dan
    # keyin, qolganlaridan oldin turishi shart.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'parda_shop.middleware.NoCacheMiddleware',
]

ROOT_URLCONF = 'parda_shop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'parda_shop.context_processors.site_context',
            ],
        },
    }
]

WSGI_APPLICATION = 'parda_shop.wsgi.application'

# Railway (va boshqa serverlar) `DATABASE_URL` beradi. Mahalliy ishlashda u
# yo'q — SQLite ishlatiladi. Railway'da SQLite YARAMAYDI: fayl tizimi har
# qayta joylashda tozalanadi va butun baza yo'qoladi.
DATABASES = {
    'default': env.db_url(
        'DATABASE_URL',
        default='sqlite:///%s' % (BASE_DIR / 'db.sqlite3'),
    ),
}
# Har so'rovda yangi ulanish ochilmasin (PostgreSQL uchun sezilarli tezlik).
if not DATABASES['default']['ENGINE'].endswith('sqlite3'):
    DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=60)
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Xodim parollari uchun eng kam talablar. Mijozlar ro'yxatdan o'tmaydi,
# lekin boshqaruv paneli hisoblari zaif parol bilan qolmasligi kerak.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
LANGUAGES = [('uz', "O'zbekcha"), ('ru', 'Русский')]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise fayllarni siqadi va nomiga hash qo'shadi (brauzer keshi eski
# css'ni ushlab qolmasin). `collectstatic` bajarilishi shart.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Yuklangan rasmlarni (media) Django o'zi bersinmi.
#
# Railway'da nginx yo'q, shuning uchun u yerda o'zi yoqiladi. MUHIM: Railway
# fayl tizimi vaqtinchalik — har qayta joylashda tozalanadi. Rasmlar
# yo'qolmasligi uchun Railway'da Volume yaratib, uni `/app/media` ga ulash
# SHART (README dagi qadamlarga qarang).
SERVE_MEDIA = env.bool('SERVE_MEDIA', default=bool(RAILWAY_DOMAIN))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# `django.contrib.sites` eski allauth jadvallari uchun saqlanmoqda.
SITE_ID = 1

# Kirish faqat xodimlar uchun — boshqaruv paneli ichidagi login sahifasi.
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
LOGIN_URL = reverse_lazy('dashboard:login')
# Kirgandan keyin rolga qarab yo'naltiriladi (support -> suhbatlar).
LOGIN_REDIRECT_URL = reverse_lazy('dashboard:after_login')
LOGOUT_REDIRECT_URL = '/'

# Tunnel/reverse-proxy orqasida ishlaganda (masalan cloudflared bilan probniy
# havola) so'rov Django'ga http bo'lib yetadi, lekin tashqarida u https.
# Faqat ishonchli proksi oldida turganda yoqing — aks holda header'ni
# soxtalashtirish mumkin.
# Railway'da bu avtomatik yoqiladi: TLS Railway tomonida tugaydi, Django'ga
# so'rov http bo'lib yetadi, lekin tashqarida u https.
if env.bool('BEHIND_PROXY', default=bool(RAILWAY_DOMAIN)):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# --------------------------------------------------------------------------
# Ishlab chiqarish rejimidagi (DEBUG=False) xavfsizlik sozlamalari.
# Mahalliy ishlashda (DEBUG=True) yoqilmaydi, aks holda http://127.0.0.1
# https'ga yo'naltirilib, sayt ochilmay qolardi.
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Tunnel orqasida SSL'ni Django emas, proksi hal qiladi — shuning uchun
    # yo'naltirishni alohida yoqiladi.
    # Railway'da HTTPS doim bor, shuning uchun u yerda ikkalasi ham o'zi
    # yoqiladi. Cloudflare tunnelida esa yoqilsa havola ishlamay qoladi —
    # o'sha yerda `RAILWAY_PUBLIC_DOMAIN` bo'lmagani uchun o'chiq qoladi.
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=bool(RAILWAY_DOMAIN))
    SECURE_HSTS_SECONDS = env.int(
        'SECURE_HSTS_SECONDS', default=31536000 if RAILWAY_DOMAIN else 0,
    )
    SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(SECURE_HSTS_SECONDS)
    SECURE_HSTS_PRELOAD = bool(SECURE_HSTS_SECONDS)

# --------------------------------------------------------------------------
# Email — support xodimlariga «jonli operator kerak» xabarini yuborish uchun.
# Mahalliy ishlashda (DEBUG=True) xat konsolga chiqadi, SMTP kerak emas.
# --------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=10)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='sevara-design@example.com')

# Xodimlarning profilidagi emaildan tashqari qo'shimcha manzillar.
SUPPORT_NOTIFY_EMAILS = env.list('SUPPORT_NOTIFY_EMAILS', default=[])
# Emaildagi havola to'liq bo'lishi uchun (bo'sh bo'lsa nisbiy manzil yoziladi).
SITE_BASE_URL = env('SITE_BASE_URL', default='')

# --------------------------------------------------------------------------
# Suhbat yordamchisi — Google Gemini (bepul tarif).
# Kalit bo'lmasa AI o'chadi va mijoz to'g'ridan-to'g'ri operatorga ulanadi.
# --------------------------------------------------------------------------
AI_SUPPORT = env.bool('AI_SUPPORT', default=True)
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_MODEL = env('GEMINI_MODEL', default='gemini-3.5-flash-lite')
AI_SUPPORT_TIMEOUT = env.float('AI_SUPPORT_TIMEOUT', default=12.0)
AI_SUPPORT_MAX_TOKENS = env.int('AI_SUPPORT_MAX_TOKENS', default=400)

# --------------------------------------------------------------------------
# Loglar. Django'ning odatiy sozlamasi DEBUG=False bo'lganda xatolarni faqat
# adminlarga EMAIL qiladi — SMTP sozlanmagan bo'lsa xato hech qayerga
# yozilmaydi va serverda nima bo'lganini bilib bo'lmaydi. Shuning uchun
# hammasini konsolga chiqaramiz: Railway loglarida ko'rinadi.
# --------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'oddiy': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'oddiy'},
    },
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
    },
}

# Savat sessiyadagi kaliti
CART_SESSION_KEY = 'cart'

# Kontent saqlanganda `_ru` maydonlarini o'zbekchasidan avtomatik tarjima qilish.
# Tarmoq bo'lmasa maydonlar o'zgarishsiz qoladi (`parda_shop.mt`).
AUTO_TRANSLATE = env.bool('AUTO_TRANSLATE', default=True)
AUTO_TRANSLATE_TIMEOUT = env.float('AUTO_TRANSLATE_TIMEOUT', default=4.0)
