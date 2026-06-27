"""Transactional email helpers. Falls back gracefully if SMTP is misconfigured —
errors are logged, never raised into the request cycle."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

log = logging.getLogger(__name__)


def _send(subject: str, to: list[str], template: str, context: dict, reply_to=None):
    try:
        html = render_to_string(template, context)
        text = strip_tags(html)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            reply_to=reply_to or None,
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        log.warning('Email send failed (%s → %s): %s', template, to, e)
        return False


def order_confirmation(order):
    """Sent right after the order is placed — before payment confirmation."""
    return _send(
        subject=f'Order #{order.id} received — Nova',
        to=[order.email],
        template='emails/order_confirmation.html',
        context={'order': order, 'site_url': settings.SITE_URL, 'paid': False},
    )


def order_paid(order):
    """Sent once we have a verified payment from the gateway."""
    return _send(
        subject=f'Payment confirmed for order #{order.id} — Nova',
        to=[order.email],
        template='emails/order_confirmation.html',
        context={'order': order, 'site_url': settings.SITE_URL, 'paid': True},
    )


def admin_notification(order):
    """Sent to the studio admin whenever a new order is paid."""
    if not getattr(settings, 'ADMIN_EMAIL', None):
        return False
    return _send(
        subject=f'[Nova] New paid order #{order.id} — ${order.total}',
        to=[settings.ADMIN_EMAIL],
        template='emails/admin_new_order.html',
        context={'order': order, 'site_url': settings.SITE_URL},
        reply_to=[order.email],
    )
