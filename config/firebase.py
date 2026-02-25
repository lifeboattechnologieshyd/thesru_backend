



import json
import firebase_admin
from firebase_admin import credentials, messaging

from db.models import NotificationChannelConfig

_firebase_apps = {}  # cache per store


def get_firebase_app(store):
    import json
    import firebase_admin
    from firebase_admin import credentials

    if store.id in _firebase_apps:
        return _firebase_apps[store.id]

    config = NotificationChannelConfig.objects.filter(
        store=store,
        channel="PUSH",
        is_active=True
    ).first()

    if not config or not config.fcm_server_key:
        raise ValueError("FCM credentials not configured for this store")

    cred_dict = json.loads(config.fcm_server_key)

    cred = credentials.Certificate(cred_dict)

    app = firebase_admin.initialize_app(
        cred,
        name=f"store_{store.id}"
    )

    _firebase_apps[store.id] = app
    return app


def send_push_notification(store, token, title, body, data=None):
    print(" send_push_notification called")
    print(" Store ID:", store.id)
    print(" Token:", token)
    print(" Title:", title)
    print(" Body:", body)
    print(" Data:", data)

    app = get_firebase_app(store)

    print(" Creating Firebase message")

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data=data or {},
        token=token
    )

    print(" Sending push notification via Firebase")

    try:
        response = messaging.send(message, app=app)
        print(" Push notification sent successfully")
        print(" Firebase response:", response)
        return response
    except Exception as e:
        print(" ERROR sending push notification:", str(e))
        raise