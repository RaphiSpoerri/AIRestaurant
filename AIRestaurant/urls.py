from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.index, name='index'),
    path('menu/', views.menu, name='menu'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('ai_chat/', views.ai_chat, name='ai_chat'),
    path('rate_ai_response/<int:rating_id>/', views.rate_ai_response, name='rate_ai_response'),
    
    # Customer pages
    path('cart/', views.cart, name='cart'),
    path('add_to_cart/<int:menu_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:menu_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('place_order/', views.place_order, name='place_order'),
    path('order_history/', views.order_history, name='order_history'),
    path('deposit/', views.deposit, name='deposit'),
    path('rate_chef/<int:order_id>/', views.rate_chef, name='rate_chef'),
    path('file_complaint/', views.file_complaint, name='file_complaint'),
    path('file_compliment/', views.file_compliment, name='file_compliment'),
    path('my_complaints/', views.my_complaints, name='my_complaints'),
    
    # Delivery pages
    path('available_orders/', views.available_orders, name='available_orders'),
    path('delivery_bid/<int:order_id>/', views.delivery_bid, name='delivery_bid'),
    path('my_deliveries/', views.my_deliveries, name='my_deliveries'),
    
    # Chef pages
    path('chef_dashboard/', views.chef_dashboard, name='chef_dashboard'),
    
    # Manager pages
    path('manager_dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manage_menu/', views.manage_menu, name='manage_menu'),
    path('review_complaint/<int:complaint_id>/', views.review_complaint, name='review_complaint'),
    path('assign_order/<int:order_id>/', views.assign_order, name='assign_order'),
    
    # Order status update
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    # Cart operations
    path('update_cart/', views.update_cart, name='update_cart'),
    
    # Dish rating
    path('rate_dish/<int:dish_id>/', views.rate_dish, name='rate_dish'),
]

