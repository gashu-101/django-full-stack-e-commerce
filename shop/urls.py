from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('shop/c/<slug:category_slug>/', views.shop, name='shop_by_category'),
    path('p/<slug:slug>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_success, name='order_success'),
    path('pay/failed/<str:tx_ref>/', views.payment_failed, name='payment_failed'),

    # Chapa — specific patterns first; the slug-matching initiate route last.
    path('pay/chapa/webhook/', views.chapa_webhook, name='chapa_webhook'),
    path('pay/chapa/return/<str:tx_ref>/', views.chapa_return, name='chapa_return'),
    path('pay/chapa/<str:tx_ref>/', views.chapa_initiate, name='chapa_initiate'),

    # Crypto (NOWPayments)
    path('pay/crypto/webhook/', views.crypto_webhook, name='crypto_webhook'),
    path('pay/crypto/return/<str:tx_ref>/', views.crypto_return, name='crypto_return'),
    path('pay/crypto/<str:tx_ref>/', views.crypto_initiate, name='crypto_initiate'),
]
