from django.urls import path, re_path
from . import views
from . import views_submit

urlpatterns = [
    # Public pages
    path('', views.home, name='index'),
    path('menu/', views.menu, name='menu'),
    path('merch/', views.merch, name='merch'),
    path('faq/', views.faq, name='faq'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/', views.register, name='register'),
    path('ai_chat/', views.ai_chat, name='ai_chat'),
    path('rate_ai_response/<int:rating_id>/', views.rate_ai_response, name='rate_ai_response'),
    path('discussions/', views.discussions, name='discussions'),
    path('create_thread/', views.create_thread, name='create_thread'),
    path('thread/<int:thread_id>/', views.thread_view, name='thread'),
    path('submit_message/', views_submit.submit_message, name='submit_message'),
    path('submit_complaint/', views_submit.submit_complaint, name='submit_complaint'),
    path('submit_compliment/', views_submit.submit_compliment, name='submit_compliment'),

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
    path('suspended/', views.suspended_notice, name='suspended_notice'),
    path('plea/<int:plea_id>/kick/', views.plea_kick, name='plea_kick'),
    path('plea/<int:plea_id>/forgive/', views.plea_forgive, name='plea_forgive'),
    
    # Delivery pages
    path('available_orders/', views.available_orders, name='available_orders'),
    path('delivery_bid/<int:order_id>/', views.delivery_bid, name='delivery_bid'),
    path('my_deliveries/', views.my_deliveries, name='my_deliveries'),
    
    # Chef pages
    
    # Manager pages
    path('manage_menu/', views.manage_menu, name='manage_menu'),
    path('manage_users/', views.manage_users, name='manage_users'),
    path('review_complaint/<int:complaint_id>/', views.review_complaint, name='review_complaint'),
    path('assign_order/<int:order_id>/', views.assign_order, name='assign_order'),
    path('approve_user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject_user/<int:user_id>/', views.reject_user, name='reject_user'),
    
    # Order status update
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    # Allow both query-string and path forms for customer profiles:
    path('customer/', views.customer, name='customer'),
    path('customer/<str:profile>/', views.customer, name='customer_profile'),
    path('chef/', views.chef, name='chef'),
    path('deliverer/', views.deliverer, name='deliverer'),
    path('manager/', views.manager, name='manager'),
    # Generic profile view by user id (used by thread/profile links)
    path('profile/<int:user_id>/', views.profile_view, name='profile'),
    path('cart/', views.cart, name='cart'),
    path('update_cart/', views.update_cart, name='update_cart'),
    
    
    # Dish rating
    path('rate_dish/<int:dish_id>/', views.rate_dish, name='rate_dish'),
]

