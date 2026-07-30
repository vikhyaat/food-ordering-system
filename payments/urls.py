from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('<int:order_id>/', views.pay, name='pay'),
    path('<int:order_id>/success/', views.payment_success, name='success'),
    path('<int:order_id>/receipt/', views.download_receipt, name='download_receipt'),
]
