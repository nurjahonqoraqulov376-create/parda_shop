from django.contrib import admin

from .models import Lead, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'user__username')
    inlines = [OrderItemInline]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'lead_type', 'status', 'handled_by', 'created_at')
    list_filter = ('lead_type', 'status', 'created_at')
    search_fields = ('name', 'phone', 'message')
