from django.urls import path

from . import views

app_name = 'support'

urlpatterns = [
    path('suhbat/xabarlar/', views.history, name='history'),
    path('suhbat/yuborish/', views.send, name='send'),
]
