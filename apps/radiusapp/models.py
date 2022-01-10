"""radiusapp models file."""
from typing import Optional
from netaddr import EUI
from django.db import models, connection
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from networks.models import CustomerIpLeaseModel, NetworkIpPoolKind

from radiusapp.radius_commands import finish_session, change_session_inet2guest, change_session_guest2inet


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


class CustomerRadiusSession(models.Model):
    """Model helper 4 RADIUS authentication."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, default=None, null=True)
    assign_time = models.DateTimeField(help_text=_("Time when session assigned first time"), auto_now_add=True)
    last_event_time = models.DateTimeField(_("Last update time"))
    radius_username = models.CharField(_("User-Name av pair from radius"), max_length=128)
    ip_lease = models.OneToOneField(CustomerIpLeaseModel, verbose_name=_("Ip lease"), on_delete=models.CASCADE)
    session_id = models.UUIDField(_("Unique session id"))
    session_duration = models.DurationField(
        verbose_name=_('Session duration'),
        help_text=_("most often this is Acct-Session-Time av pair"), blank=True, null=True, default=None
    )
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
    closed = models.BooleanField(_("Is session finished"), default=False)

    def finish_session(self) -> Optional[str]:
        """Send radius disconnect packet to BRAS."""
        if not self.radius_username:
            return
        return finish_session(self.radius_username)

    def radius_coa_inet2guest(self) -> Optional[str]:
        if not self.radius_username:
            return
        return change_session_inet2guest(self.radius_username)

    def radius_coa_guest2inet(self) -> Optional[str]:
        if not self.radius_username:
            return
        if not self.customer:
            return
        customer_service = self.customer.current_service
        if not customer_service:
            return
        service = customer_service.service
        if not service:
            return

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

    @staticmethod
    def create_lease_w_auto_pool_n_session(ip: str, mac: str, customer_id: int,
                                           radius_uname: str, radius_unique_id: str) -> bool:
        with connection.cursor() as cur:
            cur.execute("SELECT create_lease_w_auto_pool_n_session"
                        "(%s::inet, %s::macaddr, %s::integer, %s, %s::uuid)",
                        (ip, mac, customer_id, radius_uname, radius_unique_id))
            created = cur.fetchone()
        return created

    def __str__(self):
        return f"{self.customer}: ({self.radius_username}) {self.ip_lease}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>: {self.__str__()}"

    class Meta:
        """Declare database table name in metaclass."""

        db_table = "radius_customer_session"
