import abc
from typing import Optional, Tuple


class IVendorSpecific(abc.ABC):
    @property
    @abc.abstractmethod
    def vendor(self):
        raise NotImplementedError

    @staticmethod
    def get_rad_val(data, v: str):
        k = data.get(v)
        if k:
            k = k.get('value')
            if k:
                return k[0]

    @abc.abstractmethod
    def parse_option82(self, data) -> Optional[Tuple[str, str]]:
        raise NotImplementedError
