from django.urls import path

from . import views

app_name = 'catalog'

urlpatterns = [
    path('katalog/', views.catalog_list, name='list'),
    path('qidiruv/', views.search, name='search'),
    path('katalog/<slug:slug>/', views.category_detail, name='category'),
    path('mahsulot/<slug:slug>/', views.product_detail, name='product_detail'),
]
