"""Payment gateway adapters: Chapa (Ethiopia) and NOWPayments (crypto).

Each adapter raises PaymentError on misconfiguration or HTTP failure. Webhook
helpers verify signatures cryptographically before trusting the payload.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.urls import reverse


class PaymentError(Exception):
    """Raised for misconfiguration, HTTP, or verification failures."""


def make_tx_ref(prefix: str = 'nova') -> str:
    return f"{prefix}-{secrets.token_urlsafe(12)}"


def absolute_url(request, path: str) -> str:
    """Build a fully-qualified URL the gateway can call back to."""
    if request is not None:
        return request.build_absolute_uri(path)
    return settings.SITE_URL + path


# =========================================================================
# Chapa — https://developer.chapa.co/
# =========================================================================
class Chapa:
    @staticmethod
    def configured() -> bool:
        return bool(settings.CHAPA_SECRET_KEY)

    @staticmethod
    def _headers() -> dict:
        if not settings.CHAPA_SECRET_KEY:
            raise PaymentError('CHAPA_SECRET_KEY is not configured.')
        return {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

    @staticmethod
    def convert_amount(usd_total: Decimal) -> Decimal:
        """Convert the cart's USD subtotal into the configured Chapa currency."""
        if settings.CHAPA_CURRENCY.upper() == 'USD':
            return Decimal(usd_total).quantize(Decimal('0.01'))
        rate = Decimal(str(settings.CHAPA_FX_RATE))
        return (Decimal(usd_total) * rate).quantize(Decimal('0.01'))

    @classmethod
    def initialize(cls, order, request) -> dict:
        """Create a Chapa transaction, returning the checkout URL."""
        amount = cls.convert_amount(order.total)
        payload = {
            'amount': str(amount),
            'currency': settings.CHAPA_CURRENCY,
            'email': order.email,
            'first_name': order.first_name or 'Customer',
            'last_name': order.last_name or '-',
            'tx_ref': order.tx_ref,
            'callback_url': absolute_url(request, reverse('shop:chapa_webhook')),
            'return_url': absolute_url(request, reverse('shop:chapa_return', args=[order.tx_ref])),
            'customization': {
                'title': 'Nova Studio',
                'description': f'Order #{order.id} — {len(order.items.all())} item(s)',
            },
        }
        try:
            resp = requests.post(
                f'{settings.CHAPA_BASE_URL}/transaction/initialize',
                json=payload, headers=cls._headers(), timeout=20,
            )
        except requests.RequestException as e:
            raise PaymentError(f'Chapa request failed: {e}') from e
        try:
            data = resp.json()
        except ValueError:
            raise PaymentError(f'Chapa returned non-JSON ({resp.status_code}).')
        if resp.status_code >= 400 or data.get('status') != 'success':
            raise PaymentError(data.get('message') or f'Chapa init failed ({resp.status_code}).')
        checkout = (data.get('data') or {}).get('checkout_url')
        if not checkout:
            raise PaymentError('Chapa response missing checkout_url.')
        return {'checkout_url': checkout, 'raw': data}

    @classmethod
    def verify(cls, tx_ref: str) -> dict:
        try:
            resp = requests.get(
                f'{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}',
                headers=cls._headers(), timeout=20,
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            raise PaymentError(f'Chapa verify failed: {e}') from e
        if data.get('status') != 'success':
            raise PaymentError(data.get('message') or 'Chapa verify returned non-success.')
        return data

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, header_value: str) -> bool:
        """Chapa sends a Chapa-Signature header — HMAC SHA-256 of body using secret."""
        if not settings.CHAPA_WEBHOOK_SECRET or not header_value:
            return False
        expected = hmac.new(
            settings.CHAPA_WEBHOOK_SECRET.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, header_value.strip())


# =========================================================================
# NOWPayments — https://documenter.getpostman.com/view/7907941
# =========================================================================
class NowPayments:
    @staticmethod
    def configured() -> bool:
        return bool(settings.NOWPAYMENTS_API_KEY)

    @staticmethod
    def _headers() -> dict:
        if not settings.NOWPAYMENTS_API_KEY:
            raise PaymentError('NOWPAYMENTS_API_KEY is not configured.')
        return {
            'x-api-key': settings.NOWPAYMENTS_API_KEY,
            'Content-Type': 'application/json',
        }

    @classmethod
    def create_invoice(cls, order, request) -> dict:
        """Create a hosted invoice. User is redirected to invoice_url."""
        payload = {
            'price_amount': float(Decimal(order.total).quantize(Decimal('0.01'))),
            'price_currency': settings.NOWPAYMENTS_PRICE_CURRENCY,
            'order_id': order.tx_ref,
            'order_description': f'Nova Studio — Order #{order.id}',
            'ipn_callback_url': absolute_url(request, reverse('shop:crypto_webhook')),
            'success_url': absolute_url(request, reverse('shop:crypto_return', args=[order.tx_ref])),
            'cancel_url': absolute_url(request, reverse('shop:payment_failed', args=[order.tx_ref])),
        }
        try:
            resp = requests.post(
                f'{settings.NOWPAYMENTS_BASE_URL}/invoice',
                json=payload, headers=cls._headers(), timeout=20,
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            raise PaymentError(f'NOWPayments request failed: {e}') from e
        if resp.status_code >= 400:
            raise PaymentError(data.get('message') or f'NOWPayments invoice failed ({resp.status_code}).')
        invoice_url = data.get('invoice_url')
        if not invoice_url:
            raise PaymentError('NOWPayments response missing invoice_url.')
        return {'invoice_url': invoice_url, 'raw': data}

    @classmethod
    def payment_status(cls, payment_id: str) -> dict:
        try:
            resp = requests.get(
                f'{settings.NOWPAYMENTS_BASE_URL}/payment/{payment_id}',
                headers=cls._headers(), timeout=20,
            )
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            raise PaymentError(f'NOWPayments status failed: {e}') from e

    @staticmethod
    def verify_ipn_signature(raw_body: bytes, header_value: str) -> bool:
        """NOWPayments signs the IPN body — HMAC SHA-512 of the *sorted* JSON
        using IPN secret. We re-sort to match their canonicalization."""
        if not settings.NOWPAYMENTS_IPN_SECRET or not header_value:
            return False
        try:
            obj = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return False
        canon = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
        expected = hmac.new(
            settings.NOWPAYMENTS_IPN_SECRET.encode('utf-8'),
            canon, hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, header_value.strip())


def is_paid_status(gateway: str, status_value: Any) -> bool:
    """Normalise the various 'success' status strings each gateway uses."""
    s = str(status_value or '').lower()
    if gateway == 'chapa':
        return s in ('success', 'successful', 'paid')
    if gateway == 'crypto':
        return s in ('finished', 'confirmed', 'paid')
    return False
