"""Agent taklif qilgan amalni tekshirib bajaradi.

Bu fayl `agent.py` dan ataylab ajratilgan: u yerda AI bilan gaplashish,
bu yerda esa **bazaga yozish**. Yozish yo'li bitta va tor bo'lishi kerak.

Kafolatlar:

* Faqat `agent.ACTIONS` dagi amal bajariladi. O'chirish amali umuman yo'q.
* Har bir yozuv panelning **o'z formasidan** o'tadi — tekshiruvlar,
  slug yasash va avtomatik tarjima bir xil ishlaydi.
* Menejer administratorgina kiradigan bo'limga yoza olmaydi.
* Bajarilgani ham, xato bo'lgani ham `AgentAction` ga yoziladi.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from accounts.permissions import has_role

from .agent import ACTIONS
from .models import AgentAction
from .registry import get_form_class, get_section

logger = logging.getLogger(__name__)


class ActionError(Exception):
    """Amalni bajarib bo'lmadi (tekshiruvdan o'tmadi yoki yozuv topilmadi)."""


def _section_for(name, user):
    spec = ACTIONS.get(name)
    if spec is None:
        raise ActionError('Bunday amal yo‘q: %s' % name)
    section = get_section(spec['section'])
    if section is None:
        raise ActionError('Bo‘lim topilmadi: %s' % spec['section'])
    if section['admin_only'] and not has_role(user, 'admin'):
        raise PermissionDenied('Bu bo‘limga ruxsatingiz yo‘q')
    return spec, section, spec['section']


# `AgentAction.summary` — CharField(255). Tavsif undan uzun bo'lsa
# PostgreSQL yozuvni RAD ETADI (`value too long for type character
# varying(255)`) va tasdiqlash 500 bilan tugaydi. SQLite uzunlikni
# tekshirmaydi, shuning uchun bu faqat serverda bilingandi.
# To'liq ma'lumot `payload` (JSON) da saqlanadi, ya'ni qisqartirish
# hech narsani yo'qotmaydi.
SUMMARY_LIMIT = 240
VALUE_LIMIT = 60


def _short(value, limit=VALUE_LIMIT):
    text = str(value).replace('\n', ' ').strip()
    return text if len(text) <= limit else text[:limit - 1] + '…'


def describe(action):
    """Tasdiqlash kartochkasi va jurnal uchun qisqa tavsif."""
    spec = ACTIONS.get(action.get('action'))
    label = spec['label'] if spec else action.get('action', '')
    pairs = ', '.join(
        '%s: %s' % (key, _short(value))
        for key, value in (action.get('fields') or {}).items()
    )
    text = '%s (%s)' % (label, pairs) if pairs else label
    return _short(text, SUMMARY_LIMIT)


def image_field_name(model):
    """Modeldagi rasm maydonining nomi (`image`, `photo`, `logo`) yoki None.

    `isinstance` bilan tekshiramiz: `ImageField.get_internal_type()`
    `'FileField'` qaytaradi, ya'ni nom bo'yicha solishtirish ishlamaydi.
    """
    from django.db.models import ImageField
    for field in model._meta.get_fields():
        if isinstance(field, ImageField):
            return field.name
    return None


def execute(action, user, image=None):
    """Amalni bajaradi va yaratilgan/o'zgartirilgan yozuvni qaytaradi.

    `image` — yordamchiga yuborilgan rasm (ochilgan fayl). Model rasm
    qabul qilsa, forma orqali biriktiriladi.

    `(obyekt, bo'lim_kaliti)` qaytaradi. Xatolik bo'lsa `ActionError`.
    """
    name = (action or {}).get('action')
    fields = dict((action or {}).get('fields') or {})
    spec, section, section_key = _section_for(name, user)

    # Oq ro'yxatdan tashqaridagi maydon bu yergacha yetib kelmasligi kerak,
    # lekin ikkinchi to'siq zarar qilmaydi.
    fields = {field: value for field, value in fields.items()
              if field in spec['allowed']}

    model = section['model']
    form_class = get_form_class(section_key)
    instance = None

    if name.startswith('update_'):
        pk = fields.pop('pk', None)
        try:
            instance = model.objects.get(pk=pk)
        except (model.DoesNotExist, TypeError, ValueError):
            raise ActionError('Yozuv topilmadi: #%s' % pk)

    data = _form_data(form_class, instance, fields)

    files = {}
    if image is not None:
        name = image_field_name(model)
        if name:
            from django.core.files.uploadedfile import SimpleUploadedFile
            files[name] = SimpleUploadedFile(
                getattr(image, 'name', 'rasm.jpg').rsplit('/', 1)[-1],
                image.read(), content_type='image/jpeg')

    form = form_class(data, files or None, instance=instance)
    if not form.is_valid():
        raise ActionError(_first_error(form))

    obj = form.save()
    return obj, section_key


def _form_data(form_class, instance, fields):
    """Formaning barcha maydonlarini to'ldiradi.

    O'zgartirishda mavjud qiymatlar asos qilib olinadi, agent bergan
    maydonlar ustidan yoziladi. Aks holda forma to'ldirilmagan maydonlarni
    «bo'sh» deb hisoblab, mavjud ma'lumotni o'chirib yuborardi.
    """
    data = {}
    blank_form = form_class(instance=instance)
    for field_name, field in blank_form.fields.items():
        if field.disabled:
            continue
        value = blank_form.initial.get(field_name, field.initial)
        if hasattr(value, 'pk'):
            value = value.pk
        if value is not None and value != '':
            data[field_name] = value
    data.update(fields)
    return data


def _first_error(form):
    for field_name, errors in form.errors.items():
        if errors:
            return '%s: %s' % (field_name, errors[0])
    return 'Ma’lumot tekshiruvdan o‘tmadi'


def run_and_log(action, user, image=None):
    """`execute` ni chaqiradi va natijani jurnalga yozadi.

    `(AgentAction, obyekt|None)` qaytaradi. Xato bo'lsa obyekt `None`,
    yozuvda esa `status='failed'` va xato matni turadi.
    """
    summary = describe(action)[:SUMMARY_LIMIT]
    name = (action or {}).get('action', '')
    fields = (action or {}).get('fields') or {}

    try:
        obj, section_key = execute(action, user, image)
    except (ActionError, PermissionDenied) as exc:
        record = AgentAction.objects.create(
            user=user, action=name, summary=summary, payload=fields,
            status=AgentAction.STATUS_FAILED, error=str(exc),
        )
        return record, None

    url = ''
    try:
        url = reverse('dashboard:section_edit', args=[section_key, obj.pk])
    except Exception:  # pragma: no cover - manzil bo'lmasa jurnal buzilmasin
        logger.warning('Amal manzilini yasab bo‘lmadi: %s', name)

    record = AgentAction.objects.create(
        user=user, action=name, summary=summary, payload=fields,
        status=AgentAction.STATUS_DONE, object_id=obj.pk, object_url=url,
    )
    return record, obj
