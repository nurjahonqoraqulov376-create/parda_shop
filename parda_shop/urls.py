from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('boshqaruv/', include('dashboard.urls')),
    path('', include('catalog.urls')),
    path('', include('orders.urls')),
    path('', include('support.urls')),
    path('', include('pages.urls')),
    prefix_default_language=True,
)

# Yuklangan rasmlar (media). `django.conf.urls.static.static()` DEBUG=False
# bo'lganda hech narsa qaytarmaydi, shuning uchun to'g'ridan-to'g'ri `serve`
# ishlatamiz — probniy havolani DEBUG'siz ochganda ham rasmlar ko'rinsin.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
