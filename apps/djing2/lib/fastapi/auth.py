import pickle

from django.conf import settings
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from profiles.models import BaseAccount
from starlette import status
from starlette.requests import Request
from django.utils.translation import gettext as _
from rest_framework.authtoken.models import Token
from djing2.lib.auth_backends import get_right_user
from djing2.lib.redis import redis_proxy
from djing2.lib import check_subnet


TOKEN_RESULT_TYPE = tuple[BaseAccount, str]
REDIS_AUTH_CACHE_TTL = getattr(settings, 'REDIS_AUTH_CACHE_TTL', 3600)


def get_token(token: str) -> Token:
    cashe_key = f'redis_user_token_{token}'
    data = redis_proxy.get(cashe_key)
    if data is not None:
        data = pickle.loads(data)
        return data
    token_instance = Token.objects.select_related("user").get(key=token)
    redis_proxy.set(cashe_key, pickle.dumps(token_instance), ex=int(REDIS_AUTH_CACHE_TTL))
    return token_instance


class TokenAPIKeyHeader(APIKeyHeader):
    def __call__(self, request: Request) -> TOKEN_RESULT_TYPE:
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
            token_instance = get_token(token)
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

        # TODO: Cash it
        user = get_right_user(token_instance.user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Failed to get concrete profile'
            )
        return user, token


token_auth_dep = TokenAPIKeyHeader(name='Authorization')

FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail='Forbidden'
)


def is_admin_auth_dependency(token_auth: TOKEN_RESULT_TYPE = Depends(token_auth_dep)) -> TOKEN_RESULT_TYPE:
    user, token = token_auth
    if not user.is_admin:
        raise FORBIDDEN
    return user, token


def is_customer_auth_dependency(token_auth: TOKEN_RESULT_TYPE = Depends(token_auth_dep)) -> BaseAccount:
    user, token = token_auth
    if user and not user.is_staff:
        return user
    raise FORBIDDEN


def is_superuser_auth_dependency(token_auth: TOKEN_RESULT_TYPE = Depends(token_auth_dep)) -> TOKEN_RESULT_TYPE:
    user, token = token_auth
    if not (user.is_admin and user.is_superuser):
        raise FORBIDDEN
    return user, token


def allowed_subnet_dependency(request: Request):
    try:
        check_subnet(request.headers)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err)
        )
