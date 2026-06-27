from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Category, Order, OrderItem
from .cart import Cart
from .forms import CheckoutForm


def home(request):
    featured = Product.objects.filter(featured=True)[:4]
    latest = Product.objects.all()[:8]
    categories = Category.objects.all()
    return render(request, 'shop/home.html', {
        'featured': featured,
        'latest': latest,
        'categories': categories,
    })


def shop(request, category_slug=None):
    products = Product.objects.all()
    current = None
    if category_slug:
        current = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=current)

    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(name__icontains=q)

    return render(request, 'shop/shop.html', {
        'products': products,
        'categories': Category.objects.all(),
        'current_category': current,
        'q': q,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related': related,
    })


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    try:
        qty = max(1, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        qty = 1
    override = request.POST.get('override') == '1'
    cart.add(product, quantity=qty, override=override)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({'ok': True, 'count': len(cart), 'subtotal': str(cart.subtotal)})
    messages.success(request, f"Added {product.name} to your bag.")
    return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    cart.remove(product)
    return redirect('shop:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'shop/cart.html', {'cart': cart})


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('shop:shop')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.total = cart.subtotal
            order.save()
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product'].name,
                    price=item['price'],
                    quantity=item['quantity'],
                )
            cart.clear()
            return redirect('shop:order_success', order_id=order.pk)
    else:
        form = CheckoutForm()
    return render(request, 'shop/checkout.html', {'form': form, 'cart': cart})


def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'shop/order_success.html', {'order': order})
