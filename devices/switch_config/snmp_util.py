from abc import ABC
from typing import Generator, Optional
from django.utils.translation import gettext
from easysnmp import Session
from .base import DeviceImplementationError


class SNMPBaseWorker(ABC):
    ses = None

    def __init__(self, ip: Optional[str], community='public', ver=2):
        if ip is None or ip == '':
            raise DeviceImplementationError(gettext('Ip address is required'))
        self._ip = ip
        self._community = community
        self._ver = ver

    def start_ses(self):
        if self.ses is None:
            self.ses = Session(
                hostname=self._ip, community=self._community,
                version=self._ver
            )

    def set_int_value(self, oid: str, value):
        self.start_ses()
        return self.ses.set(oid, value, 'i')

    def get_list(self, oid) -> Generator:
        self.start_ses()
        for v in self.ses.walk(oid):
            yield v.value

    def get_list_keyval(self, oid) -> Generator:
        self.start_ses()
        for v in self.ses.walk(oid):
            snmpnum = v.oid.split('.')[-1:]
            yield v.value, snmpnum[0] if len(snmpnum) > 0 else None

    def get_item(self, oid):
        self.start_ses()
        v = self.ses.get(oid).value
        if v != 'NOSUCHINSTANCE':
            return v
