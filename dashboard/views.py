from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Sum, When
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language

from accounts.forms import MyProfileForm, StaffUserForm
from accounts.permissions import has_role, role_required
from catalog.models import Product
from orders.models import Lead, Order
from pages.models import SiteSettings
from parda_shop.translations import translate
from support.models import Conversation, Message

from . import agent as agent_ai
from .fieldgroups import group_fields
from . import agent_run
from . import agent_uploads
from .forms import LeadStatusForm, OrderStatusForm, dashboard_form
from .models import AgentAction
from .registry import get_form_class, get_section

User = get_user_model()
PAGE_SIZE = 20

MANAGER_ROLES = ('manager', 'admin')
# Support xodimi faqat suhbatlarga kiradi.
CHAT_ROLES = ('support', 'manager', 'admin')


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

    # «Kim qo'shgan» faqat shu maydoni bor modellarda ko'rsatiladi.
    has_author = any(f.name == 'created_by' for f in section['model']._meta.get_fields())
    mine_only = has_author and request.GET.get('mine') == '1'
    if mine_only:
        queryset = queryset.filter(created_by=request.user)
    if has_author:
        queryset = queryset.select_related('created_by')

    return render(request, 'dashboard/section_list.html', {
        'section': section,
        'section_key': key,
        'page_obj': _paginate(request, queryset),
        'query': query,
        'total': queryset.count(),
        'has_author': has_author,
        'mine_only': mine_only,
    })


@role_required(*MANAGER_ROLES)
def section_form(request, key, pk=None):
    section = _require_section(key, request.user)
    instance = get_object_or_404(section['model'], pk=pk) if pk else None
    form_class = get_form_class(key)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            # Kim qo'shganini eslab qolamiz: ro'yxatda ko'rinadi va
            # xodim o'z yozuvlarini ajratib ola oladi.
            if instance is None and hasattr(obj, 'created_by_id'):
                obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, _t('dash.saved'))
            return redirect('dashboard:section_list', key=key)
    else:
        form = form_class(instance=instance)

    return render(request, 'dashboard/section_form.html', {
        'section': section,
        'section_key': key,
        'form': form,
        'field_groups': group_fields(form),
        'object': instance,
        'can_delete': has_role(request.user, 'admin'),
    })


@role_required(*MANAGER_ROLES)
def section_delete(request, key, pk):
    section = _require_section(key, request.user)
    if not has_role(request.user, 'admin'):
        raise PermissionDenied(_t('dash.no_access'))
    instance = get_object_or_404(section['model'], pk=pk)
    if request.method == 'POST':
        try:
            instance.delete()
        except ProtectedError:
            # Masalan, buyurtmada ishlatilgan mahsulot: `OrderItem` PROTECT
            # bo'lgani uchun o'chirib bo'lmaydi. Ilgari bu 500 xato berardi.
            messages.error(request, _t('dash.delete_protected'))
            return redirect('dashboard:section_list', key=key)
        messages.success(request, _t('dash.deleted'))
        return redirect('dashboard:section_list', key=key)
    return render(request, 'dashboard/confirm_delete.html', {
        'section': section,
        'section_key': key,
        'object': instance,
        'cancel_url': reverse('dashboard:section_list', args=[key]),
    })


# --------------------------------------------------------------------------
# Suhbatlar (support)
# --------------------------------------------------------------------------
@role_required(*CHAT_ROLES)
def after_login(request):
    """Kirgandan keyin rolga mos sahifaga yo'naltiradi.

    Support xodimi umumiy ko'rinishga kira olmaydi, shuning uchun uni
    to'g'ridan-to'g'ri suhbatlarga tushiramiz.
    """
    if has_role(request.user, 'support'):
        return redirect('dashboard:chat_list')
    return redirect('dashboard:overview')


@role_required(*CHAT_ROLES)
def chat_list(request):
    conversations = Conversation.objects.select_related('operator')
    status = request.GET.get('status', '').strip()
    if status:
        conversations = conversations.filter(status=status)
    # Operator kutayotganlar doim tepada.
    conversations = conversations.order_by(
        Case(When(status=Conversation.STATUS_WAITING, then=0), default=1, output_field=IntegerField()),
        '-last_message_at',
    )
    return render(request, 'dashboard/chat_list.html', {
        'page_obj': _paginate(request, conversations),
        'status': status,
        'statuses': Conversation.STATUS,
        'total': conversations.count(),
    })


