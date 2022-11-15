from typing import List, Optional
from messenger.models.base_messenger import get_messenger_model_info_generator


def send_messenger_broadcast_message_task(text: str, recipients: Optional[List[int]] = None):
    for type_name, messenger_uint, messenger_model_class in get_messenger_model_info_generator():
        for msg in messenger_model_class.objects.all():
            msg.send_message_broadcast(
                text=text,
                profile_ids=recipients
            )
