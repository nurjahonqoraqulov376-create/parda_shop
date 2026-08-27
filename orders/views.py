from django.contrib import messages
from django.db import connection, transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.views.decorators.http import require_POST

from accounts.permissions import has_role
from catalog.models import Product
from parda_shop.translations import translate

from .cart import MAX_QUANTITY, Cart
from .forms import LeadForm, OrderForm
from .models import Order

# Shu brauzerda rasmiylashtirilgan buyurtmalar ro'yxati (sessiyada).
COMPLETED_ORDERS_SESSION_KEY = 'completed_orders'


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


def _posted_quantity(request, default=1):
    """POST'dagi miqdorni xavfsiz songa aylantiradi."""
    try:
        quantity = int(request.POST.get('quantity', default))
    except (TypeError, ValueError):
        return default
    return max(-MAX_QUANTITY, min(quantity, MAX_QUANTITY))


def _stock_warning(product):
    return _t('cart.stock_limited') % {'stock': product.stock}


# --------------------------------------------------------------------------
# Savat
# --------------------------------------------------------------------------
def cart_detail(request):
    return render(request, 'orders/cart.html', {'cart': Cart(request)})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not product.in_stock:
        messages.error(request, _t('product.out_of_stock'))
        return redirect(_safe_next(request, reverse('orders:cart_detail')))

    cart = Cart(request)
    added = cart.add(product, quantity=max(_posted_quantity(request), 1))
    if added > product.stock:
        # Ombordagidan ko'p so'raldi — bor miqdorgacha kamaytiramiz.
        cart.add(product, quantity=product.stock, override=True)
        messages.warning(request, _stock_warning(product))
    else:
        messages.success(request, _t('product.added'))
    return redirect(_safe_next(request, reverse('orders:cart_detail')))


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)
    quantity = _posted_quantity(request)
    if quantity > 0 and product.is_active and quantity > product.stock:
        cart.add(product, quantity=product.stock, override=True)
        messages.warning(request, _stock_warning(product))
    else:
        cart.add(product, quantity=quantity, override=True)
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
def _reserve_stock(rows):
    """Ombordagi sonni tekshirib, buyurtma uchun ayiradi.

    Muvaffaqiyatsiz bo'lsa xato matnlari ro'yxati qaytadi va ombor
    o'zgarmaydi. Tranzaksiya ichida chaqirilishi shart.
    """
    ids = [row['product'].pk for row in rows]
    products = Product.objects.filter(pk__in=ids)
    # SQLite `SELECT ... FOR UPDATE` ni qo'llamaydi, shuning uchun faqat
    # qo'llaydigan bazalarda (PostgreSQL/MySQL) qulflaymiz.
    if connection.features.has_select_for_update:
        products = products.select_for_update()
    locked = {product.pk: product for product in products}

    problems = []
    for row in rows:
        product = locked.get(row['product'].pk)
        if product is None or not product.is_active:
            problems.append('%s — %s' % (row['product'].name, _t('product.out_of_stock')))
        elif product.stock < row['quantity']:
            problems.append('%s — %s' % (product.name, _stock_warning(product)))
    if problems:
        return problems

    # `F()` bilan ayiramiz: ikkita buyurtma bir vaqtda kelsa ham hisob
    # bazaning o'zida bajariladi va bir-birini o'chirib yubormaydi.
    for row in rows:
        Product.objects.filter(pk=row['product'].pk).update(stock=F('stock') - row['quantity'])
    return []


def checkout(request):
    cart = Cart(request)
    if cart.is_empty:
        messages.info(request, _t('cart.empty'))
        return redirect('catalog:list')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            rows = list(cart)
            with transaction.atomic():
                problems = _reserve_stock(rows)
                if problems:
                    for problem in problems:
                        messages.error(request, problem)
                    return redirect('orders:cart_detail')

                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                order.save()
                for row in rows:
                    order.items.create(
                        product=row['product'], quantity=row['quantity'], price=row['price'],
                    )
                order.recalculate_total()

            cart.clear()
            # «Rahmat» sahifasini faqat shu brauzer ocha olsin.
            completed = request.session.get(COMPLETED_ORDERS_SESSION_KEY, [])
            request.session[COMPLETED_ORDERS_SESSION_KEY] = [*completed, order.pk][-20:]
            request.session.modified = True
            return redirect('orders:success', order.pk)
    else:
        form = OrderForm()

    return render(request, 'orders/checkout.html', {'form': form, 'cart': cart})


def order_success(request, pk):
    """Buyurtma tafsilotlari — faqat egasiga ko'rinadi.

    Ilgari bu sahifa har kimga ochiq edi: manzildagi raqamni almashtirib,
    begona odamning ismi, telefoni va manzilini o'qish mumkin edi.
    """
    order = get_object_or_404(Order, pk=pk)
    allowed = (
        order.pk in request.session.get(COMPLETED_ORDERS_SESSION_KEY, [])
        or (request.user.is_authenticated and order.user_id == request.user.pk)
        or has_role(request.user, 'manager', 'admin')
    )
    if not allowed:
        raise Http404
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
