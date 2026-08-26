from decimal import Decimal

from django.conf import settings

from catalog.models import Product


class Cart:
    """Sessiyada saqlanadigan savat.

    Ma'lumot ko'rinishi: {'<product_id>': {'quantity': 2, 'price': '129000'}}
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_KEY)
        if cart is None:
            cart = self.session[settings.CART_SESSION_KEY] = {}
        self.cart = cart

    # --- o'zgartirish ---
    def add(self, product, quantity=1, override=False):
        key = str(product.pk)
        if key not in self.cart:
            self.cart[key] = {'quantity': 0, 'price': str(product.price)}
        if override:
            self.cart[key]['quantity'] = quantity
        else:
            self.cart[key]['quantity'] += quantity
        self.cart[key]['price'] = str(product.price)
        if self.cart[key]['quantity'] < 1:
            self.remove(product)
        else:
            self.save()

    def remove(self, product):
        self.cart.pop(str(product.pk), None)
        self.save()

    def clear(self):
        self.session[settings.CART_SESSION_KEY] = self.cart = {}
        self.save()

    def save(self):
        self.session.modified = True

    # --- o'qish ---
    def __iter__(self):
        products = Product.objects.filter(pk__in=[int(pk) for pk in self.cart])
        for product in products:
            row = self.cart[str(product.pk)]
            price = Decimal(row['price'])
            quantity = row['quantity']
            yield {
                'product': product,
                'quantity': quantity,
                'price': price,
                'total': price * quantity,
            }

    def __len__(self):
        return sum(row['quantity'] for row in self.cart.values())

    @property
    def total(self):
        return sum(Decimal(row['price']) * row['quantity'] for row in self.cart.values())

    @property
    def is_empty(self):
        return not self.cart
