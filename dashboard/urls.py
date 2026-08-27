from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from accounts.forms import StaffLoginForm

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('kirish/', LoginView.as_view(
        template_name='dashboard/login.html',
        authentication_form=StaffLoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('chiqish/', LogoutView.as_view(), name='logout'),
    path('', views.overview, name='overview'),
    path('buyurtmalar/', views.order_list, name='order_list'),
    path('buyurtmalar/<int:pk>/', views.order_detail, name='order_detail'),
    path('sorovlar/', views.lead_list, name='lead_list'),
    path('sorovlar/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('foydalanuvchilar/', views.user_list, name='user_list'),
    path('foydalanuvchilar/yangi/', views.user_form, name='user_create'),
    path('foydalanuvchilar/<int:pk>/', views.user_form, name='user_edit'),
    path('foydalanuvchilar/<int:pk>/ochirish/', views.user_delete, name='user_delete'),
    path('sozlamalar/', views.site_settings, name='settings'),
    # Suhbatlar pastdagi `<slug:key>` catch-all'dan OLDIN turishi shart —
    # aks holda `suhbatlar/` generic CRUD bo'limi deb qabul qilinadi.
    path('kirgandan-keyin/', views.after_login, name='after_login'),
    path('suhbatlar/', views.chat_list, name='chat_list'),
    path('suhbatlar/<int:pk>/', views.chat_detail, name='chat_detail'),
    path('suhbatlar/<int:pk>/yopish/', views.chat_close, name='chat_close'),
    path('<slug:key>/', views.section_list, name='section_list'),
    path('<slug:key>/yangi/', views.section_form, name='section_create'),
    path('<slug:key>/<int:pk>/', views.section_form, name='section_edit'),
    path('<slug:key>/<int:pk>/ochirish/', views.section_delete, name='section_delete'),
]
