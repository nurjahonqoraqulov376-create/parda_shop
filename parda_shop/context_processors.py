from accounts.permissions import has_role
from catalog.models import Category
from orders.cart import Cart
from orders.forms import LeadForm
from pages.models import SiteSettings


def site_context(request):
    """Header, footer va modal formalar uchun umumiy kontekst."""
    cart = Cart(request)
    return {
        'site': SiteSettings.load(),
        'menu_categories': Category.objects.filter(is_active=True),
        'cart': cart,
        'cart_count': len(cart),
        'cart_total': cart.total,
        'callback_form': LeadForm(initial={'lead_type': 'callback'}),
        'can_manage': has_role(request.user, 'manager', 'admin'),
        'is_site_admin': has_role(request.user, 'admin'),
    }
