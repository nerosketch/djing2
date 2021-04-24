import importlib
import inspect
import os
from .base import BaseMessengerInterface


def _import_mods(mod_name: str):
    viber = importlib.import_module(name="messenger.messenger_implementation.%s" % mod_name)

    def _pred(v):
        inspect.isclass(v) and issubclass(v, BaseMessengerInterface) and v is not BaseMessengerInterface

    membs = inspect.getmembers(viber, predicate=_pred)
    return membs


def _read_mods():
    fls = set(os.listdir(os.path.realpath(os.path.dirname(__file__))))
    fls -= {"__pycache__", "base.py", "__init__.py"}
    fls = [fl.split(".")[0] for fl in fls if fl.endswith(".py")]
    for fl in fls:
        membs = _import_mods(fl)
        yield from membs


MESSENGER_MAP = {mod_obj.data_value: mod_obj for mod_name, mod_obj in _read_mods()}


__all__ = ["MESSENGER_MAP", "BaseMessengerInterface"]
