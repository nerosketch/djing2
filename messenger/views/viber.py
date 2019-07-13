from django.contrib.auth import get_user_model
from django.utils.translation import gettext

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from viberbot.api.messages import ContactMessage, KeyboardMessage
from viberbot.api.user_profile import UserProfile as ViberUserProfile
from viberbot.api.viber_requests import (
    ViberMessageRequest, ViberSubscribedRequest,
    ViberFailedRequest, ViberUnsubscribedRequest
)
from djing2.viewsets import DjingModelViewSet
from messenger.models import viber as models
from messenger.serializers import viber as serializers


UserProfile = get_user_model()


class ViberMessengerModelViewSet(DjingModelViewSet):
    queryset = models.ViberMessenger.objects.all()
    serializer_class = serializers.ViberMessengerModelSerializer


class ViberMessageModelViewSet(DjingModelViewSet):
    queryset = models.ViberMessage.objects.all()
    serializer_class = serializers.ViberMessageModelSerializer


class ViberSubscriberModelViewSet(DjingModelViewSet):
    queryset = models.ViberSubscriber.objects.all()
    serializer_class = serializers.ViberSubscriberModelSerializer


class ListenViberView(GenericAPIView):
    queryset = models.ViberMessenger.objects.all()
    serializer_class = serializers.ViberMessengerModelSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'boturl'
    http_method_names = 'post',

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        self.object = obj

        viber = obj.get_viber()
        if not viber.verify_signature(request.body, request.META.get('HTTP_X_VIBER_CONTENT_SIGNATURE')):
            return Response(status=status.HTTP_403_FORBIDDEN)

        vr = viber.parse_request(request.body)
        if isinstance(vr, ViberMessageRequest):
            in_msg = vr.message
            if isinstance(in_msg, ContactMessage):
                self.inbox_contact(in_msg, vr.sender)
            subscriber, created = self.make_subscriber(vr.sender)
            if not created:
                models.ViberMessage.objects.create(
                    msg=vr.message,
                    sender=vr.sender.id,
                    messenger=obj,
                    subscriber=subscriber
                )
        elif isinstance(vr, ViberSubscribedRequest):
            self.make_subscriber(vr.user)
        elif isinstance(vr, ViberFailedRequest):
            print("client failed receiving message. failure: {0}".format(vr))
        elif isinstance(vr, ViberUnsubscribedRequest):
            models.ViberSubscriber.objects.filter(
                uid=vr.user_id
            ).delete()
        return Response(status=status.HTTP_200_OK)

    def make_subscriber(self, viber_user_profile: ViberUserProfile):
        subscriber, created = models.ViberSubscriber.objects.get_or_create(
            uid=viber_user_profile.id,
            defaults={
                'name': viber_user_profile.name,
                'avatar': viber_user_profile.avatar
            }
        )
        if created and hasattr(self, 'object'):
            msg = KeyboardMessage(keyboard={
                'Type': 'keyboard',
                'DefaultHeight': True,
                'Buttons': ({
                    'ActionType': 'share-phone',
                    'ActionBody': 'reply to me',
                    "Text": gettext('My telephone number'),
                    "TextSize": "medium"
                },)
            }, min_api_version=3)
            viber = self.object
            viber.send_message_to_id(viber_user_profile.id, msg)
        return subscriber, created

    def inbox_contact(self, msg, sender: ViberUserProfile):
        tel = msg.contact.phone_number
        accs = UserProfile.objects.filter(telephone__icontains=tel)
        viber = self.object
        if accs.exists():
            first_acc = accs.first()
            subs = models.ViberSubscriber.objects.filter(uid=sender.id)
            subs_len = subs.count()
            if subs_len > 0:
                first_sub = subs.first()
                if subs_len > 1:
                    models.ViberSubscriber.objects.exclude(pk=first_sub.pk).delete()
                first_sub.account = first_acc
                first_sub.name = first_acc.get_full_name()
                first_sub.save(update_fields=('account', 'name'))
                viber.send_message_to_acc(first_acc, gettext(
                    'Your account is attached. Now you will be receive notifications from billing'
                ))
        else:
            viber.send_message_to_id(sender.id, gettext(
                'Telephone not found, please specify telephone number in account in billing'
            ))
