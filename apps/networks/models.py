from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from typing import Optional, Union
from netaddr import EUI

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, connection, InternalError
from django.utils.translation import gettext_lazy as _
from netfields import MACAddressField, CidrAddressField
from djing2 import ping as icmp_ping
from djing2.lib import process_lock, LogicError, safe_int
from djing2.models import BaseAbstractModel
from groupapp.models import Group
from customers.models import Customer
from networks.radius_commands import finish_session


DHCP_DEFAULT_LEASE_TIME = getattr(settings, "DHCP_DEFAULT_LEASE_TIME", 86400)


def _human_readable_int(num: int, u="b") -> str:
    """
    Translates 'num' into decimal prefixes with 'u' prefix name.

    :prop num: Integer count number.
    :prop u: Unit name.
    """
    decs = (
        (10 ** 12, "T"),
        (10 **  9, "G"),
        (10 **  6, "M"),
        (10 **  3, "K"),
    )
    for dec, pref in decs:
        if num >= dec:
            num = round(num / dec, 2)
            return f"{num} {pref}{u}"
    return str(num)

class VlanIf(BaseAbstractModel):
    title = models.CharField(_("Vlan title"), max_length=128)
    vid = models.PositiveSmallIntegerField(
        _("VID"),
        default=1,
        validators=[
            MinValueValidator(2, message=_("Vid could not be less then 2")),
            MaxValueValidator(4094, message=_("Vid could not be more than 4094")),
        ],
        unique=True,
    )
    is_management = models.BooleanField(_("Is management"), default=False)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "networks_vlan"
        verbose_name = _("Vlan")
        verbose_name_plural = _("Vlan list")


class NetworkIpPoolKind(models.IntegerChoices):
    NETWORK_KIND_NOT_DEFINED = 0, _("Not defined")
    NETWORK_KIND_INTERNET = 1, _("Internet")
    NETWORK_KIND_GUEST = 2, _("Guest")
    NETWORK_KIND_TRUST = 3, _("Trusted")
    NETWORK_KIND_DEVICES = 4, _("Devices")
    NETWORK_KIND_ADMIN = 5, _("Admin")


class NetworkIpPool(BaseAbstractModel):
    """Customer network ip lease information"""

    network = CidrAddressField(
        verbose_name=_("Ip network address"),
        help_text=_("Ip address of network. For example: 192.168.1.0/24 or fde8:6789:1234:1::/64"),
        unique=True,
    )
    kind = models.PositiveSmallIntegerField(
        _("Kind of network"), choices=NetworkIpPoolKind.choices, default=NetworkIpPoolKind.NETWORK_KIND_NOT_DEFINED
    )
    description = models.CharField(_("Description"), max_length=64)
    groups = models.ManyToManyField(
        Group, verbose_name=_("Member groups"), db_table="networks_ippool_groups", blank=True
    )

    # Usable ip range
    ip_start = models.GenericIPAddressField(_("Start work ip range"))
    ip_end = models.GenericIPAddressField(_("End work ip range"))

    vlan_if = models.ForeignKey(
        VlanIf, verbose_name=_("Vlan interface"), on_delete=models.CASCADE, blank=True, null=True, default=None
    )

    gateway = models.GenericIPAddressField(_("Gateway ip address"))

    is_dynamic = models.BooleanField(_("Is dynamic"), default=False)

    create_time = models.DateTimeField(auto_now_add=True)

    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return f"{self.description}: {self.network}"

    def __repr__(self):
        return f"<{self.__class__.__name__}>: {self.__str__()}"

    def clean(self):
        errs = {}
        if self.network is None:
            errs["network"] = ValidationError(_("Network is invalid"), code="invalid")

        try:
            net = ip_network("%s" % self.network)
        except ValueError as err:
            errs["network"] = ValidationError(message=str(err), code="invalid")
            raise ValidationError(errs) from err

        if self.ip_start is None:
            errs["ip_start"] = ValidationError(_("Ip start is invalid"), code="invalid")

        start_ip = ip_address(self.ip_start)
        if start_ip not in net:
            errs["ip_start"] = ValidationError(_("Start ip must be in subnet of specified network"), code="invalid")
        if self.ip_end is None:
            errs["ip_end"] = ValidationError(_("Ip end is invalid"), code="invalid")

        end_ip = ip_address(self.ip_end)
        if end_ip not in net:
            errs["ip_end"] = ValidationError(_("End ip must be in subnet of specified network"), code="invalid")

        gw = ip_address(self.gateway)
        if gw not in net:
            errs["gateway"] = ValidationError(_("Gateway ip must be in subnet of specified network"), code="invalid")
        if start_ip <= gw <= end_ip:
            errs["gateway"] = ValidationError(_("Gateway must not be in the range of allowed ips"), code="invalid")
        if errs:
            raise ValidationError(errs)

        other_nets = NetworkIpPool.objects.exclude(pk=self.pk).only("network").order_by("network")
        if not other_nets.exists():
            return
        for other_net in other_nets.iterator():
            other_net_netw = ip_network("%s" % other_net.network)
            if net.overlaps(other_net_netw):
                errs["network"] = ValidationError(
                    _("Network is overlaps with %(other_network)s"), params={"other_network": str(other_net_netw)}
                )
                raise ValidationError(errs)

    def get_free_ip(self) -> Optional['CustomerIpLeaseModel']:
        """
        Find unused ip
        :return:
        """
        return CustomerIpLeaseModel.objects.filter(
            pool=self,
            customer=None,
            is_dynamic=self.is_dynamic
        ).first()

    @staticmethod
    def find_ip_pool_by_ip(ip_addr: str):
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_ip_pool_by_ip(%s::inet)", (ip_addr,))
            res = cur.fetchone()
        if isinstance(res[0], int) and res[0] > 0:
            return NetworkIpPool(
                pk=res[0],
                network=res[1],
                kind=res[2],
                description=res[3],
                ip_start=res[4],
                ip_end=res[5],
                vlan_if_id=res[6],
                gateway=res[7],
                is_dynamic=res[8],
            )
        return None

    def reserve_leases(self):
        start_ip = ip_address(self.ip_start)
        end_ip = ip_address(self.ip_end)
        sql = ("INSERT INTO networks_ip_leases"
                "(ip_address, pool_id, is_dynamic, "
                "last_update, state, svid, cvid, input_octets, "
                "input_packets, output_octets, output_packets) "
                "SELECT %s::inet + ip, %s::int, false, null, "
                "false, 0,0,0,0,0,0 FROM generate_series(0, %s::int) ip "
                "ON CONFLICT DO NOTHING"
               )
        range_len = int(end_ip) - int(start_ip)
        with connection.cursor() as cur:
            cur.execute(sql=sql, params=[str(start_ip), self.pk, range_len])

    class Meta:
        """Declare database table name in metaclass."""
        db_table = "networks_ip_pool"
        verbose_name = _("Network ip pool")
        verbose_name_plural = _("Network ip pools")


