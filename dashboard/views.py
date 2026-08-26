from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language

from accounts.forms import StaffUserForm
from accounts.permissions import has_role, role_required
from catalog.models import Product
from orders.models import Lead, Order
from pages.models import SiteSettings
from parda_shop.translations import translate

from .forms import LeadStatusForm, OrderStatusForm, dashboard_form
from .registry import get_form_class, get_section

User = get_user_model()
PAGE_SIZE = 20

MANAGER_ROLES = ('manager', 'admin')


def _t(key):
    return translate(key, get_language())


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))


def _require_section(key, user):
    section = get_section(key)
    if section is None:
        raise Http404('Bo‘lim topilmadi')
    if section['admin_only'] and not has_role(user, 'admin'):
        raise PermissionDenied(_t('dash.no_access'))
    return section


# --------------------------------------------------------------------------
# Umumiy ko'rinish
# --------------------------------------------------------------------------
@role_required(*MANAGER_ROLES)
def overview(request):
    status_counts = {row['status']: row['count'] for row in Order.objects.values('status').annotate(count=Count('id'))}
    return render(request, 'dashboard/overview.html', {
        'orders_total': Order.objects.count(),
        'orders_new': status_counts.get('new', 0),
        'orders_confirmed': status_counts.get('confirmed', 0),
        'orders_done': status_counts.get('done', 0),
        'revenue': Order.objects.filter(status='done').aggregate(total=Sum('total_amount'))['total'] or 0,
        'leads_new': Lead.objects.filter(status='new').count(),
        'products_total': Product.objects.count(),
        'low_stock': Product.objects.filter(is_active=True, stock__lte=3).order_by('stock')[:8],
        'recent_orders': Order.objects.all()[:8],
        'recent_leads': Lead.objects.all()[:8],
    })


# --------------------------------------------------------------------------
# Generic CRUD bo'limlari (registry asosida)
# --------------------------------------------------------------------------
@role_required(*MANAGER_ROLES)
def section_list(request, key):
    section = _require_section(key, request.user)
    queryset = section['model'].objects.all()
    if section.get('select_related'):
        queryset = queryset.select_related(*section['select_related'])

    query = request.GET.get('q', '').strip()
    if query and section['search_fields']:
        condition = Q()
        for field in section['search_fields']:
            condition |= Q(**{f'{field}__icontains': query})
        queryset = queryset.filter(condition)

    return render(request, 'dashboard/section_list.html', {
        'section': section,
        'section_key': key,
        'page_obj': _paginate(request, queryset),
        'query': query,
        'total': queryset.count(),
    })


@role_required(*MANAGER_ROLES)
def section_form(request, key, pk=None):
    section = _require_section(key, request.user)
    instance = get_object_or_404(section['model'], pk=pk) if pk else None
    form_class = get_form_class(key)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:section_list', key=key)
    else:
        form = form_class(instance=instance)

    return render(request, 'dashboard/section_form.html', {
        'section': section,
        'section_key': key,
        'form': form,
        'object': instance,
    })


@role_required(*MANAGER_ROLES)
def section_delete(request, key, pk):
    section = _require_section(key, request.user)
    if not has_role(request.user, 'admin'):
        raise PermissionDenied(_t('dash.no_access'))
    instance = get_object_or_404(section['model'], pk=pk)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, _t('dash.deleted'))
        return redirect('dashboard:section_list', key=key)
    return render(request, 'dashboard/confirm_delete.html', {
        'section': section,
        'section_key': key,
        'object': instance,
        'cancel_url': reverse('dashboard:section_list', args=[key]),
    })


# --------------------------------------------------------------------------
# Buyurtmalar
# --------------------------------------------------------------------------
@role_required(*MANAGER_ROLES)
def order_list(request):
    orders = Order.objects.all().prefetch_related('items')
    status = request.GET.get('status', '').strip()
    if status:
        orders = orders.filter(status=status)
    query = request.GET.get('q', '').strip()
    if query:
        orders = orders.filter(Q(full_name__icontains=query) | Q(phone__icontains=query))
    return render(request, 'dashboard/order_list.html', {
        'page_obj': _paginate(request, orders),
        'status': status,
        'query': query,
        'statuses': Order.STATUS,
        'total': orders.count(),
    })


@role_required(*MANAGER_ROLES)
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=pk)
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:order_detail', pk=order.pk)
    else:
        form = OrderStatusForm(instance=order)
    return render(request, 'dashboard/order_detail.html', {'order': order, 'form': form})


# --------------------------------------------------------------------------
# So'rovlar (leads)
# --------------------------------------------------------------------------
@role_required(*MANAGER_ROLES)
def lead_list(request):
    leads = Lead.objects.select_related('handled_by')
    status = request.GET.get('status', '').strip()
    if status:
        leads = leads.filter(status=status)
    lead_type = request.GET.get('type', '').strip()
    if lead_type:
        leads = leads.filter(lead_type=lead_type)
    return render(request, 'dashboard/lead_list.html', {
        'page_obj': _paginate(request, leads),
        'status': status,
        'lead_type': lead_type,
        'statuses': Lead.STATUS,
        'types': Lead.TYPES,
        'total': leads.count(),
    })


@role_required(*MANAGER_ROLES)
def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        form = LeadStatusForm(request.POST, instance=lead)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status != 'new' and updated.handled_by is None:
                updated.handled_by = request.user
            updated.save()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:lead_list')
    else:
        form = LeadStatusForm(instance=lead)
    return render(request, 'dashboard/lead_detail.html', {'lead': lead, 'form': form})


# --------------------------------------------------------------------------
# Foydalanuvchilar va sozlamalar (faqat admin)
# --------------------------------------------------------------------------
@role_required('admin')
def user_list(request):
    users = User.objects.filter(Q(is_staff=True) | Q(profile__isnull=False))
    users = users.select_related('profile').distinct().order_by('-date_joined')
    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))
    return render(request, 'dashboard/user_list.html', {
        'page_obj': _paginate(request, users),
        'query': query,
        'total': users.count(),
    })


@role_required('admin')
def user_form(request, pk=None):
    account = get_object_or_404(User, pk=pk) if pk else None
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:user_list')
    else:
        form = StaffUserForm(instance=account)
    return render(request, 'dashboard/user_form.html', {'account': account, 'form': form})


@role_required('admin')
def user_delete(request, pk):
    account = get_object_or_404(User, pk=pk)
    if account == request.user or account.is_superuser:
        raise PermissionDenied('O‘zingizni yoki superuser hisobini o‘chirib bo‘lmaydi.')
    if request.method == 'POST':
        account.delete()
        messages.success(request, _t('dash.deleted'))
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': account,
        'cancel_url': reverse('dashboard:user_list'),
    })


@role_required('admin')
def site_settings(request):
    instance = SiteSettings.load()
    form_class = dashboard_form(SiteSettings)
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:settings')
    else:
        form = form_class(instance=instance)
    return render(request, 'dashboard/settings.html', {'form': form})
