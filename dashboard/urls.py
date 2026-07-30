from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),

    path('users/', views.manage_users, name='manage_users'),
    path('users/<int:user_id>/toggle-block/', views.toggle_block_user, name='toggle_block_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/add/', views.category_form_view, name='add_category'),
    path('categories/<int:pk>/edit/', views.category_form_view, name='edit_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),

    path('food/', views.manage_food, name='manage_food'),
    path('food/add/', views.food_form_view, name='add_food'),
    path('food/<int:pk>/edit/', views.food_form_view, name='edit_food'),
    path('food/<int:pk>/delete/', views.delete_food, name='delete_food'),

    path('orders/', views.manage_orders, name='manage_orders'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),

    path('payments/', views.manage_payments, name='manage_payments'),

    path('reports/', views.reports, name='reports'),
    path('reports/export/csv/', views.export_orders_csv, name='export_orders_csv'),
]
