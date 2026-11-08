from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('finance/', views.finance_dashboard_view, name='dashboard'),
    path('finance/transactions/create/', views.transaction_create_view, name='transaction_create'),
    path('finance/transactions/<int:pk>/edit/', views.transaction_edit_view, name='transaction_edit'),
    path('finance/transactions/<int:pk>/delete/', views.transaction_delete_view, name='transaction_delete'),
    path('finance/categories/create/', views.finance_category_create_view, name='category_create'),
]
