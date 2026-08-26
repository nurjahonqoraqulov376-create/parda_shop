from django.urls import path

from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'),
    path('biz-haqimizda/', views.about, name='about'),
    path('ishlarimiz/', views.work_list, name='works'),
    path('ishlarimiz/<slug:slug>/', views.work_detail, name='work_detail'),
    path('aloqa/', views.contact, name='contact'),
]
