class NoCacheMiddleware:
    """HTML sahifalarni brauzer keshida (shu jumladan bfcache) saqlamaslikka majburlaydi.

    Har bir sahifada savat, foydalanuvchi va boshqa sessiyaga bog'liq holat
    ko'rsatiladi, shuning uchun "orqaga" tugmasi bosilganda brauzer eski
    (masalan, mahsulot savatga qo'shilishidan oldingi) sahifani keshdan emas,
    serverdan qayta so'rashi kerak.

    Rasm, CSS va JS bunga kirmaydi: ular sessiyaga bog'liq emas va keshlanishi
    kerak, aks holda har bir sahifada qaytadan yuklanib sayt sekinlashadi.
    """

    CACHEABLE_PREFIXES = ('image/', 'font/', 'video/', 'audio/')
    CACHEABLE_TYPES = (
        'text/css',
        'text/javascript',
        'application/javascript',
        'application/pdf',
        'image/svg+xml',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    @classmethod
    def _is_static_asset(cls, content_type):
        content_type = (content_type or '').split(';')[0].strip().lower()
        if not content_type:
            return False
        return content_type.startswith(cls.CACHEABLE_PREFIXES) or content_type in cls.CACHEABLE_TYPES

    def __call__(self, request):
        response = self.get_response(request)
        if self._is_static_asset(response.get('Content-Type')):
            return response
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response
