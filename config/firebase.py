import requests
import json

from db.models import NotificationChannelConfig, NotificationTemplate
from enums.store import NotificationChannel

FCM_URL = "https://fcm.googleapis.com/fcm/send"

def render_template(text: str, context: dict) -> str:
    """
    Simple {{var}} replacement
    """
    if not text:
        return ""
    for key, value in context.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def send_push_notification(
    *,
    store,
    event,
    user,
    context: dict
):
    """
    Sends PUSH notification using store-based FCM config
    """

    # 1️⃣ Channel config (FCM)
    channel_config = NotificationChannelConfig.objects.filter(
        store=store,
        channel=NotificationChannel.PUSH,
        is_active=True
    ).first()

    if not channel_config or not channel_config.fcm_server_key:
        return False, "FCM not configured for store"

    # 2️⃣ Template
    template = NotificationTemplate.objects.filter(
        store=store,
        event=event,
        channel=NotificationChannel.PUSH,
        is_active=True
    ).first()

    if not template:
        return False, "Push template not found"

    # 3️⃣ Device token
    device_token = getattr(user, "device_token", None)
    if not device_token:
        return False, "User device token missing"

    # 4️⃣ Render content
    title = render_template(template.title, context)
    body = render_template(template.description, context)

    # 5️⃣ FCM payload
    payload = {
        "to": device_token,
        "notification": {
            "title": title,
            "body": body,
        },
        "data": {
            "event": event,
            **context
        }
    }

    headers = {
        "Authorization": f"key={channel_config.fcm_server_key}",
        "Content-Type": "application/json"
    }

    # 6️⃣ Send
    response = requests.post(
        FCM_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=10
    )

    if response.status_code != 200:
        return False, response.text

    return True, "Push sent successfully"