from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('savat/', views.cart_detail, name='cart_detail'),
    path('savat/qoshish/<int:pk>/', views.cart_add, name='cart_add'),
    path('savat/yangilash/<int:pk>/', views.cart_update, name='cart_update'),
    path('savat/ochirish/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('rasmiylashtirish/', views.checkout, name='checkout'),
    path('buyurtma/<int:pk>/rahmat/', views.order_success, name='success'),
    path('sorov/', views.lead_create, name='lead_create'),
]
