# DIQQAT: bu yerga `release:` qatorini QO'SHMANG.
#
# Nixpacks `release:` ni QURISH (build) bosqichiga qo'shib yuboradi, u yerda
# esa Railway'ning ichki tarmog'i hali yo'q — `postgres.railway.internal`
# topilmaydi va qurish "failed to resolve host" xatosi bilan to'xtaydi.
#
# Migratsiyalar Railway'ning o'z sozlamasi orqali bajariladi:
#   Settings -> Deploy -> Pre-deploy Command
#   python manage.py migrate --noinput && python manage.py setup_roles
# U ishlash paytida bajariladi va bazaga ulana oladi.
web: gunicorn parda_shop.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile - --error-logfile -
