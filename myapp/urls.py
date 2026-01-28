from django.contrib import admin
from django.urls import path
from myapp import views, consumer_views, business_views, manager_views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.login_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),

    path('home/', consumer_views.consumer_home_view, name='consumer_home'),
    path('search/', consumer_views.search_products_view, name='search_products'),
    path('cart/', consumer_views.cart_view, name='cart_view'),
    path('order/', consumer_views.order_view, name='order_view'),
    path('user/profile/', consumer_views.user_profile_view, name='user_profile'),
    path('product/<int:product_id>/', consumer_views.product_detail_view, name='product_detail'),
    path('add_to_cart/<int:product_id>/', consumer_views.add_to_cart_view, name='add_to_cart'),
    path('buy_now/<int:product_id>/', consumer_views.buy_now_view, name='buy_now'),
    path('like_comment/<int:comment_id>/', consumer_views.like_comment_view, name='like_comment'),
    path('delete_order/<str:order_id>/', consumer_views.delete_order_view, name='delete_order'),
    path('purchase_order/<str:order_id>/', consumer_views.purchase_order_view, name='purchase_order'),
    path('order/confirm_receipt/<str:order_id>/', consumer_views.confirm_receipt_view, name='confirm_receipt'),
    path('order/add_comment_for_order/<str:order_id>/<int:product_id>/', consumer_views.add_comment_for_order_view, name='add_comment_for_order'),
    path('api/get_product_clicks/', consumer_views.get_product_clicks_api, name='get_product_clicks'),

    path('business/home/', business_views.business_home_view, name='business_home'),
    path('business/product/<int:product_id>/', business_views.business_product_detail_view, name='business_product_detail'),
    path('business/add/', business_views.add_product_view, name='add_product'),
    path('business/update/', business_views.update_product_view, name='update_product'),
    path('business/delete/', business_views.delete_product_view, name='delete_product'),
    path('business/delete/<str:product_id>/', business_views.delete_single_product_view, name='delete_single_product'),
    path('business/profile/', business_views.business_profile_view, name='business_profile'),
    path('orders/', business_views.business_orders_view, name='orders'),
    path('ship_order/<str:order_id>/', business_views.ship_order_view, name='ship_order'),

    path('manager/logs/', manager_views.logs_view, name='logs_view'),
    path('manager/comments/', manager_views.comments_view, name='comments_view'),
    path('manager/delete_comment/<int:comment_id>/', manager_views.delete_comment_view, name='delete_comment'),
    path('manager/clicks/', manager_views.clicks_view, name='clicks_view'),
    path('manager/users/', manager_views.users_view, name='users_view'),
    path('manager/delete_user/<str:user_id>/', manager_views.delete_user_view, name='delete_user'),
]
