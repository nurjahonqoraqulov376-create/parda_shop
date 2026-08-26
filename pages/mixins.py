from django.utils.translation import get_language

from parda_shop.mt import is_enabled, translate_html


class TranslatableMixin:
    """Model maydonining joriy tilga mos variantini qaytaradi.

    Har bir tarjima qilinadigan maydon uchun modelda `<field>_ru` maydoni
    bo'lishi kutiladi. Ruscha variant bo'sh bo'lsa o'zbekchasi qaytariladi.

    Saqlash paytida `<field>_ru` o'zbekcha maydondan avtomatik tarjima
    qilinadi. Tarjima muvaffaqiyatsiz bo'lsa maydon tegilmaydi.
    """

    # Model darajasida yoki alohida obyektda `False` qilinsa tarjima o'chadi.
    auto_translate = True

    def t(self, field):
        value = getattr(self, field, '') or ''
        if (get_language() or '').startswith('ru'):
            return getattr(self, f'{field}_ru', '') or value
        return value

    @classmethod
    def translatable_fields(cls):
        """`(uz_maydon, ru_maydon)` juftliklari ro'yxati."""
        names = {field.name for field in cls._meta.fields}
        return [
            (name, f'{name}_ru')
            for name in sorted(names)
            if not name.endswith('_ru') and f'{name}_ru' in names
        ]

    def apply_auto_translation(self, only=None):
        """Ruscha maydonlarni o'zbekchasidan qayta yozadi.

        `only` berilsa faqat shu o'zbekcha maydonlar ko'riladi. Yangilangan
        ruscha maydonlar nomlari to'plami qaytariladi.
        """
        updated = set()
        for source_name, target_name in self.translatable_fields():
            if only is not None and source_name not in only:
                continue
            source = (getattr(self, source_name, '') or '').strip()
            if not source:
                continue
            translated = translate_html(source)
            if translated is None:  # tarmoq yo'q yoki xato — eski qiymat qoladi
                continue
            limit = self._meta.get_field(target_name).max_length
            if limit:
                translated = translated[:limit]
            setattr(self, target_name, translated)
            updated.add(target_name)
        return updated

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.auto_translate and is_enabled():
            only = set(update_fields) if update_fields is not None else None
            updated = self.apply_auto_translation(only=only)
            if update_fields is not None and updated:
                kwargs['update_fields'] = set(update_fields) | updated
        super().save(*args, **kwargs)
