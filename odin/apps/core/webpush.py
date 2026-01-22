import json
import logging

from pywebpush import WebPushException, webpush
from requests import Response

from django.conf import settings

from odin.apps.core.models import Device


logger = logging.getLogger(__name__)


def send_push_notification(
    device: Device, title: str, body: str, icon: str | None = None, badge: str | None = None
) -> Response | str | None:
    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/static/favicon-128.png",
        "badge": badge or "/static/favicon-32.png",
    }
    try:
        return webpush(
            subscription_info=device.subscription,
            data=json.dumps(payload),
            vapid_private_key=settings.FIREBASE_CLOUD_MESSAGING_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.FIREBASE_CLOUD_MESSAGING_ADMIN_EMAIL,
            },
        )
    except WebPushException as e:
        logger.error(f"Can't send a webpush to device {device.pk}: {e}")
    return None


def send_push_notification_to_admins(title: str, body: str, icon: str | None = None, badge: str | None = None) -> None:
    for device in Device.objects.filter(is_admin=True):
        send_push_notification(device=device, title=title, body=body, icon=icon, badge=badge)
