from datetime import datetime
from typing import Optional

from django.db import models, connection
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from networks.models import CustomerIpLeaseModel, NetworkIpPoolKind


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


class FetchSubscriberLeaseResponse(object):
    lease_id = 0
    ip_addr = ''
    pool_id = 0
    lease_time = 0
    customer_mac = ''
    customer_id = 0
    is_dynamic = None
    is_assigned = None

    def __init__(self, lease_id=0, ip_addr='', pool_id=0, lease_time=0,
                 customer_mac='', customer_id=0, is_dynamic=None, is_assigned=None):
        self.lease_id = lease_id
        self.ip_addr = ip_addr
        self.pool_id = pool_id
        self.lease_time = lease_time
        self.customer_mac = customer_mac
        self.customer_id = customer_id
        self.is_dynamic = is_dynamic
        self.is_assigned = is_assigned


class CustomerRadiusSessionManager(models.Manager):
    # @staticmethod
    # def create_or_update_session(session_id: str, lease_id: int, dev_mac: str,
    #                              dev_port: int, sess_time: timedelta, uname: str,
    #                              inp_oct: int, out_oct: int,
    #                              in_pkt: int, out_pkt: int,
    #                              is_stop: bool = False) -> bool:
    #     if not all([session_id, lease_id, dev_mac]):
    #         return False
    #     session_id = str(session_id)
    #     lease_id = safe_int(lease_id)
    #     dev_mac = str(dev_mac)
    #     dev_port = safe_int(dev_port)
    #     uname = str(uname)
    #     in_pkt = safe_int(in_pkt)
    #     out_pkt = safe_int(out_pkt)
    #     inp_oct = safe_int(inp_oct)
    #     out_oct = safe_int(out_oct)
    #     is_stop = bool(is_stop)
    #     if not isinstance(sess_time, timedelta):
    #         v_sess_time = timedelta(seconds=int(sess_time))
    #     with connection.cursor() as cur:
    #         cur.execute("select * from create_or_update_radius_session"
    #                     "(%s::uuid, %s::inet, %s::macaddr, %s::smallint, %s::integer, "
    #                     "%s::character varying, %s::integer, %s::integer, %s::integer, "
    #                     "%s::integer, %s::boolean)",
    #                     [session_id, lease_id, dev_mac,
    #                      dev_port, sess_time.total_seconds(), uname,
    #                      inp_oct, out_oct,
    #                      in_pkt, out_pkt,
    #                      is_stop])
    #         is_created = cur.fetchone()[0]
    #     return is_created

    @staticmethod
    def fetch_subscriber_lease(
            customer_mac: str, customer_id: Optional[int],
            customer_group: Optional[int], is_dynamic: bool,
            vid: int, pool_kind: NetworkIpPoolKind) -> Optional[FetchSubscriberLeaseResponse]:
        if not isinstance(pool_kind, NetworkIpPoolKind):
            raise TypeError('pool_kind must be choice from NetworkIpPoolKind')
        with connection.cursor() as cur:
            cur.execute("select * from fetch_subscriber_lease"
                        "(%s::macaddr, %s, %s, %s::boolean, %s::smallint, %s::smallint)",
                        [customer_mac, customer_id, customer_group, is_dynamic, vid, pool_kind.value])
            res = cur.fetchone()
        lease_id, ip_addr, pool_id, lease_time, customer_mac, customer_id, is_dynamic, is_assigned = res
        if lease_id is None:
            return
        return FetchSubscriberLeaseResponse(
            lease_id=lease_id,
            ip_addr=ip_addr,
            pool_id=pool_id,
            lease_time=lease_time,
            customer_mac=customer_mac,
            customer_id=customer_id,
            is_dynamic=is_dynamic,
            is_assigned=is_assigned
        )

    def assign_guest_lease(self, radius_uname: str, customer_mac: str,  session_id: str):
        # Тут создаём сессию и сразу выделяем гостевой ip для этой сессии.
        # Гостевой ip можно сделать из обычного, если нет пользователя.
        r = self.fetch_subscriber_lease(
            customer_mac=customer_mac,
            customer_id=None,
            customer_group=None,
            is_dynamic=True,
            vid=1,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_GUEST
        )
        if not r:
            return None
        new_lease = self.create(
            customer=None,
            last_event_time=datetime.now(),
            radius_username=radius_uname,
            ip_lease_id=r.lease_id,
            session_id=session_id
        )
        return new_lease


class CustomerRadiusSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, default=None, null=True)
    assign_time = models.DateTimeField(auto_now_add=True, help_text=_('Time when session assigned first time'))
    last_event_time = models.DateTimeField(_('Last update time'))
    radius_username = models.CharField(_('User-Name av pair from radius'), max_length=128)
    ip_lease = models.ForeignKey(CustomerIpLeaseModel, verbose_name=_('Ip lease'), on_delete=models.CASCADE)
    session_id = models.UUIDField(_('Unique session id'))
    session_duration = models.DurationField(_('most often this is Acct-Session-Time av pair'), blank=True, null=True,
                                            default=None)
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
    closed = models.BooleanField(_('Is session finished'), default=False)

    objects = CustomerRadiusSessionManager()

    # def finish_session(self) -> bool:
    #     uname = str(self.radius_username).encode()
    #     uname = uname.replace(b'"', b'')
    #     uname = uname.replace(b"'", b'')
    #     r = subprocess.run(
    #         ['radclient', '-qx', '127.0.0.1:3799', 'disconnect', 'secretradiuspassword'],
    #         input=b'User-Name="%s"' % uname)
    #     return r.returncode == 0

    @property
    def is_guest_session(self) -> bool:
        return self.customer is None

    def h_input_octets(self):
        return _human_readable_int(self.input_octets)

    def h_output_octets(self):
        return _human_readable_int(self.output_octets)

    def h_input_packets(self):
        return _human_readable_int(self.input_packets)

    def h_output_packets(self):
        return _human_readable_int(self.output_packets)

    def delete(self, using=None, keep_parents=False):
        # TODO: Move it to db trigger
        lease = self.ip_lease
        if lease:
            CustomerIpLeaseModel.objects.filter(pk=lease.pk).delete()
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        db_table = 'radius_customer_session'
