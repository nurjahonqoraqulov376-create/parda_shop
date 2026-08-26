class NoCacheMiddleware:
    """Sahifalarni brauzer keshida (shu jumladan orqaga/oldinga bfcache) saqlamaslikka majburlaydi.

    Har bir sahifada savat, foydalanuvchi va boshqa sessiyaga bog'liq holat ko'rsatiladi,
    shuning uchun "orqaga" tugmasi bosilganda brauzer eski (masalan, mahsulot savatga
    qo'shilishidan oldingi) sahifani keshdan emas, serverdan qayta so'rashi kerak.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response
