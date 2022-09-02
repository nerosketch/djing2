from typing import Tuple

from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from profiles.models import BaseAccount
from starlette import status
from starlette.requests import Request
from django.utils.translation import gettext as _
from rest_framework.authtoken.models import Token
from djing2.lib.auth_backends import get_right_user


TOKEN_API_RESULT_TYPE = Tuple[BaseAccount, str]


class TokenAPIKeyHeader(APIKeyHeader):
    def __call__(self, request: Request) -> TOKEN_API_RESULT_TYPE:
        token: str = request.headers.get(self.model.name)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        divided_auth = token.split(' ')
        if not divided_auth or divided_auth[0].lower() != 'token':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Bad auth'
            )
        if len(divided_auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=msg
            )
        elif len(divided_auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=msg
            )
        kw, token = divided_auth

        try:
            token_instance = Token.objects.select_related("user").get(key=token)
        except Token.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_("Invalid token.")
            ) from None

        if not token_instance.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_("User inactive or deleted.")
            )

        user = get_right_user(token_instance.user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Failed to get concrete profile'
            )
        return user, token


token_auth_dep = TokenAPIKeyHeader(name='Authorization')


def is_admin_auth_dependency(token_auth: TOKEN_API_RESULT_TYPE = Depends(token_auth_dep)) -> TOKEN_API_RESULT_TYPE:
    user, token = token_auth
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Forbidden'
        )
    return user, token
