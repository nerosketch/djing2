from ipaddress import ip_address, AddressValueError
from typing import Optional

from django.contrib.auth.backends import ModelBackend

from customers.models import Customer
from networks.models import CustomerIpLeaseModel
from profiles.models import BaseAccount, UserProfile


def get_right_user(base_user: BaseAccount) -> Optional[BaseAccount]:
    try:
        if base_user.is_staff:
            amodel = UserProfile
        else:
            amodel = Customer
        return amodel._default_manager.get(pk=base_user.pk)
    except (BaseAccount.DoesNotExist, UserProfile.DoesNotExist, Customer.DoesNotExist):
        return None


class DjingAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(BaseAccount.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            user = BaseAccount._default_manager.get_by_natural_key(username)
        except BaseAccount.DoesNotExist:
            return None
        else:
            if not user.check_password(password):
                return None
            if not self.user_can_authenticate(user):
                return None
            if user.is_staff:
                auser = UserProfile.objects.get_by_natural_key(username)
            else:
                auser = Customer.objects.get_by_natural_key(username)
            if not request or not request.META:
                return auser
            auser.auth_log(
                user_agent=request.META.get("HTTP_USER_AGENT"),
                remote_ip=request.META.get("HTTP_X_REAL_IP")
            )
            return auser

    def get_user(self, user_id) -> Optional[BaseAccount]:
        user = BaseAccount._default_manager.get(pk=user_id)
        return get_right_user(user)


class LocationAuthBackend(DjingAuthBackend):
    def authenticate(self, request, byip=None, **kwargs):
        if byip is None:
            return
        try:
            remote_ip = request.META.get(
                "HTTP_X_REAL_IP",
                request.META.get('REMOTE_ADDR')
            )
            if not remote_ip:
                return
            remote_ip = ip_address(remote_ip)
            ip_users = CustomerIpLeaseModel.objects.filter(ip_address=str(remote_ip)).select_related('customer')
            if ip_users.exists():
                ip_user = ip_users.first()
                if ip_user and ip_user.customer:
                    if self.user_can_authenticate(ip_user.customer):
                        return ip_user.customer
        except AddressValueError:
            return None
