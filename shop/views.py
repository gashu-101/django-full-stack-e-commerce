import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import emails, payments
from .cart import Cart
from .forms import CheckoutForm
from .models import Category, Order, OrderItem, Product

log = logging.getLogger(__name__)


# ============================================================================
# Catalogue
# ============================================================================
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


# ============================================================================
# Cart
# ============================================================================
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


# ============================================================================
# Checkout
# ============================================================================
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('shop:shop')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        method = request.POST.get('payment_method', 'cod')
        if method not in dict(Order.METHOD):
            method = 'cod'
        if form.is_valid():
            order = form.save(commit=False)
            order.total = cart.subtotal
            order.payment_method = method
            order.tx_ref = payments.make_tx_ref(prefix=f'nova-{method}')
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
            emails.order_confirmation(order)
            return _route_to_gateway(request, order)
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {
        'form': form,
        'cart': cart,
        'methods': Order.METHOD,
        'chapa_enabled': payments.Chapa.configured(),
        'crypto_enabled': payments.NowPayments.configured(),
        'chapa_currency': settings.CHAPA_CURRENCY,
        'chapa_estimated': payments.Chapa.convert_amount(cart.subtotal),
    })


def _route_to_gateway(request, order):
    method = order.payment_method
    if method == 'chapa':
        return redirect('shop:chapa_initiate', tx_ref=order.tx_ref)
    if method == 'crypto':
        return redirect('shop:crypto_initiate', tx_ref=order.tx_ref)
    # COD — nothing to charge
    order.status = 'pending'
    order.save(update_fields=['status'])
    emails.admin_notification(order)
    return redirect('shop:order_success', order_id=order.id)


def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'shop/order_success.html', {'order': order})


def payment_failed(request, tx_ref):
    order = get_object_or_404(Order, tx_ref=tx_ref)
    if order.status not in ('paid',):
        order.status = 'failed'
        order.save(update_fields=['status'])
    return render(request, 'shop/payment_failed.html', {'order': order})


# ============================================================================
# Chapa — Ethiopian payments
# ============================================================================
def chapa_initiate(request, tx_ref):
    order = get_object_or_404(Order, tx_ref=tx_ref)
    if not payments.Chapa.configured():
        messages.error(request, 'Chapa is not configured. Set CHAPA_SECRET_KEY in your .env.')
        return redirect('shop:checkout')
    try:
        result = payments.Chapa.initialize(order, request)
    except payments.PaymentError as e:
        log.error('Chapa init failed: %s', e)
        messages.error(request, f'Could not start Chapa payment: {e}')
        order.status = 'failed'
        order.save(update_fields=['status'])
        return redirect('shop:payment_failed', tx_ref=order.tx_ref)
    order.payment_url = result['checkout_url']
    order.payment_meta = {'initialize': result['raw']}
    order.save(update_fields=['payment_url', 'payment_meta'])
    return redirect(result['checkout_url'])


def chapa_return(request, tx_ref):
    """Browser return URL after Chapa hosted checkout. Verify server-side."""
    order = get_object_or_404(Order, tx_ref=tx_ref)
    if order.status != 'paid':
        try:
            data = payments.Chapa.verify(tx_ref)
            _mark_paid_if_success(order, 'chapa', data, status=(data.get('data') or {}).get('status'))
        except payments.PaymentError as e:
            log.warning('Chapa verify on return failed: %s', e)
    if order.status == 'paid':
        return redirect('shop:order_success', order_id=order.id)
    return render(request, 'shop/payment_pending.html', {'order': order})


@csrf_exempt
@require_POST
def chapa_webhook(request):
    """Chapa POSTs here. Verify signature, re-verify with API, then mark paid."""
    sig = request.headers.get('Chapa-Signature') or request.headers.get('x-chapa-signature', '')
    if not payments.Chapa.verify_webhook_signature(request.body, sig):
        log.warning('Chapa webhook signature invalid')
        return HttpResponse('invalid signature', status=400)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest('invalid json')
    tx_ref = body.get('tx_ref') or body.get('trx_ref') or (body.get('data') or {}).get('tx_ref')
    if not tx_ref:
        return HttpResponseBadRequest('missing tx_ref')
    order = Order.objects.filter(tx_ref=tx_ref).first()
    if not order:
        return HttpResponse('order not found', status=404)
    try:
        verified = payments.Chapa.verify(tx_ref)
    except payments.PaymentError as e:
        log.error('Chapa server verify failed for %s: %s', tx_ref, e)
        return HttpResponse('verify failed', status=502)
    inner_status = (verified.get('data') or {}).get('status') or body.get('status')
    _mark_paid_if_success(order, 'chapa', verified, status=inner_status)
    return HttpResponse('ok')


# ============================================================================
# Crypto via NOWPayments
# ============================================================================
def crypto_initiate(request, tx_ref):
    order = get_object_or_404(Order, tx_ref=tx_ref)
    if not payments.NowPayments.configured():
        messages.error(request, 'Crypto payments are not configured. Set NOWPAYMENTS_API_KEY in your .env.')
        return redirect('shop:checkout')
    try:
        result = payments.NowPayments.create_invoice(order, request)
    except payments.PaymentError as e:
        log.error('NOWPayments invoice failed: %s', e)
        messages.error(request, f'Could not start crypto payment: {e}')
        order.status = 'failed'
        order.save(update_fields=['status'])
        return redirect('shop:payment_failed', tx_ref=order.tx_ref)
    order.payment_url = result['invoice_url']
    order.payment_meta = {'invoice': result['raw']}
    order.save(update_fields=['payment_url', 'payment_meta'])
    return redirect(result['invoice_url'])


def crypto_return(request, tx_ref):
    order = get_object_or_404(Order, tx_ref=tx_ref)
    # NOWPayments confirms asynchronously via IPN — don't mark paid from the return URL.
    if order.status == 'paid':
        return redirect('shop:order_success', order_id=order.id)
    return render(request, 'shop/payment_pending.html', {'order': order, 'is_crypto': True})


@csrf_exempt
@require_POST
def crypto_webhook(request):
    """NOWPayments IPN. Verify HMAC SHA-512 over the sorted JSON body."""
    sig = request.headers.get('x-nowpayments-sig', '')
    if not payments.NowPayments.verify_ipn_signature(request.body, sig):
        log.warning('NOWPayments IPN signature invalid')
        return HttpResponse('invalid signature', status=400)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest('invalid json')
    tx_ref = body.get('order_id')
    order = Order.objects.filter(tx_ref=tx_ref).first()
    if not order:
        return HttpResponse('order not found', status=404)
    status_value = body.get('payment_status')
    _mark_paid_if_success(order, 'crypto', body, status=status_value)
    return HttpResponse('ok')


# ============================================================================
# Helpers
# ============================================================================
def _mark_paid_if_success(order, gateway, payload, status):
    order.payment_meta = {**(order.payment_meta or {}), 'verified': payload}
    if payments.is_paid_status(gateway, status):
        if order.status != 'paid':
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at', 'payment_meta'])
            emails.order_paid(order)
            emails.admin_notification(order)
        else:
            order.save(update_fields=['payment_meta'])
    elif str(status).lower() in ('failed', 'cancelled', 'expired'):
        order.status = 'failed'
        order.save(update_fields=['status', 'payment_meta'])
    else:
        order.save(update_fields=['payment_meta'])
