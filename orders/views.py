from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.views.decorators.http import require_POST

from catalog.models import Product
from parda_shop.translations import translate

from .cart import Cart
from .forms import LeadForm, OrderForm
from .models import Order


def _t(key):
    return translate(key, get_language())


def _safe_next(request, fallback):
    """`next` faqat shu saytning ichki manzili bo'lsa qaytariladi.

    Aks holda tashqi saytga yo'naltirib yuborish (open redirect) mumkin edi:
    kimdir `next=https://firibgar.example` bilan havola tarqatsa, foydalanuvchi
    bizning saytimizdan begona saytga tushib qolardi.
    """
    url = request.POST.get('next')
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return fallback


# --------------------------------------------------------------------------
# Savat
# --------------------------------------------------------------------------
def cart_detail(request):
    return render(request, 'orders/cart.html', {'cart': Cart(request)})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    Cart(request).add(product, quantity=max(quantity, 1))
    messages.success(request, _t('product.added'))
    return redirect(_safe_next(request, reverse('orders:cart_detail')))


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    Cart(request).add(product, quantity=quantity, override=True)
    messages.success(request, _t('cart.updated'))
    return redirect('orders:cart_detail')


@require_POST
def cart_remove(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Cart(request).remove(product)
    messages.success(request, _t('cart.removed'))
    return redirect('orders:cart_detail')


# --------------------------------------------------------------------------
# Buyurtma
# --------------------------------------------------------------------------
def checkout(request):
    cart = Cart(request)
    if cart.is_empty:
        messages.info(request, _t('cart.empty'))
        return redirect('catalog:list')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                order.save()
                for row in cart:
                    product = row['product']
                    order.items.create(product=product, quantity=row['quantity'], price=row['price'])
                    product.stock = max(product.stock - row['quantity'], 0)
                    product.save(update_fields=['stock'])
                order.recalculate_total()
            cart.clear()
            return redirect('orders:success', order.pk)
    else:
        form = OrderForm()

    return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})


def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'orders/success.html', {'order': order})


# --------------------------------------------------------------------------
# Ariza (lead)
# --------------------------------------------------------------------------
@require_POST
def lead_create(request):
    form = LeadForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, _t('lead.success'))
    else:
        messages.error(request, _t('lead.error'))
    return redirect(_safe_next(request, '/'))
