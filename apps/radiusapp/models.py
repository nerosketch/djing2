"""radiusapp models file."""
from typing import Optional
from netaddr import EUI
from django.db import models, connection
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from networks.models import CustomerIpLeaseModel, NetworkIpPoolKind

from .radius_commands import finish_session, change_session_inet2guest, change_session_guest2inet


def _human_readable_int(num: int, u="b") -> str:
    """
    Translates 'num' into decimal prefixes with 'u' prefix name.

    :prop num: Integer count number.
    :prop u: Unit name.
    """
    decs = (
        (10 ** 12, "T"),
        (10 ** 9, "G"),
        (10 ** 6, "M"),
        (10 ** 3, "K"),
    )
    for dec, pref in decs:
        if num >= dec:
            num = round(num / dec, 2)
            return f"{num} {pref}{u}"
    return str(num)


class FetchSubscriberLeaseResponse:
    """Type for ip lease results."""

    lease_id = 0
    ip_addr = ""
    pool_id = 0
    lease_time = 0
    customer_mac = None
    customer_id = 0
    is_dynamic = None
    is_assigned = None

    def __init__(
        self,
        lease_id=0,
        ip_addr="",
        pool_id=0,
        lease_time=0,
        customer_mac=None,
        customer_id=0,
        is_dynamic=None,
        is_assigned=None,
    ):
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
        self.customer_mac = EUI(customer_mac) if customer_mac else None
        self.customer_id = customer_id
        self.is_dynamic = is_dynamic
        self.is_assigned = is_assigned

    def __repr__(self):
        """Repr 4 this."""
        return "{}: <{}, {}, {}, {}, {}>".format(
            self.__class__.__name__,
            self.ip_addr,
            self.lease_time,
            self.customer_mac,
            self.is_dynamic,
            self.is_assigned,
        )

    def __str__(self):
        """Str 4 this."""
        return self.__repr__()


class CustomerRadiusSessionManager(models.Manager):
    """Session manager 4 CustomerRadiusSession model."""

    @staticmethod
    def fetch_subscriber_lease(
        customer_mac: EUI,
        customer_id: Optional[int],
        customer_group: Optional[int],
        is_dynamic: bool,
        vid: Optional[int],
        pool_kind: NetworkIpPoolKind,
    ) -> Optional[FetchSubscriberLeaseResponse]:
        """Fetch lease 4 customer."""
        if not isinstance(pool_kind, NetworkIpPoolKind):
            raise TypeError("pool_kind must be choice from NetworkIpPoolKind")
        with connection.cursor() as cur:
            cur.execute(
                "select * from fetch_subscriber_lease"
                "(%s::macaddr, %s, %s, %s::boolean,"
                "%s::smallint, %s::smallint)",
                [str(customer_mac), customer_id, customer_group, is_dynamic, vid, pool_kind.value],
            )
            res = cur.fetchone()
        (lease_id, ip_addr, pool_id, lease_time, lease_mac, customer_id, is_dynamic, is_assigned) = res
        if lease_id is None:
            return
        return FetchSubscriberLeaseResponse(
            lease_id=lease_id,
            ip_addr=ip_addr,
            pool_id=pool_id,
            lease_time=lease_time,
            customer_mac=lease_mac,
            customer_id=customer_id,
            is_dynamic=is_dynamic,
            is_assigned=is_assigned,
        )

    def _assign_guest_session(
        self, customer_mac: EUI, customer_id: Optional[int] = None
    ) -> Optional[FetchSubscriberLeaseResponse]:
        """Fetch guest lease."""
        # Тут выделяем гостевой ip для этой сессии.
        return self.fetch_subscriber_lease(
            customer_mac=customer_mac,
            customer_id=customer_id,
            customer_group=None,
            is_dynamic=True,
            vid=None,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_GUEST,
        )

    def assign_guest_session(
        self,
        customer_mac: EUI,
    ) -> Optional[FetchSubscriberLeaseResponse]:
        """Fetch guest lease 4 unknown customer."""
        return self._assign_guest_session(customer_mac=customer_mac)

    def assign_guest_customer_session(
        self, customer_id: int, customer_mac: EUI
    ) -> Optional[FetchSubscriberLeaseResponse]:
        """
        Fetch guest lease for known customer, but who hasn't access to service.

        :param customer_id: customers.models.Customer model id.
        :param customer_mac: Customer device MAC address.
        :return: CustomerRadiusSession instance
        """
        # Тут создаём сессию и сразу выделяем гостевой ip для этой сессии,
        #  с привязкой абонента.
        return self._assign_guest_session(customer_mac=customer_mac, customer_id=customer_id)


class CustomerRadiusSession(models.Model):
    """Model helper 4 RADIUS authentication."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, default=None, null=True)
    assign_time = models.DateTimeField(help_text=_("Time when session assigned first time"), auto_now_add=True)
    last_event_time = models.DateTimeField(_("Last update time"))
    radius_username = models.CharField(_("User-Name av pair from radius"), max_length=128)
    ip_lease = models.OneToOneField(CustomerIpLeaseModel, verbose_name=_("Ip lease"), on_delete=models.CASCADE)
    session_id = models.UUIDField(_("Unique session id"))
    session_duration = models.DurationField(
        _("most often this is Acct-Session-Time av pair"), blank=True, null=True, default=None
    )
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
    closed = models.BooleanField(_("Is session finished"), default=False)

    objects = CustomerRadiusSessionManager()

    def finish_session(self) -> bool:
        """Send radius disconnect packet to BRAS."""
        if not self.radius_username:
            return False
        return finish_session(self.radius_username)

    def radius_coa_inet2guest(self) -> bool:
        if not self.radius_username:
            return False
        return change_session_inet2guest(self.radius_username)

    def radius_coa_guest2inet(self) -> bool:
        if not self.radius_username:
            return False
        if not self.customer:
            return False
        customer_service = self.customer.current_service
        if not customer_service:
            return False
        service = customer_service.service
        if not service:
            return False

        speed_in_burst, speed_out_burst = service.calc_burst()
        return change_session_guest2inet(
            radius_uname=self.radius_username,
            speed_in=int(service.speed_in * 1000000),
            speed_out=int(service.speed_out * 1000000),
            speed_in_burst=speed_in_burst,
            speed_out_burst=speed_out_burst,
        )

    # def is_guest_session(self) -> bool:
    #     """Is current session guest."""
    #     return self.customer is None

    def h_input_octets(self):
        """Human readable input octets."""
        return _human_readable_int(num=self.input_octets)

    def h_output_octets(self):
        """Human readable output octets."""
        return _human_readable_int(num=self.output_octets)

    def h_input_packets(self):
        """Human readable input packets."""
        return _human_readable_int(num=self.input_packets, u="p")

    def h_output_packets(self):
        """Human readable output packets."""
        return _human_readable_int(num=self.output_packets, u="p")

    def __str__(self):
        return f"{self.customer}: ({self.radius_username}) {self.ip_lease}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>: {self.__str__()}"

    class Meta:
        """Declare database table name in metaclass."""

        db_table = "radius_customer_session"
