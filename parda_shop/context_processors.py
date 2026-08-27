from accounts.permissions import has_role
from catalog.models import Category
from orders.cart import Cart
from orders.forms import LeadForm
from pages.models import SiteSettings


def site_context(request):
    """Header, footer va modal formalar uchun umumiy kontekst."""
    cart = Cart(request)
    can_manage = has_role(request.user, 'manager', 'admin')
    can_chat = can_manage or has_role(request.user, 'support')
    return {
        'site': SiteSettings.load(),
        'menu_categories': Category.objects.filter(is_active=True),
        'cart': cart,
        'cart_count': len(cart),
        'cart_total': cart.total,
        'callback_form': LeadForm(initial={'lead_type': 'callback'}),
        'can_manage': can_manage,
        'can_chat': can_chat,
        'is_support': has_role(request.user, 'support'),
        'is_site_admin': has_role(request.user, 'admin'),
        # Panel belgisidagi hisoblagich — faqat xodimlar uchun so'rov ketadi.
        'waiting_chats': _waiting_chats() if can_chat else 0,
    }


def _waiting_chats():
    from support.models import Conversation
    return Conversation.objects.filter(status=Conversation.STATUS_WAITING).count()