class CustomerIpLeaseModelQuerySet(models.QuerySet):
    def active_leases(self) -> models.QuerySet:
        """
        Filter by time, where lease time does not expired
        :return: new QuerySet
        """
        expire_time = datetime.now() - timedelta(seconds=DHCP_DEFAULT_LEASE_TIME)
        return self.filter(lease_time__lt=expire_time)

    def release(self):
        """
        Free leases. Mark it free, for use again.
        """
        return self.update(
            mac_address=None,
            customer=None,
            input_octets=0,
            output_octets=0,
            input_packets=0,
            output_packets=0,
            cvid=0,
            svid=0,
            state=False,
            last_update=datetime.now(),
            session_id=None,
            radius_username=None
        )


class CustomerIpLeaseModel(models.Model):
    ip_address = models.GenericIPAddressField(_("Ip address"), unique=True)
    mac_address = MACAddressField(verbose_name=_("Mac address"), null=True, default=None)
    pool = models.ForeignKey(NetworkIpPool, on_delete=models.CASCADE, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, default=None)
    is_dynamic = models.BooleanField(_("Is dynamic"), default=False)
    input_octets = models.BigIntegerField(default=0)
    output_octets = models.BigIntegerField(default=0)
    input_packets = models.BigIntegerField(default=0)
    output_packets = models.BigIntegerField(default=0)
    cvid = models.PositiveSmallIntegerField(_("Customer Vlan id"), default=0)
    svid = models.PositiveSmallIntegerField(_("Service Vlan id"), default=0)
    state = models.BooleanField(_('Lease state'), null=True, blank=True, default=None)
    lease_time = models.DateTimeField(_("Lease time"), blank=True, null=True, default=datetime.now)
    last_update = models.DateTimeField(_("Last update"), blank=True, null=True, default=None)
    session_id = models.UUIDField(_("Unique session id"), blank=True, null=True, default=None)
    radius_username = models.CharField(
        _("User-Name av pair from radius"),
        max_length=128,
        null=True,
        blank=True,
        default=None
    )

    objects = CustomerIpLeaseModelQuerySet.as_manager()

    def __str__(self):
        return f"{self.ip_address} [{self.mac_address}]"

    @staticmethod
    def find_customer_by_device_credentials(device_mac: Union[EUI, str], device_port: int = 0) -> Optional[Customer]:
        sql = (
            "SELECT ba.id, ba.last_login, ba.is_superuser, ba.username, "
            "ba.fio, ba.birth_day, ba.is_active, ba.is_admin, "
            "ba.telephone, ba.create_date, ba.last_update_time, "
            "cs.balance, cs.is_dynamic_ip, cs.auto_renewal_service, "
            "cs.current_service_id, cs.dev_port_id, cs.device_id, "
            "cs.gateway_id, cs.group_id, cs.last_connected_service_id, cs.address_id "
            "FROM customers cs "
            "LEFT JOIN device dv ON (dv.id = cs.device_id) "
            "LEFT JOIN device_port dp ON (cs.dev_port_id = dp.id) "
            "LEFT JOIN device_dev_type_is_use_dev_port ddtiudptiu ON (ddtiudptiu.dev_type = dv.dev_type) "
            "LEFT JOIN base_accounts ba ON cs.baseaccount_ptr_id = ba.id "
            "WHERE dv.mac_addr = %s::MACADDR "
            "AND ((NOT ddtiudptiu.is_use_dev_port) OR dp.num = %s::SMALLINT) "
            "LIMIT 1;"
        )
        with connection.cursor() as cur:
            cur.execute(
                sql, (str(device_mac), device_port),
            )
            res = cur.fetchone()
        if res is None or res[0] is None:
            return None
        (
            bid, last_login, is_superuser, username,
            fio, birth_day, is_active, is_admin,
            telephone, create_date, last_update_time,
            balance, is_dyn_ip, auto_renw_srv,
            curr_srv_id, dev_port_id, dev_id,
            gw_id, grp_id, last_srv_id, address_id,
        ) = res
        return Customer(
            pk=bid,
            last_login=last_login,
            is_superuser=is_superuser,
            username=username,
            fio=fio,
            birth_day=birth_day,
            is_active=is_active,
            is_admin=is_admin,
            telephone=telephone,
            create_date=create_date,
            last_update_time=last_update_time,
            balance=balance,
            is_dynamic_ip=is_dyn_ip,
            auto_renewal_service=auto_renw_srv,
            current_service_id=curr_srv_id,
            dev_port_id=dev_port_id,
            device_id=dev_id,
            gateway_id=gw_id,
            group_id=grp_id,
            last_connected_service_id=last_srv_id,
            address_id=address_id,
        )

    @staticmethod
    def get_service_permit_by_ip(ip_addr: str) -> bool:
        with connection.cursor() as cur:
            cur.execute("select * from find_service_permit(%s::inet)", [ip_addr])
            res = cur.fetchone()
        return res[0] if len(res) > 0 else False

    @process_lock()
    def ping_icmp(self, num_count=10, arp=False) -> bool:
        host_ip = str(self.ip_address)
        return icmp_ping(ip_addr=host_ip, count=num_count, arp=arp)

    @staticmethod
    def lease_commit_add_update(client_ip: str, mac_addr: str, dev_mac: str, dev_port: int):
        """
        When external system assign ip address for customer
        then it ip address may be store to billing via this method.
        :param client_ip: client ip address
        :param mac_addr: client mac address
        :param dev_mac: device mac address
        :param dev_port: device port number
        :return: str about result
        """
        dev_port = safe_int(dev_port)
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT * FROM lease_commit_add_update(%s::inet, %s::macaddr, %s::macaddr, %s::smallint)",
                    (client_ip, mac_addr, dev_mac, dev_port or None),
                )
                res = cur.fetchone()
            # lease_id, ip_addr, pool_id, lease_time, mac_addr, customer_id, is_dynamic, last_update = res
            return res
        except InternalError as err:
            raise LogicError(str(err)) from err

    @property
    def h_input_octets(self):
        """Human readable input octets."""
        return _human_readable_int(num=self.input_octets)

    @property
    def h_output_octets(self):
        """Human readable output octets."""
        return _human_readable_int(num=self.output_octets)

    @property
    def h_input_packets(self):
        """Human readable input packets."""
        return _human_readable_int(num=self.input_packets, u="p")

    @property
    def h_output_packets(self):
        """Human readable output packets."""
        return _human_readable_int(num=self.output_packets, u="p")

    @property
    def finish_session(self) -> Optional[str]:
        """Send radius disconnect packet to BRAS."""
        if not self.radius_username:
            return
        return finish_session(self.radius_username)

    class Meta:
        db_table = "networks_ip_leases"
        verbose_name = _("IP lease")
        verbose_name_plural = _("IP leases")


class CustomerIpLeaseLog(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("Ip address"))
    lease_time = models.DateTimeField(_("Lease time"), auto_now_add=True)
    last_update = models.DateTimeField(_("Last update"), blank=True, null=True, default=None)
    mac_address = MACAddressField(verbose_name=_("Mac address"), null=True, default=None)
    is_dynamic = models.BooleanField(_("Is dynamic"), default=False)
    event_time = models.DateTimeField(_("Event time"), auto_now_add=True)
    end_use_time = models.DateTimeField(_("Lease end use time"), null=True, blank=True, default=None)

    def __str__(self):
        return self.ip_address

    class Meta:
        db_table = "networks_ip_lease_log"
