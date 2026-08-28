release: python manage.py migrate --noinput && python manage.py setup_roles
web: gunicorn parda_shop.wsgi --bind 0.0.0.0:$PORT --workers 3 --timeout 60 --access-logfile - --error-logfile -
