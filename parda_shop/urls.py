from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from pages.sitemaps import SITEMAPS

def robots_txt(request):
    """`robots.txt` — sitemap manzili joriy domendan olinadi.

    Domen almashsa (masalan o'z domeningizga o'tsangiz) fayl o'zi
    to'g'ri manzilni ko'rsatadi, qo'lda tahrirlash kerak emas.
    """
    return TemplateView.as_view(
        template_name='robots.txt', content_type='text/plain',
        extra_context={'scheme': request.scheme, 'host': request.get_host()},
    )(request)


# Bu manzillar TIL PREFIKSISIZ bo'lishi shart: qidiruv tizimlari ularni
# aynan saytning ildizidan qidiradi (`/robots.txt`, `/sitemap.xml`).
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('robots.txt', robots_txt, name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS},
         name='django.contrib.sitemaps.views.sitemap'),
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
