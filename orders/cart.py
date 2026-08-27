from decimal import Decimal, InvalidOperation

from django.conf import settings

from catalog.models import Product

# Bitta mahsulotdan olinadigan eng ko'p miqdor — forma orqali bema'ni katta
# son yuborilsa savat va buyurtma summasi buzilmasligi uchun.
MAX_QUANTITY = 999


class Cart:
    """Sessiyada saqlanadigan savat.

    Ma'lumot ko'rinishi: {'<product_id>': {'quantity': 2, 'price': '129000'}}

    Sessiyadagi ma'lumot buzilgan bo'lishi mumkin (eski format, qo'lda
    o'zgartirilgan cookie, o'chirilgan mahsulot). Savat har bir sahifada
    ishlagani uchun bunday holat butun saytni ishdan chiqarmasligi kerak —
    shuning uchun kirishda ma'lumot tozalanadi, yaroqsiz qatorlar tashlanadi.
    """

    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(settings.CART_SESSION_KEY)
        cart = self._sanitize(raw)
        if cart != raw:
            self.session[settings.CART_SESSION_KEY] = cart
            self.session.modified = True
        self.cart = cart
        self._rows = None

    # ------------------------------------------------------------------
    # Ichki yordamchilar
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize(raw):
        """Sessiyadagi xom ma'lumotdan faqat yaroqli qatorlarni qoldiradi."""
        clean = {}
        if not isinstance(raw, dict):
            return clean
        for key, row in raw.items():
            if not (isinstance(key, str) and key.isdigit() and isinstance(row, dict)):
                continue
            try:
                quantity = int(row.get('quantity', 0))
                price = Decimal(str(row.get('price', '0')))
            except (TypeError, ValueError, InvalidOperation):
                continue
            if quantity < 1 or price < 0:
                continue
            clean[key] = {'quantity': min(quantity, MAX_QUANTITY), 'price': str(price)}
        return clean

    def _build_rows(self):
        """Savat qatorlari — narx har doim bazadagi joriy narxdan olinadi.

        Sessiyada saqlangan narx eskirgan bo'lishi mumkin (admin narxni
        o'zgartirgan). Ko'rsatiladigan summa bilan buyurtmaga yoziladigan
        summa bir xil bo'lishi uchun ikkalasi ham shu yerdan oladi.
        """
        if not self.cart:
            return []

        products = (
            Product.objects
            .filter(pk__in=[int(key) for key in self.cart], is_active=True)
            .select_related('category')
        )
        found = {str(product.pk): product for product in products}

        # O'chirilgan yoki nofaol qilingan mahsulot savatda osilib qolmasin —
        # aks holda ro'yxatda ko'rinmaydi, lekin summaga qo'shilib turadi.
        stale = [key for key in self.cart if key not in found]
        if stale:
            for key in stale:
                self.cart.pop(key, None)
            self.save()

        rows = []
        for key, product in found.items():
            quantity = self.cart[key]['quantity']
            # Sessiyadagi narxni joriy narx bilan yangilab qo'yamiz.
            self.cart[key]['price'] = str(product.price)
            rows.append({
                'product': product,
                'quantity': quantity,
                'price': product.price,
                'total': product.price * quantity,
            })
        return rows

    @property
    def rows(self):
        if self._rows is None:
            self._rows = self._build_rows()
        return self._rows

    def _invalidate(self):
        self._rows = None

    # ------------------------------------------------------------------
    # O'zgartirish
    # ------------------------------------------------------------------
    def add(self, product, quantity=1, override=False):
        key = str(product.pk)
        current = self.cart.get(key, {'quantity': 0, 'price': str(product.price)})
        new_quantity = quantity if override else current['quantity'] + quantity
        new_quantity = min(new_quantity, MAX_QUANTITY)

        if new_quantity < 1:
            self.remove(product)
            return 0

        self.cart[key] = {'quantity': new_quantity, 'price': str(product.price)}
        self.save()
        return new_quantity

    def remove(self, product):
        self.cart.pop(str(product.pk), None)
        self.save()

    def clear(self):
        self.session[settings.CART_SESSION_KEY] = self.cart = {}
        self.save()

    def save(self):
        self.session[settings.CART_SESSION_KEY] = self.cart
        self.session.modified = True
        self._invalidate()

    # ------------------------------------------------------------------
    # O'qish
    # ------------------------------------------------------------------
    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return sum(row['quantity'] for row in self.rows)

    @property
    def total(self):
        return sum((row['total'] for row in self.rows), Decimal('0'))

    @property
    def is_empty(self):
        return not self.rows
