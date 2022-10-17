from django.utils.translation import gettext
from fastapi import Depends, HTTPException
from profiles.models import BaseAccount
from starlette import status
from .auth import is_admin_auth_dependency


PERMISSION_DENIED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail=gettext('Permission denied, check your rights.')
)


def check_perm(user: BaseAccount, perm_codename: str, raise_exception=True) -> bool:
    has_perm = user.has_perm(perm=perm_codename)
    if raise_exception and not has_perm:
        raise PERMISSION_DENIED
    return has_perm


def permission_check_dependency(perm_codename: str):
    def _permission_check_dep(is_auth=Depends(is_admin_auth_dependency)) -> BaseAccount:
        user, token = is_auth
        check_perm(user, perm_codename)
        return user

    return _permission_check_dep
