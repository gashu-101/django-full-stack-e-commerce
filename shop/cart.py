from decimal import Decimal
from django.conf import settings
from .models import Product


class Cart:
    """Session-backed shopping cart."""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def _save(self):
        self.session.modified = True

    def add(self, product, quantity=1, override=False):
        pid = str(product.pk)
        if pid not in self.cart:
            self.cart[pid] = {'quantity': 0, 'price': str(product.price)}
        if override:
            self.cart[pid]['quantity'] = quantity
        else:
            self.cart[pid]['quantity'] += quantity
        if self.cart[pid]['quantity'] <= 0:
            self.remove(product)
        else:
            self._save()

    def remove(self, product):
        pid = str(product.pk)
        if pid in self.cart:
            del self.cart[pid]
            self._save()

    def __iter__(self):
        ids = self.cart.keys()
        products = Product.objects.filter(pk__in=ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.pk)]['product'] = product
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    @property
    def subtotal(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        self.session[settings.CART_SESSION_ID] = {}
        self._save()
