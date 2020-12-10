from datetime import timedelta
from typing import Tuple, Optional

from django.db import models, connection
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
    @staticmethod
    def create_or_update_session(session_id: str, v_ip_addr: str, v_dev_mac: str,
                                 v_dev_port: int, v_sess_time: timedelta, v_uname: str,
                                 v_inp_oct: int, v_out_oct: int,
                                 v_in_pkt: int, v_out_pkt: int,
                                 v_is_stop: bool = False) -> bool:
        if not all([session_id, v_ip_addr, v_dev_mac]):
            return False
        session_id = str(session_id)
        v_ip_addr = str(v_ip_addr)
        v_dev_mac = str(v_dev_mac)
        v_dev_port = safe_int(v_dev_port)
        v_uname = str(v_uname)
        v_in_pkt = safe_int(v_in_pkt)
        v_out_pkt = safe_int(v_out_pkt)
        v_inp_oct = safe_int(v_inp_oct)
        v_out_oct = safe_int(v_out_oct)
        v_is_stop = bool(v_is_stop)
        if not isinstance(v_sess_time, timedelta):
            v_sess_time = timedelta(seconds=int(v_sess_time))
        with connection.cursor() as cur:
            cur.execute("select * from create_or_update_radius_session"
                        "(%s::uuid, %s::inet, %s::macaddr, %s::smallint, %s::integer, "
                        "%s::varchar(32), %s::integer, %s::integer, %s::integer, "
                        "%s::integer, %s::boolean)",
                        [session_id, v_ip_addr, v_dev_mac,
                         v_dev_port, v_sess_time.total_seconds(), v_uname,
                         v_inp_oct, v_out_oct,
                         v_in_pkt, v_out_pkt,
                         v_is_stop])
            is_created = cur.fetchone()[0]
        # print('is_created:', is_created)
        return is_created


class UserSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    assign_time = models.DateTimeField(auto_now_add=True, help_text=_('Time when session assigned first time'))
    last_event_time = models.DateTimeField(_('Last update time'))
    radius_username = models.CharField(_('User-Name av pair from radius'), max_length=32)
    framed_ip_addr = models.GenericIPAddressField(_('Framed-IP-Address'))
    session_id = models.UUIDField(_('Unique session id'))
    session_duration = models.DurationField(_('most often this is Acct-Session-Time av pair'), blank=True, null=True,
                                            default=None)
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
