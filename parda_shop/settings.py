from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'uz'
LANGUAGES = [('uz', "O'zbekcha"), ('ru', 'Русский')]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
# DEBUG=False bo'lganda ham media fayllarni Django o'zi bersinmi (probniy
# havola uchun qulay; haqiqiy prod'da bu ishni nginx bajarishi kerak).
SERVE_MEDIA = env.bool('SERVE_MEDIA', default=False)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# `django.contrib.sites` eski allauth jadvallari uchun saqlanmoqda.
SITE_ID = 1

# Kirish faqat xodimlar uchun — boshqaruv paneli ichidagi login sahifasi.
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
LOGIN_URL = reverse_lazy('dashboard:login')
LOGIN_REDIRECT_URL = reverse_lazy('dashboard:overview')
LOGOUT_REDIRECT_URL = '/'

# CSRF middleware uchun ishonchli manbalar (prod'da haqiqiy domeni qo'shish)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://127.0.0.1:8931', 'http://localhost:8931'])

# Tunnel/reverse-proxy orqasida ishlaganda (masalan cloudflared bilan probniy
# havola) so'rov Django'ga http bo'lib yetadi, lekin tashqarida u https.
# Faqat ishonchli proksi oldida turganda yoqing — aks holda header'ni
# soxtalashtirish mumkin.
if env.bool('BEHIND_PROXY', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# Savat sessiyadagi kaliti
CART_SESSION_KEY = 'cart'

# Kontent saqlanganda `_ru` maydonlarini o'zbekchasidan avtomatik tarjima qilish.
# Tarmoq bo'lmasa maydonlar o'zgarishsiz qoladi (`parda_shop.mt`).
AUTO_TRANSLATE = env.bool('AUTO_TRANSLATE', default=True)
AUTO_TRANSLATE_TIMEOUT = env.float('AUTO_TRANSLATE_TIMEOUT', default=4.0)
