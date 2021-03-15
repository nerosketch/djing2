from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_delete
# from django.utils.translation import gettext_lazy as _
# from rest_framework.exceptions import APIException
# from rest_framework import status
from networks.models import CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession


# class FailedSessionStop(APIException):
#     status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     default_detail = _('Failed to stop session')


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def try_stop_session_too(sender, instance, **kwargs):
    sess = CustomerRadiusSession.objects.filter(ip_lease=instance).first()
    if sess:
        sess.finish_session()
        # if not sess.finish_session():
            # raise FailedSessionStop