@role_required(*CHAT_ROLES)
def chat_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)

    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if text:
            Message.objects.create(
                conversation=conversation, sender=Message.SENDER_OPERATOR,
                text=text, author=request.user, seen_by_operator=True,
            )
            # Operator javob yozdi — endi AI aralashmaydi.
            conversation.status = Conversation.STATUS_WITH_OPERATOR
            conversation.operator = request.user
            conversation.save(update_fields=['status', 'operator'])
            conversation.touch()
        return redirect('dashboard:chat_detail', pk=conversation.pk)

    # Ochilgan zahoti mijoz xabarlari o'qilgan deb belgilanadi.
    conversation.messages.filter(
        sender=Message.SENDER_VISITOR, seen_by_operator=False,
    ).update(seen_by_operator=True)

    return render(request, 'dashboard/chat_detail.html', {
        'conversation': conversation,
        'messages_list': conversation.messages.select_related('author'),
    })


@role_required(*CHAT_ROLES)
def chat_close(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if request.method == 'POST':
        conversation.status = Conversation.STATUS_CLOSED
        conversation.save(update_fields=['status'])
        messages.success(request, _t('dash.saved'))
    return redirect('dashboard:chat_list')


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


# --------------------------------------------------------------------------
# AI yordamchi (agent)
# --------------------------------------------------------------------------
# Agent xodim nomidan baza yozadi, shuning uchun uch qatlamli to'siq bor:
#   1) rol tekshiruvi (bu yerda),
#   2) amallarning oq ro'yxati (`agent.ACTIONS`),
#   3) tasdiqlash — hech narsa avtomatik yozilmaydi.
AGENT_HISTORY_KEY = 'agent_history'
# Nosozlik sababi -> xodimga ko'rsatiladigan matn kaliti.
AGENT_REASON_TEXT = {
    agent_ai.REASON_BUSY: 'dash.agent_busy',
    agent_ai.REASON_TIMEOUT: 'dash.agent_timeout',
    agent_ai.REASON_TOO_LONG: 'dash.agent_too_big',
    agent_ai.REASON_OFFLINE: 'dash.agent_offline',
}
AGENT_PENDING_KEY = 'agent_pending'
# Taklif tasdiqlangunicha rasm vaqtinchalik joyda turadi.
AGENT_IMAGE_KEY = 'agent_pending_image'
AGENT_HISTORY_LIMIT = 20


def _image_format(name):
    """Fayl kengaytmasidan Gemini uchun format nomi."""
    suffix = (name or '').rsplit('.', 1)[-1].lower()
    return {'png': 'PNG', 'webp': 'WEBP'}.get(suffix, 'JPEG')


@role_required(*MANAGER_ROLES)
def agent_page(request):
    pending = request.session.get(AGENT_PENDING_KEY)
    return render(request, 'dashboard/agent.html', {
        'alerts': agent_ai.alerts(),
        'snapshot': agent_ai.site_snapshot(),
        'agent_enabled': agent_ai.is_enabled(),
        'history': request.session.get(AGENT_HISTORY_KEY, []),
        'pending': pending,
        'pending_summary': agent_run.describe(pending) if pending else '',
        'pending_image_url': agent_uploads.public_url(
            request.session.get(AGENT_IMAGE_KEY)),
        'recent_actions': AgentAction.objects.select_related('user')[:15],
    })


@role_required(*MANAGER_ROLES)
def agent_send(request):
    """Savol yuboriladi; javob va (bo'lsa) amal taklifi qaytadi."""
    if request.method != 'POST':
        return JsonResponse({'error': 'faqat POST'}, status=405)

    question = (request.POST.get('text') or '').strip()
    if len(question) > 2000:
        return JsonResponse({'error': _t('dash.agent_too_long')}, status=400)

    # Rasm ixtiyoriy: yordamchi uni ko'rib tavsif yozadi va tasdiqlangach
    # yozuvga biriktiriladi.
    image = None
    upload = request.FILES.get('image')
    if upload is not None:
        try:
            stored_name, data = agent_uploads.stash(upload)
        except agent_uploads.UploadError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        # Eski taklifning rasmi qolib ketmasin.
        agent_uploads.discard(request.session.get(AGENT_IMAGE_KEY))
        request.session[AGENT_IMAGE_KEY] = stored_name
        image = (data, _image_format(stored_name))
    elif not question:
        return JsonResponse({'error': _t('dash.agent_empty')}, status=400)

    history = request.session.get(AGENT_HISTORY_KEY, [])
    answer, action, reason = agent_ai.ask(question, request.user, history, image)

    if answer is None:
        # Sababni aytamiz: xodim nima qilishini bilsin (kutish, qisqartirish).
        return JsonResponse({'ok': False, 'answer': _t(AGENT_REASON_TEXT.get(
            reason, 'dash.agent_offline'))})

    history = (history + [['user', question], ['agent', answer]])[-AGENT_HISTORY_LIMIT:]
    request.session[AGENT_HISTORY_KEY] = history
    request.session[AGENT_PENDING_KEY] = action
    request.session.modified = True

    return JsonResponse({
        'ok': True,
        'answer': answer,
        'action': {'label': action['label'], 'summary': agent_run.describe(action)} if action else None,
        'has_image': bool(request.session.get(AGENT_IMAGE_KEY)),
    })


@role_required(*MANAGER_ROLES)
def agent_run_pending(request):
    """Taklif qilingan amalni TASDIQLANGANDAN keyin bajaradi."""
    if request.method != 'POST':
        return redirect('dashboard:agent')

    action = request.session.get(AGENT_PENDING_KEY)
    if not action:
        messages.error(request, _t('dash.agent_no_action'))
        return redirect('dashboard:agent')

    stored_name = request.session.get(AGENT_IMAGE_KEY)
    image = agent_uploads.load(stored_name)
    try:
        record, obj = agent_run.run_and_log(action, request.user, image)
    finally:
        if image is not None:
            image.close()

    request.session[AGENT_PENDING_KEY] = None
    if obj is not None:
        # Rasm yozuvga ko'chdi — vaqtinchalik nusxa kerak emas.
        agent_uploads.discard(stored_name)
        request.session[AGENT_IMAGE_KEY] = None
    request.session.modified = True

    if obj is None:
        messages.error(request, '%s: %s' % (_t('dash.agent_failed'), record.error))
    else:
        messages.success(request, '%s — %s' % (_t('dash.saved'), record.summary))
        if record.object_url:
            return redirect(record.object_url)
    return redirect('dashboard:agent')


@role_required(*MANAGER_ROLES)
def agent_cancel(request):
    """Taklifni bekor qiladi."""
    if request.method == 'POST':
        agent_uploads.discard(request.session.get(AGENT_IMAGE_KEY))
        request.session[AGENT_PENDING_KEY] = None
        request.session[AGENT_IMAGE_KEY] = None
        request.session.modified = True
    return redirect('dashboard:agent')


@role_required(*MANAGER_ROLES)
def agent_reset(request):
    """Suhbatni tozalaydi."""
    if request.method == 'POST':
        agent_uploads.discard(request.session.get(AGENT_IMAGE_KEY))
        request.session[AGENT_HISTORY_KEY] = []
        request.session[AGENT_PENDING_KEY] = None
        request.session[AGENT_IMAGE_KEY] = None
        request.session.modified = True
    return redirect('dashboard:agent')


@role_required(*MANAGER_ROLES)
def agent_pulse(request):
    """Nazorat qatori — sahifa uni davriy yangilab turadi."""
    return JsonResponse({'alerts': agent_ai.alerts(), 'snapshot': agent_ai.site_snapshot()})


# --------------------------------------------------------------------------
# O'z profili
# --------------------------------------------------------------------------
@role_required(*CHAT_ROLES)
def my_profile(request):
    """Har bir xodim o'z ismi, telefoni va parolini o'zgartiradi.

    Rol bu yerda YO'Q: aks holda menejer o'ziga administrator huquqini
    berib qo'ya olardi. Rolni faqat administrator, boshqa xodimning
    sahifasidan o'zgartiradi.
    """
    if request.method == 'POST':
        form = MyProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            changed = form.password_changed
            form.save()
            if changed:
                # Parol almashgach Django sessiyani bekor qiladi —
                # xodim o'zini chiqarib yubormasin.
                update_session_auth_hash(request, request.user)
                messages.success(request, _t('dash.password_changed'))
            else:
                messages.success(request, _t('dash.profile_saved'))
            return redirect('dashboard:profile')
    else:
        form = MyProfileForm(instance=request.user)

    return render(request, 'dashboard/profile.html', {
        'form': form,
        'profile': getattr(request.user, 'profile', None),
    })
