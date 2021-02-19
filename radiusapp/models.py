from datetime import timedelta

from django.db import models, connection
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from djing2.lib import safe_int


def _human_readable_int(num: int) -> str:
    decs = (
        (10 ** 12, 'T'),
        (10 ** 9, 'G'),
        (10 ** 6, 'M'),
        (10 ** 3, 'K'),
    )
    for dec, pref in decs:
        if num >= dec:
            num = round(num / dec, 2)
            return f'{num} {pref}b'
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

    @staticmethod
    def fetch_subscriber_lease(customer_mac: str, device_mac: str, device_port: int, is_dynamic: bool, vid: int):
        with connection.cursor() as cur:
            # v_mac_addr, v_dev_mac, v_dev_port, v_is_dynamic, v_vid
            cur.execute("select * from fetch_subscriber_lease"
                        "(%s::macaddr, %s::macaddr, %s::smallint, %s::boolean, %s::smallint)",
                        [customer_mac, device_mac, device_port, is_dynamic, vid])
            res = cur.fetchone()
        lease_id, ip_addr, pool_id, lease_time, customer_mac, customer_id, is_dynamic, is_assigned = res
        if lease_id is None:
            return
        return {
            'id': lease_id,
            'ip_addr': ip_addr,
            'pool_id': pool_id,
            'lease_time': lease_time,
            'customer_mac': customer_mac,
            'customer_id': customer_id,
            'is_dynamic': is_dynamic,
            'is_assigned': is_assigned
        }


class UserSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    assign_time = models.DateTimeField(auto_now_add=True, help_text=_('Time when session assigned first time'))
    last_event_time = models.DateTimeField(_('Last update time'))
    radius_username = models.CharField(_('User-Name av pair from radius'), max_length=128)
    framed_ip_addr = models.GenericIPAddressField(_('Framed-IP-Address'))
    session_id = models.UUIDField(_('Unique session id'))
    session_duration = models.DurationField(_('most often this is Acct-Session-Time av pair'), blank=True, null=True,
                                            default=None)
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
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
