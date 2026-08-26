from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ('phone', 'role')


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'get_role', 'is_staff', 'is_superuser')
    list_filter = BaseUserAdmin.list_filter + ('profile__role',)

    @admin.display(description='Rol', ordering='profile__role')
    def get_role(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.get_role_display() if profile else '—'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'role')
    list_filter = ('role',)
    list_editable = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')
