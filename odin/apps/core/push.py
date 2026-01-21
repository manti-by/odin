from typing import Any

from webpush import WebPush, WebPushException

from django.conf import settings

from odin.apps.core.models import Device


def _get_webpush() -> WebPush:
    return WebPush(
        private_key=settings.VAPID_PRIVATE_KEY.encode() if settings.VAPID_PRIVATE_KEY else b"",
        public_key=settings.VAPID_PUBLIC_KEY.encode() if settings.VAPID_PUBLIC_KEY else b"",
        subscriber=settings.VAPID_ADMIN_EMAIL or "mailto:admin@example.com",
    )


def send_push_notification(
    device: Device,
    title: str,
    body: str,
    icon: str | None = None,
    badge: str | None = None,
    data: dict[str, Any] | None = None,
    tag: str | None = None,
    url: str | None = None,
) -> bool:
    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/static/favicon-128.png",
        "badge": badge or "/static/favicon-32.png",
    }
    if data:
        payload["data"] = data
    if tag:
        payload["tag"] = tag
    if url:
        payload["url"] = url

    try:
        wp = _get_webpush()
        wp.send(subscription=device.subscription, payload=payload, ttl=86400)  # ty: ignore[unresolved-attribute]
        return True
    except WebPushException:
        return False


def send_broadcast_notification(
    title: str,
    body: str,
    icon: str | None = None,
    badge: str | None = None,
    data: dict[str, Any] | None = None,
    tag: str | None = None,
    url: str | None = None,
) -> tuple[int, int]:
    devices = list(Device.objects.active())
    if not devices:
        return 0, 0

    success_count = 0
    failure_count = 0

    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/static/favicon-128.png",
        "badge": badge or "/static/favicon-32.png",
    }
    if data:
        payload["data"] = data
    if tag:
        payload["tag"] = tag
    if url:
        payload["url"] = url

    wp = _get_webpush()

    for device in devices:
        try:
            wp.send(subscription=device.subscription, payload=payload, ttl=86400)  # ty: ignore[unresolved-attribute]
            success_count += 1
        except WebPushException:
            device.is_active = False
            device.save(update_fields=["is_active"])
            failure_count += 1

    return success_count, failure_count
