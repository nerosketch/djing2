import importlib
import inspect
import os
# from .telegram import TelegramMessenger
# from .viber import ViberMessenger
from .base import BaseMessengerInterface


def _read_mods():
    fls = set(os.listdir(os.path.realpath(os.path.dirname(__file__))))
    fls -= {'__pycache__', 'base.py', '__init__.py'}
    return list(fls)


def _import_mods(mod_name: str):
    mod = importlib.import_module(name='.'.join(('messenger', 'messenger_implementation', mod_name)))
    membs = inspect.getmembers(mod)
    for mn, mo in membs:
        try:
            moo = getattr(mo, mn)

            s = issubclass(mo.__class__, BaseMessengerInterface)
            print(mn, mo, moo, s)
        except AttributeError:
            pass
    memb = [mobj for mname, mobj in membs if issubclass(mobj.__class__, BaseMessengerInterface)]
    print('\tMEMBERS', memb)


MODS = _import_mods('viber')


MOD_NAMES = _read_mods()


__all__ = ['MODS'] + MOD_NAMES
