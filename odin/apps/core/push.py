import firebase_admin
from firebase_admin import credentials

from django.conf import settings

from odin.apps.core.models import Device


def send_push_notification(
    device: Device, title: str, body: str, icon: str | None = None, badge: str | None = None
) -> dict:
    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/static/favicon-128.png",
        "badge": badge or "/static/favicon-32.png",
    }
    cred = credentials.Certificate(settings.FIREBASE_ADMIN_CREDENTIALS_FILE)
    firebase_admin.initialize_app(cred)
    return payload
