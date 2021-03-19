"""radiusapp models file."""
import subprocess
from datetime import datetime
from typing import Optional

from django.conf import settings
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
    """Type for ip lease results."""

    lease_id = 0
    ip_addr = ''
    pool_id = 0
    lease_time = 0
    customer_mac = ''
    customer_id = 0
    is_dynamic = None
    is_assigned = None

    def __init__(self, lease_id=0, ip_addr='', pool_id=0, lease_time=0,
                 customer_mac='', customer_id=0, is_dynamic=None,
                 is_assigned=None):
        """Init fn.

        :param lease_id: number, CustomerIpLeaseModel instance id
        :param ip_addr: customer ip address
        :param pool_id: NetworkIpPool instance id
        :param lease_time: when lease assigned
        :param customer_mac: customer device mac address
        :param customer_id: customers.models.Customer instance id
        :param is_dynamic: if lease assigned dynamically or not
        :param is_assigned: is it new assignment or not
        """
        self.lease_id = lease_id
        self.ip_addr = ip_addr
        self.pool_id = pool_id
        self.lease_time = lease_time
        self.customer_mac = customer_mac
        self.customer_id = customer_id
        self.is_dynamic = is_dynamic
        self.is_assigned = is_assigned

    def __repr__(self):
        """Repr 4 this."""
        return "%s: <%s, %s, %s, %s, %s>" % (
            self.__class__.__name__,
            self.ip_addr,
            self.lease_time,
            self.customer_mac,
            self.is_dynamic,
            self.is_assigned
        )

    def __str__(self):
        """Str 4 this."""
        return self.__repr__()


class CustomerRadiusSessionManager(models.Manager):
    """Session manager 4 CustomerRadiusSession model."""

    @staticmethod
    def fetch_subscriber_lease(
            customer_mac: str, customer_id: Optional[int],
            customer_group: Optional[int], is_dynamic: bool,
            vid: Optional[int], pool_kind: NetworkIpPoolKind) -> Optional[
                FetchSubscriberLeaseResponse]:
        """Fetch lease 4 customer."""
        if not isinstance(pool_kind, NetworkIpPoolKind):
            raise TypeError('pool_kind must be choice from NetworkIpPoolKind')
        with connection.cursor() as cur:
            cur.execute("select * from fetch_subscriber_lease"
                        "(%s::macaddr, %s, %s, %s::boolean,"
                        "%s::smallint, %s::smallint)",
                        [customer_mac, customer_id, customer_group, is_dynamic,
                         vid, pool_kind.value])
            res = cur.fetchone()
        (lease_id, ip_addr, pool_id, lease_time, customer_mac,
         customer_id, is_dynamic, is_assigned) = res
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

    def _assign_guest_session(self, radius_uname: str,
                              customer_mac: str, session_id: str,
                              customer_id: Optional[int] = None):
        """Fetch guest lease."""
        # Тут создаём сессию и сразу выделяем гостевой ip для этой сессии.
        r = self.fetch_subscriber_lease(
            customer_mac=customer_mac,
            customer_id=customer_id,
            customer_group=None,
            is_dynamic=True,
            vid=None,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_GUEST
        )
        if not r:
            return None
        sess = self.filter(
            ip_lease_id=r.lease_id
        )
        if sess.exists():
            return sess.first()
        # TODO: Move session creating into
        #  'fetch_subscriber_lease' sql procedure
        sess = self.create(
            customer=None,
            last_event_time=datetime.now(),
            radius_username=radius_uname,
            ip_lease_id=r.lease_id,
            session_id=session_id
        )
        return sess

    def assign_guest_session(self, radius_uname: str,
                             customer_mac: str, session_id: str):
        """Fetch guest lease 4 unknown customer."""
        return self._assign_guest_session(radius_uname, customer_mac,
                                          session_id)

    def assign_guest_customer_session(self, radius_uname: str,
                                      customer_id: int,
                                      customer_mac: str,
                                      session_id: str):
        """
        Fetch guest lease for known customer, but who hasn't access to service.

        :param radius_uname: User-Name av from RADIUS.
        :param customer_id: customers.models.Customer model id.
        :param customer_mac: Customer device MAC address.
        :param session_id: unique session id.
        :return: CustomerRadiusSession instance
        """
        # Тут создаём сессию и сразу выделяем гостевой ip для этой сессии,
        #  с привязкой абонента.
        return self._assign_guest_session(
            radius_uname=radius_uname,
            customer_mac=customer_mac,
            session_id=session_id,
            customer_id=customer_id
        )


class CustomerRadiusSession(models.Model):
    """Model helper 4 RADIUS authentication."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                 default=None, null=True)
    assign_time = models.DateTimeField(
        help_text=_('Time when session assigned first time'),
        auto_now_add=True)
    last_event_time = models.DateTimeField(_('Last update time'))
    radius_username = models.CharField(_('User-Name av pair from radius'),
                                       max_length=128)
    ip_lease = models.OneToOneField(CustomerIpLeaseModel,
                                    verbose_name=_('Ip lease'),
                                    on_delete=models.CASCADE)
    session_id = models.UUIDField(_('Unique session id'))
    session_duration = models.DurationField(
        _('most often this is Acct-Session-Time av pair'),
        blank=True, null=True, default=None)
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
    closed = models.BooleanField(_('Is session finished'), default=False)

    objects = CustomerRadiusSessionManager()

    def finish_session(self) -> bool:
        """Send radius disconnect packet to BRAS."""
        if not self.radius_username:
            return False
        uname = str(self.radius_username).encode()
        uname = uname.replace(b'"', b'')
        uname = uname.replace(b"'", b'')
        fin_cmd_list = getattr(settings, 'RADIUS_FINISH_SESSION_CMD_LIST')
        if not fin_cmd_list:
            return False
        r = subprocess.run(
            fin_cmd_list,
            input=b'User-Name="%s"' % uname)
        return r.returncode == 0

    # def is_guest_session(self) -> bool:
    #     """Is current session guest."""
    #     return self.customer is None

    def h_input_octets(self):
        """Human readable input octets."""
        return _human_readable_int(self.input_octets)

    def h_output_octets(self):
        """Human readable output octets."""
        return _human_readable_int(self.output_octets)

    def h_input_packets(self):
        """Human readable input packets."""
        return _human_readable_int(self.input_packets)

    def h_output_packets(self):
        """Human readable output packets."""
        return _human_readable_int(self.output_packets)

    def delete(self, *args, **kwargs):
        """Remove current instance. And also remove ip lease."""
        # TODO: Move it to db trigger
        lease_id = self.ip_lease_id
        CustomerIpLeaseModel.objects.filter(pk=lease_id).delete()
        return super().delete(*args, **kwargs)

    def __str__(self):
        return "%s: (%s) %s" % (
            self.customer,
            self.radius_username,
            self.ip_lease
        )

    def __repr__(self):
        return "<%s>: %s" % (
            self.__class__.__name__,
            self.__str__()
        )

    class Meta:
        """Declare database table name in metaclass."""

        db_table = 'radius_customer_session'
