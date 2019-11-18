from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from djing2.lib.auth_backends import _get_right_user


class CustomTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        token_model = self.get_model()
        try:
            token = token_model.objects.select_related('user').get(key=key)
        except token_model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return _get_right_user(token.user), token
