from db.models import NotificationTemplate, NotificationChannelConfig
from utils.user import send_sms_to_mobile


def trigger_notification(store, event, context, recipient=None, email=None):

    templates = NotificationTemplate.objects.filter(
        store=store,
        event=event,
        is_active=True
    )

    for template in templates:

        config = NotificationChannelConfig.objects.filter(
            store=store,
            channel=template.channel,
            is_active=True
        ).first()

        if not config:
            continue

        if template.channel == "SMS" and recipient:
            var = context["var"]
            send_sms_to_mobile(var, recipient, config, template.template_id)

        elif template.channel == "WHATSAPP" and recipient:
            pass
            # send_whatsapp(config, recipient, message)

        elif template.channel == "EMAIL" and email:
            pass
            # send_email(config, email, title, message)
