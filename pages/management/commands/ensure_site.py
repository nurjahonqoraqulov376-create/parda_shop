"""`django.contrib.sites` yozuvidagi domenni haqiqiysiga moslaydi.

Nima uchun kerak
----------------
`sitemap.xml` manzillarni Site jadvalidan quradi. Django o'rnatilganda u
yerga `example.com` yoziladi va hech kim tegmasa shunday qolib ketadi —
natijada sayt xaritasi butunlay yaroqsiz bo'ladi:

    <loc>https://example.com/uz/</loc>

Bu buyruq domenni muhit o'zgaruvchisidan oladi va yozuvni yangilaydi.
Domen almashsa (o'z domeningizga o'tsangiz) keyingi joylashtirishda
o'zi to'g'rilanadi.

Domen topilmasa HECH NARSA QILMAYDI va xato bermaydi — shuning uchun
uni pre-deploy'da doim qoldirish xavfsiz.
"""

import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


def target_domain():
    """Saytning haqiqiy domeni: avval qo'lda kiritilgani, keyin Railway'niki."""
    for name in ('SITE_DOMAIN', 'RAILWAY_PUBLIC_DOMAIN'):
        value = (os.environ.get(name) or '').strip()
        if value:
            return value.replace('https://', '').replace('http://', '').rstrip('/')
    return ''


class Command(BaseCommand):
    help = 'Site yozuvidagi domenni SITE_DOMAIN / RAILWAY_PUBLIC_DOMAIN dan yangilaydi.'

    def handle(self, *args, **options):
        domain = target_domain()
        if not domain:
            self.stdout.write('ensure_site: domen berilmagan — o‘tkazib yuborildi.')
            return

        site, created = Site.objects.get_or_create(
            pk=getattr(settings, 'SITE_ID', 1),
            defaults={'domain': domain, 'name': 'Sevara Design'},
        )
        if not created and site.domain != domain:
            site.domain = domain
            site.save(update_fields=['domain'])
        self.stdout.write(self.style.SUCCESS('ensure_site: %s' % site.domain))
