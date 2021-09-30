from django.db import models
from django.utils.translation import gettext_lazy as _
from viberbot import Api, BotConfiguration
from viberbot.api.messages.message import Message

from messenger.models.base_messenger import MessengerModel, MessengerSubscriberModel
from profiles.models import UserProfile

from rest_framework import status
from viberbot.api.messages import TextMessage, ContactMessage, KeyboardMessage
from viberbot.api.user_profile import UserProfile as ViberUserProfile
from viberbot.api.viber_requests import (
    ViberMessageRequest,
    ViberSubscribedRequest,
    ViberFailedRequest,
    ViberUnsubscribedRequest,
)


TYPE_NAME = 'viber'
_viber_cache = None


class ViberMessengerModel(MessengerModel):
    avatar = models.ImageField(_("Avatar"), upload_to="viber_avatar", null=True)

    def get_viber(self):
        global _viber_cache
        if _viber_cache is None:
            _viber_cache = Api(
                BotConfiguration(name=str(self.title), avatar=self.avatar.url, auth_token=str(self.token))
            )
        return _viber_cache

    def send_message_to_acc(self, to: UserProfile, msg: str):
        try:
            viber = self.get_viber()
            vs = ViberMessengerSubscriberModel.objects.get(account=to)
            viber.send_messages(str(vs.uid), TextMessage(text=msg))
        except ViberMessengerSubscriberModel.DoesNotExist:
            pass

    def send_message(self, text: str, uid=None, *args, **kwargs):
        viber = self.get_viber()
        viber.send_messages(uid, TextMessage(text=text))

    def send_message_broadcast(self, text: str, profile_ids=None):
        subscribers = ViberMessengerSubscriberModel.objects.select_related('messenger').filter(
            messenger=self
        )
        if profile_ids is not None:
            subscribers = subscribers.filter(
                account__id__in=profile_ids
            )
        for subs in subscribers.iterator():
            self.send_message(text=text, uid=subs.uid)

    def send_message_to_id(self, subscriber_id: str, msg):
        viber = self.get_viber()
        if issubclass(msg.__class__, Message):
            viber.send_messages(subscriber_id, msg)
        else:
            viber.send_messages(subscriber_id, TextMessage(text=msg))

    def send_webhook(self):
        public_url = self.get_webhook_url()
        viber = self.get_viber()
        viber.set_webhook(public_url, ["failed", "subscribed", "unsubscribed", "conversation_started"])

    def stop_webhook(self):
        viber = self.get_viber()
        viber.unset_webhook()

    def get_bot_url(self):
        return f"viber://pa?chatURI={self.title}"

    def inbox_data(self, request):
        viber = self.get_viber()
        if not viber.verify_signature(request.body, request.META.get("HTTP_X_VIBER_CONTENT_SIGNATURE")):
            return None, status.HTTP_403_FORBIDDEN

        vr = viber.parse_request(request.body)
        if isinstance(vr, ViberMessageRequest):
            in_msg = vr.message
            if isinstance(in_msg, ContactMessage):
                self._inbox_contact(in_msg, vr.sender)
            self._make_subscriber(vr.sender)
        elif isinstance(vr, ViberSubscribedRequest):
            self._make_subscriber(vr.user)
        elif isinstance(vr, ViberFailedRequest):
            print(f"client failed receiving message. failure: {vr}")
        elif isinstance(vr, ViberUnsubscribedRequest):
            ViberMessengerSubscriberModel.objects.filter(uid=vr.user_id).delete()
        return None

    def _make_subscriber(self, viber_user_profile: ViberUserProfile):
        subscriber, created = ViberMessengerSubscriberModel.objects.get_or_create(
            uid=viber_user_profile.id,
            defaults={
                'name': viber_user_profile.name,
                'avatar': viber_user_profile.avatar
            }
        )
        if created:
            msg = KeyboardMessage(keyboard={
                'Type': 'keyboard',
                'DefaultHeight': True,
                'Buttons': ({
                                'ActionType': 'share-phone',
                                'ActionBody': 'reply to me',
                                "Text": _('My telephone number'),
                                "TextSize": "medium"
                            },)
            }, min_api_version=3)
            self.send_message_to_id(viber_user_profile.id, msg)
        return subscriber, created

    def _inbox_contact(self, msg, sender: ViberUserProfile):
        tel = msg.contact.phone_number
        accs = UserProfile.objects.filter(telephone__icontains=tel)
        if accs.exists():
            subs = ViberMessengerSubscriberModel.objects.filter(uid=sender.id)
            subs_len = subs.count()
            if subs_len > 0:
                first_sub = subs.first()
                if subs_len > 1:
                    ViberMessengerSubscriberModel.objects.exclude(pk=first_sub.pk).delete()
                first_acc = accs.first()
                first_sub.account = first_acc
                first_sub.name = first_acc.get_full_name()
                first_sub.save(update_fields=('account', 'name'))
                self.send_message_to_acc(first_acc, _(
                    'Your account is attached. Now you will be receive notifications from billing'
                ))
        else:
            self.send_message_to_id(sender.id, _(
                'Telephone not found, please specify telephone number in account in billing'
            ))

    def __str__(self):
        return self.title

    class Meta:
        db_table = "messengers_viber"
        verbose_name = "Viber"
        ordering = ("title",)


MessengerModel.add_child_classes(
    messenger_type_name=TYPE_NAME,
    unique_int=2,
    messenger_class=ViberMessengerModel
)


class ViberMessengerSubscriberModel(MessengerSubscriberModel):
    uid = models.CharField(_("User unique id"), max_length=32)
    messenger = models.ForeignKey(ViberMessengerModel, on_delete=models.CASCADE)

    def send_message(self, text: str):
        return self.messenger.send_message(
            text=text,
            chat_id=self.chat_id,
        )

    class Meta:
        db_table = "messengers_viber_subscriber"
        verbose_name = _("Subscriber")
        verbose_name_plural = _("Subscribers")
        ordering = ("name",)
