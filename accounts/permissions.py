from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def user_role(user):
    """Foydalanuvchi roli: superuser doim 'admin', profilsizda ruxsat yo'q."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'admin'
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def has_role(user, *roles):
    return user_role(user) in roles


def role_required(*roles):
    """View'ni faqat berilgan rollarga ochadi; boshqalarga 403 qaytaradi."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not has_role(request.user, *roles):
                raise PermissionDenied('Sizda bu bo‘limga ruxsat yo‘q.')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class RoleRequiredMixin:
    """CBV uchun rol tekshiruvi. `allowed_roles` ni belgilang."""

    allowed_roles = ('manager', 'admin')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not has_role(request.user, *self.allowed_roles):
            raise PermissionDenied('Sizda bu bo‘limga ruxsat yo‘q.')
        return super().dispatch(request, *args, **kwargs)


class AdminOnlyMixin(RoleRequiredMixin):
    allowed_roles = ('admin',)
