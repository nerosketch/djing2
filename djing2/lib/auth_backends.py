from ipaddress import ip_address, AddressValueError

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from customers.models import Customer
from profiles.models import BaseAccount


UserProfile = get_user_model()


class DjingAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(BaseAccount.USERNAME_FIELD)
        try:
            user = BaseAccount._default_manager.get_by_natural_key(username)
        except BaseAccount.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            BaseAccount().set_password(password)
        else:
            if user.check_password(password):
                if user.is_staff:
                    auser = UserProfile.objects.get_by_natural_key(username)
                else:
                    auser = Customer.objects.get_by_natural_key(username)
                if self.user_can_authenticate(auser):
                    return auser

    def get_user(self, user_id):
        try:
            user = BaseAccount._default_manager.get(pk=user_id)
            if user.is_staff:
                amodel = UserProfile
            else:
                amodel = Customer
            return amodel._default_manager.get(pk=user_id)
        except (BaseAccount.DoesNotExist, UserProfile.DoesNotExist, Customer.DoesNotExist):
            return None


class LocationAuthBackend(DjingAuthBackend):
    def authenticate(self, request, **kwargs):
        try:
            remote_ip = ip_address(request.META.get('REMOTE_ADDR'))
            user = Customer.objects.filter(
                ip_address=str(remote_ip),
                is_active=True
            ).first()
            if user is None:
                return None
            if self.user_can_authenticate(user):
                return user
        except AddressValueError:
            return None
