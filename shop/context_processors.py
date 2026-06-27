from .cart import Cart
from .models import Category


def cart_info(request):
    cart = Cart(request)
    return {
        'cart_count': len(cart),
        'cart_subtotal': cart.subtotal,
        'nav_categories': Category.objects.all()[:6],
    }
