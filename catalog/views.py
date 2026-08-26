from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product

PAGE_SIZE = 24

SORT_OPTIONS = {
    'new': '-created_at',
    'price_asc': 'price',
    'price_desc': '-price',
    'name': 'name',
}


def filtered_products(request, base_qs=None):
    """GET parametrlari asosida mahsulotlarni filtrlaydi va saralaydi."""
    products = base_qs if base_qs is not None else Product.objects.filter(is_active=True)
    products = products.select_related('category')

    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(name_ru__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
        )

    price_from = request.GET.get('price_from', '').strip()
    if price_from.isdigit():
        products = products.filter(price__gte=int(price_from))
    price_to = request.GET.get('price_to', '').strip()
    if price_to.isdigit():
        products = products.filter(price__lte=int(price_to))

    sort = request.GET.get('sort', 'new')
    products = products.order_by(SORT_OPTIONS.get(sort, '-created_at'))
    return products, query, sort


def paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))


def catalog_list(request):
    category_slug = request.GET.get('category', '').strip()
    base = Product.objects.filter(is_active=True)
    if category_slug:
        base = base.filter(category__slug=category_slug)
    products, query, sort = filtered_products(request, base)
    return render(request, 'catalog/list.html', {
        'page_obj': paginate(request, products),
        'total': products.count(),
        'categories': Category.objects.filter(is_active=True),
        'selected_category': category_slug,
        'query': query,
        'sort': sort,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    base = Product.objects.filter(is_active=True, category=category)
    products, query, sort = filtered_products(request, base)
    return render(request, 'catalog/category.html', {
        'category': category,
        'page_obj': paginate(request, products),
        'total': products.count(),
        'categories': Category.objects.filter(is_active=True),
        'selected_category': category.slug,
        'query': query,
        'sort': sort,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        slug=slug, is_active=True,
    )
    related = Product.objects.filter(is_active=True, category=product.category).exclude(pk=product.pk)[:4]
    return render(request, 'catalog/detail.html', {'product': product, 'related': related})


def search(request):
    products, query, sort = filtered_products(request)
    return render(request, 'catalog/search.html', {
        'page_obj': paginate(request, products),
        'total': products.count(),
        'query': query,
        'sort': sort,
    })
