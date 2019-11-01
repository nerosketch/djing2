from .f601 import register_onu as register_f601_onu, remove_from_olt as remove_from_olt_f601
from .f660 import register_onu as register_f660_onu
from .base import (
    ZteOltConsoleError, OnuZteRegisterError,
    ZTEFiberIsFull, ZteOltLoginFailed, ExpectValidationError
)

__all__ = (
    'ZteOltConsoleError', 'OnuZteRegisterError', 'ZTEFiberIsFull',
    'ZteOltLoginFailed', 'ExpectValidationError', 'register_f601_onu',
    'register_f660_onu', 'remove_from_olt_f601'
)
