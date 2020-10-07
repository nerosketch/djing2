from messenger.messenger_implementation.base import BaseMessengerInterface
from django.conf import settings
from viberbot import Api, BotConfiguration
from profiles.models import UserProfile
from viberbot.api.messages import TextMessage
from viberbot.api.messages.message import Message
from django.shortcuts import resolve_url
from urllib.parse import urljoin
from viberbot.api.messages import ContactMessage, KeyboardMessage
from viberbot.api.user_profile import UserProfile as ViberUserProfile
from viberbot.api.viber_requests import (
    ViberMessageRequest, ViberSubscribedRequest,
    ViberFailedRequest, ViberUnsubscribedRequest
)


class ViberMessenger(BaseMessengerInterface):

    def get_viber(self):
        if self._viber_cache is None:
            self._viber_cache = Api(BotConfiguration(
                name=str(self.slug),
                avatar=self.avatar.url,
                auth_token=str(self.token)
            ))
        return self._viber_cache

    def send_webhook(self):
        pub_url = getattr(settings, 'VIBER_BOT_PUBLIC_URL')
        listen_url = resolve_url('messenger:listen_viber_bot', self.slug)
        public_url = urljoin(pub_url, listen_url)
        viber = self.get_viber()
        viber.set_webhook(public_url, ['failed', 'subscribed', 'unsubscribed', 'conversation_started'])

    def remove_webhook(self):
        pass

    def send_message_to_accs(self, receivers, msg_text: str):
        pass

    def send_message(self, msg_text: str):
        pass

    def send_message_to_acc(self, to: UserProfile, msg):
        pass
        # try:
        #     viber = self.get_viber()
        #     vs = to.vibersubscriber
        #     if issubclass(msg.__class__, Message):
        #         viber.send_messages(str(vs.uid), msg)
        #     else:
        #         viber.send_messages(str(vs.uid), TextMessage(text=msg))
        # except ViberSubscriber.DoesNotExist:
        #     pass

    def send_message_to_accs(self, receivers, msg_text: str):
        """
        :param receivers: QuerySet of profiles.UserProfile
        :param msg_text: text message
        :return: nothing
        """
        pass
        # viber = self.get_viber()
        # msg = TextMessage(text=msg_text)
        # for vs in ViberSubscriber.objects.filter(account__in=receivers).iterator():
        #     viber.send_messages(str(vs.uid), msg)

    def send_message_to_id(self, subscriber_id: str, msg):
        viber = self.get_viber()
        if issubclass(msg.__class__, Message):
            viber.send_messages(subscriber_id, msg)
        else:
            viber.send_messages(subscriber_id, TextMessage(text=msg))

    def inbox_data(self, data):
        # obj = self.get_object()
        # self.object = obj
        #
        # viber = obj.get_viber()
        # if not viber.verify_signature(request.body, request.META.get('HTTP_X_VIBER_CONTENT_SIGNATURE')):
        #     return Response(status=status.HTTP_403_FORBIDDEN)
        #
        # vr = viber.parse_request(request.body)
        # if isinstance(vr, ViberMessageRequest):
        #     in_msg = vr.message
        #     if isinstance(in_msg, ContactMessage):
        #         self.inbox_contact(in_msg, vr.sender)
        #     subscriber, created = self.make_subscriber(vr.sender)
        #     if not created:
        #         models.ViberMessage.objects.create(
        #             msg=vr.message,
        #             sender=vr.sender.id,
        #             messenger=obj,
        #             subscriber=subscriber
        #         )
        # elif isinstance(vr, ViberSubscribedRequest):
        #     self.make_subscriber(vr.user)
        # elif isinstance(vr, ViberFailedRequest):
        #     print("client failed receiving message. failure: {0}".format(vr))
        # elif isinstance(vr, ViberUnsubscribedRequest):
        #     models.ViberSubscriber.objects.filter(
        #         uid=vr.user_id
        #     ).delete()
        # return Response(status=status.HTTP_200_OK)
        pass

    def make_subscriber(self, viber_user_profile: ViberUserProfile):
        # subscriber, created = models.ViberSubscriber.objects.get_or_create(
        #     uid=viber_user_profile.id,
        #     defaults={
        #         'name': viber_user_profile.name,
        #         'avatar': viber_user_profile.avatar
        #     }
        # )
        # if created and hasattr(self, 'object'):
        #     msg = KeyboardMessage(keyboard={
        #         'Type': 'keyboard',
        #         'DefaultHeight': True,
        #         'Buttons': ({
        #                         'ActionType': 'share-phone',
        #                         'ActionBody': 'reply to me',
        #                         "Text": gettext('My telephone number'),
        #                         "TextSize": "medium"
        #                     },)
        #     }, min_api_version=3)
        #     viber = self.object
        #     viber.send_message_to_id(viber_user_profile.id, msg)
        # return subscriber, created
        pass

    def inbox_contact(self, msg, sender: ViberUserProfile):
        # tel = msg.contact.phone_number
        # accs = UserProfile.objects.filter(telephone__icontains=tel)
        # viber = self.object
        # if accs.exists():
        #     first_acc = accs.first()
        #     subs = models.ViberSubscriber.objects.filter(uid=sender.id)
        #     subs_len = subs.count()
        #     if subs_len > 0:
        #         first_sub = subs.first()
        #         if subs_len > 1:
        #             models.ViberSubscriber.objects.exclude(pk=first_sub.pk).delete()
        #         first_sub.account = first_acc
        #         first_sub.name = first_acc.get_full_name()
        #         first_sub.save(update_fields=('account', 'name'))
        #         viber.send_message_to_acc(first_acc, gettext(
        #             'Your account is attached. Now you will be receive notifications from billing'
        #         ))
        # else:
        #     viber.send_message_to_id(sender.id, gettext(
        #         'Telephone not found, please specify telephone number in account in billing'
        #     ))
        pass
