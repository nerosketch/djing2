from typing import Tuple, Optional
from django.db import models
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from djing2.lib import macbin2str, safe_int


def parse_opt82(remote_id: bytes, circuit_id: bytes) -> Tuple[Optional[str], int]:
    # 'remote_id': '0x000600ad24d0c544', 'circuit_id': '0x000400020002'
    mac, port = None, 0
    remote_id, circuit_id = bytes(remote_id), bytes(circuit_id)
    if circuit_id.startswith(b'ZTE'):
        mac = remote_id.decode()
    else:
        try:
            port = safe_int(circuit_id[-1:][0])
        except IndexError:
            port = 0
        if len(remote_id) >= 6:
            mac = macbin2str(remote_id[-6:])
    return mac, port


def _human_readable_int(num: int) -> str:
    decs = (
        (10 ** 12, 't'),
        (10 ** 9, 'g'),
        (10 ** 6, 'm'),
        (10 ** 3, 'k'),
    )
    for dec, pref in decs:
        if num >= dec:
            num -= dec
            return f'{num}{pref}'
    return str(num)


class UserSessionManager(models.Manager):
    def create_or_update_session(self, session_id, ):
        pass


class UserSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    assign_time = models.DateTimeField(auto_now_add=True, help_text=_('Time when session assigned first time'))
    last_event_time = models.DateTimeField(_('Last update time'))
    radius_username = models.CharField(_('User-Name av pair from radius'), max_length=32)
    framed_ip_addr = models.IPAddressField(_('Framed-IP-Address'))
    session_id = models.UUIDField(blank=True, null=True, default=None, unique=True)
    session_duration = models.DurationField(_('most often this is Acct-Session-Time av pair'), blank=True, null=True, default=None)
    input_octets = models.PositiveIntegerField(default=0)
    output_octets = models.PositiveIntegerField(default=0)
    input_packets = models.PositiveIntegerField(default=0)
    output_packets = models.PositiveIntegerField(default=0)
    closed = models.BooleanField(_('Is session finished'), default=False)

    objects = UserSessionManager()

    @property
    def h_input_octets(self):
        return _human_readable_int(self.input_octets)

    @property
    def h_output_octets(self):
        return _human_readable_int(self.output_octets)

    @property
    def h_input_packets(self):
        return _human_readable_int(self.input_packets)

    @property
    def h_output_packets(self):
        return _human_readable_int(self.output_packets)

    class Meta:
        db_table = 'user_session'


# CREATE UNIQUE INDEX usrses_uid_uni_idx ON user_session (session_id)
# WHERE session_id IS NOT NULL;
