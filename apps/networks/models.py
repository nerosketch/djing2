from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from typing import Optional, Union

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, connection, InternalError
from django.utils.translation import gettext_lazy as _
from netfields import MACAddressField, CidrAddressField

from customers.models import Customer
from djing2 import ping as icmp_ping
from djing2.lib import process_lock, LogicError, safe_int
from djing2.models import BaseAbstractModel
from groupapp.models import Group

DHCP_DEFAULT_LEASE_TIME = getattr(settings, "DHCP_DEFAULT_LEASE_TIME", 86400)


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
        ordering = ("vid",)
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
    network = CidrAddressField(
        verbose_name=_("Ip network address"),
        help_text=_("Ip address of network. For example: " "192.168.1.0 or fde8:6789:1234:1::"),
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

    # deprecated: pool_tag is deprecated, remove it
    pool_tag = models.CharField(
        _("Tag"), max_length=32, null=True, blank=True, default=None, validators=[validators.validate_slug]
    )
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return f"{self.description}: {self.network}"

    def clean(self):
        errs = {}
        if self.network is None:
            errs["network"] = ValidationError(_("Network is invalid"), code="invalid")

        try:
            net = ip_network("%s" % self.network)
        except ValueError as err:
            errs["network"] = ValidationError(message=str(err), code="invalid")
            raise ValidationError(errs)

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

    def get_free_ip(self) -> Optional[Union[IPv4Address, IPv6Address]]:
        """
        Finds unused ip
        :return:
        """
        with connection.cursor() as cur:
            cur.execute(
                "SELECT find_new_ip_pool_lease(%s, %s::boolean, 0::smallint, %s::smallint)"
                % (self.pk, 1 if self.is_dynamic else 0, self.kind)
            )
            free_ip = cur.fetchone()
        return ip_address(free_ip[0]) if free_ip and free_ip[0] else None

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

    class Meta:
        db_table = "networks_ip_pool"
        verbose_name = _("Network ip pool")
        verbose_name_plural = _("Network ip pools")
        ordering = ("network",)


class CustomerIpLeaseModelQuerySet(models.QuerySet):
    def active_leases(self) -> models.QuerySet:
        """
        Filter by time, where lease time does not expired
        :return: new QuerySet
        """
        expire_time = datetime.now() - timedelta(seconds=DHCP_DEFAULT_LEASE_TIME)
        return self.filter(lease_time__lt=expire_time)


class CustomerIpLeaseModel(models.Model):
    ip_address = models.GenericIPAddressField(_("Ip address"), unique=True)
    pool = models.ForeignKey(NetworkIpPool, on_delete=models.CASCADE)
    lease_time = models.DateTimeField(_("Lease time"), auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    mac_address = MACAddressField(verbose_name=_("Mac address"), null=True, default=None)
    is_dynamic = models.BooleanField(_("Is synamic"), default=False)
    last_update = models.DateTimeField(_("Last update"), blank=True, null=True, default=None)

    objects = CustomerIpLeaseModelQuerySet.as_manager()

    def __str__(self):
        return f"{self.ip_address} [{self.mac_address}]"

    @staticmethod
    def find_customer_by_device_credentials(device_mac: str, device_port: int = 0) -> Optional[Customer]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM find_customer_by_device_credentials(%s::macaddr, %s::smallint)",
                (device_mac, device_port),
            )
            res = cur.fetchone()
        if res is None or res[0] is None:
            return None
        (
            baseaccount_id,
            balance,
            ip_addr,
            descr,
            house,
            is_dyn_ip,
            auto_renw_srv,
            markers,
            curr_srv_id,
            dev_port_id,
            dev_id,
            gw_id,
            grp_id,
            last_srv_id,
            street_id,
            *others,
        ) = res
        return Customer(
            pk=baseaccount_id,
            balance=balance,
            description=descr,
            house=house,
            is_dynamic_ip=is_dyn_ip,
            auto_renewal_service=auto_renw_srv,
            markers=markers,
            current_service_id=curr_srv_id,
            device_id=dev_id,
            dev_port_id=dev_port_id,
            gateway_id=gw_id,
            group_id=grp_id,
            last_connected_service_id=last_srv_id,
            street_id=street_id,
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
        dev_port = dev_port if dev_port > 0 else None
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT * FROM lease_commit_add_update" "(%s::inet, %s::macaddr, %s::macaddr, %s::smallint)",
                    (client_ip, mac_addr, dev_mac, dev_port),
                )
                res = cur.fetchone()
            # lease_id, ip_addr, pool_id, lease_time, mac_addr, customer_id, is_dynamic, last_update = res
            return res
        except InternalError as err:
            raise LogicError(str(err))

    class Meta:
        db_table = "networks_ip_leases"
        verbose_name = _("IP lease")
        verbose_name_plural = _("IP leases")
        unique_together = ("ip_address", "mac_address", "pool", "customer")
        ordering = ("id",)


class CustomerIpLeaseLog(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("Ip address"))
    lease_time = models.DateTimeField(_("Lease time"), auto_now_add=True)
    last_update = models.DateTimeField(_("Last update"), blank=True, null=True, default=None)
    mac_address = MACAddressField(verbose_name=_("Mac address"), null=True, default=None)
    is_dynamic = models.BooleanField(_("Is synamic"), default=False)
    event_time = models.DateTimeField(_("Event time"), auto_now_add=True)
    end_use_time = models.DateTimeField(_("Lease end use time"), null=True, blank=True, default=None)

    def __str__(self):
        return self.ip_address

    class Meta:
        db_table = "networks_ip_lease_log"
