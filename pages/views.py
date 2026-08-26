from datetime import date

from django.shortcuts import get_object_or_404, render

from catalog.models import Category, Product
from orders.forms import LeadForm
from parda_shop.regions import DISTRICTS

from .models import Advantage, Banner, Client, ContentBlock, Testimonial, Work

HOME_SECTION_LIMIT = 8
HOME_WORK_LIMIT = 6
FOUNDED_YEAR = 2016


def _home_sections():
    """Bosh sahifada ko'rsatiladigan kategoriya bo'limlari."""
    sections = []
    for category in Category.objects.filter(is_active=True, show_on_home=True):
        products = list(category.products.filter(is_active=True)[:HOME_SECTION_LIMIT])
        if products:
            sections.append({'category': category, 'products': products})
    return sections


def home(request):
    sections = _home_sections()
    featured = Product.objects.filter(is_active=True, is_featured=True)[:HOME_SECTION_LIMIT]
    newest = Product.objects.filter(is_active=True).order_by('-created_at')[:HOME_SECTION_LIMIT]
    return render(request, 'pages/home.html', {
        'banners': Banner.objects.filter(is_active=True),
        'home_categories': Category.objects.filter(is_active=True)[:12],
        'sections': sections,
        'featured': featured,
        'newest': newest,
        'advantages': Advantage.objects.filter(is_active=True),
        'testimonials': Testimonial.objects.filter(is_active=True)[:6],
        'clients': Client.objects.filter(is_active=True)[:12],
        'works': Work.objects.filter(is_active=True)[:HOME_WORK_LIMIT],
        'content_blocks': ContentBlock.objects.filter(is_active=True, show_on_home=True),
        'lead_form': LeadForm(),
        'stats': {
            'years': date.today().year - FOUNDED_YEAR,
            'products': Product.objects.filter(is_active=True).count(),
            'categories': Category.objects.filter(is_active=True).count(),
            'districts': len(DISTRICTS),
        },
    })


def about(request):
    return render(request, 'pages/about.html', {
        'advantages': Advantage.objects.filter(is_active=True),
    })


def work_list(request):
    """Portfolio — tayyorlangan pardalar ro'yxati."""
    return render(request, 'pages/works.html', {'works': Work.objects.filter(is_active=True)})


def work_detail(request, slug):
    work = get_object_or_404(Work, slug=slug, is_active=True)
    return render(request, 'pages/work_detail.html', {
        'work': work,
        'other_works': Work.objects.filter(is_active=True).exclude(pk=work.pk)[:3],
    })


def contact(request):
    return render(request, 'pages/contact.html', {'lead_form': LeadForm()})
