from fastapi import Header, HTTPException
from fastapi.security import APIKeyHeader
from starlette import status
from starlette.requests import Request
from django.utils.translation import gettext as _
from rest_framework.authtoken.models import Token
from djing2.lib.auth_backends import _get_right_user


def_auth_hdr = Header(
    title="Authorization header with token",
    description="Contain auth token like: Authorization: Token ########################################",
    regex=r'^Token\ [0-9a-f]{40}$',
    example="Token 0000000000000000000000000000000000000000"
)

_keyword = 'Token'


class TokenAPIKeyHeader(APIKeyHeader):
    def __init__(self, auto_error: bool = True, *args, **kwargs):
        super(TokenAPIKeyHeader, self).__init__(
            auto_error=True,
            *args, **kwargs
        )

    def __call__(self, request: Request):
        token: str = request.headers.get(self.model.name)
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            else:
                return None

        divided_auth = token.split(' ')
        if not divided_auth or divided_auth[0].lower() != _keyword.lower():
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
            token = Token.objects.select_related("user").get(key=token)
        except Token.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_("Invalid token.")
            ) from None

        if not token.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_("User inactive or deleted.")
            )

        return _get_right_user(token.user), token
