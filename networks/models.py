from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from typing import Optional, Union, Tuple

from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, connection, InternalError
from django.utils.translation import gettext_lazy as _
from netaddr import EUI
from netfields import MACAddressField, CidrAddressField

from customers.models.customer import Customer
from djing2 import ping as icmp_ping
from djing2.lib import macbin2str, safe_int, process_lock
from groupapp.models import Group
from .events import on_new_lease_assigned
from .exceptions import DhcpRequestError

DHCP_DEFAULT_LEASE_TIME = getattr(settings, 'DHCP_DEFAULT_LEASE_TIME', 86400)


class VlanIf(models.Model):
    title = models.CharField(_('Vlan title'), max_length=128)
    vid = models.PositiveSmallIntegerField(_('VID'), default=1, validators=[
        MinValueValidator(2, message=_('Vid could not be less then 2')),
        MaxValueValidator(4094, message=_('Vid could not be more than 4094'))
    ], unique=True)
    is_management = models.BooleanField(_('Is management'), default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'networks_vlan'
        ordering = 'vid',
        verbose_name = _('Vlan')
        verbose_name_plural = _('Vlan list')


class NetworkIpPoolKind(models.IntegerChoices):
    NETWORK_KIND_NOT_DEFINED = 0, _('Not defined')
    NETWORK_KIND_INTERNET = 1, _('Internet')
    NETWORK_KIND_GUEST = 2, _('Guest')
    NETWORK_KIND_TRUST = 3, _('Trusted')
    NETWORK_KIND_DEVICES = 4, _('Devices')
    NETWORK_KIND_ADMIN = 5, _('Admin')


class NetworkIpPool(models.Model):
    network = CidrAddressField(
        verbose_name=_('Ip network address'),
        help_text=_('Ip address of network. For example: '
                    '192.168.1.0 or fde8:6789:1234:1::'),
        unique=True
    )
    kind = models.PositiveSmallIntegerField(
        _('Kind of network'),
        choices=NetworkIpPoolKind.choices,
        default=NetworkIpPoolKind.NETWORK_KIND_NOT_DEFINED
    )
    description = models.CharField(_('Description'), max_length=64)
    groups = models.ManyToManyField(
        Group, verbose_name=_('Member groups'),
        db_table='networks_ippool_groups',
        blank=True
    )

    # Usable ip range
    ip_start = models.GenericIPAddressField(_('Start work ip range'))
    ip_end = models.GenericIPAddressField(_('End work ip range'))

    vlan_if = models.ForeignKey(
        VlanIf, verbose_name=_('Vlan interface'),
        on_delete=models.CASCADE, blank=True,
        null=True, default=None
    )

    gateway = models.GenericIPAddressField(_('Gateway ip address'))

    is_dynamic = models.BooleanField(_('Is dynamic'), default=False)

    pool_tag = models.CharField(
        _('Tag'), max_length=32, null=True, blank=True,
        default=None, validators=[validators.validate_slug]
    )

    def __str__(self):
        return "%s: %s" % (self.description, self.network)

    def clean(self):
        errs = {}
        if self.network is None:
            errs['network'] = ValidationError(
                _('Network is invalid'),
                code='invalid'
            )

        try:
            net = ip_network("%s" % self.network)
        except ValueError as err:
            errs['network'] = ValidationError(
                message=str(err),
                code='invalid'
            )
            raise ValidationError(errs)

        if self.ip_start is None:
            errs['ip_start'] = ValidationError(
                _('Ip start is invalid'),
                code='invalid'
            )

        start_ip = ip_address(self.ip_start)
        if start_ip not in net:
            errs['ip_start'] = ValidationError(
                _('Start ip must be in subnet of specified network'),
                code='invalid'
            )
        if self.ip_end is None:
            errs['ip_end'] = ValidationError(
                _('Ip end is invalid'),
                code='invalid'
            )

        end_ip = ip_address(self.ip_end)
        if end_ip not in net:
            errs['ip_end'] = ValidationError(
                _('End ip must be in subnet of specified network'),
                code='invalid'
            )

        gw = ip_address(self.gateway)
        if gw not in net:
            errs['gateway'] = ValidationError(
                _('Gateway ip must be in subnet of specified network'),
                code='invalid'
            )
        if start_ip <= gw <= end_ip:
            errs['gateway'] = ValidationError(
                _('Gateway must not be in the range of allowed ips'),
                code='invalid'
            )
        if errs:
            raise ValidationError(errs)

        other_nets = NetworkIpPool.objects.exclude(
            pk=self.pk
        ).only('network').order_by('network')
        if not other_nets.exists():
            return
        for other_net in other_nets.iterator():
            other_net_netw = ip_network("%s" % other_net.network)
            if net.overlaps(other_net_netw):
                errs['network'] = ValidationError(
                    _('Network is overlaps with %(other_network)s'),
                    params={
                        'other_network': str(other_net_netw)
                    }
                )
                raise ValidationError(errs)

    def get_free_ip(self) -> Optional[Union[IPv4Address, IPv6Address]]:
        """
        Finds unused ip
        :return:
        """
        pool_tag = str(self.pool_tag) if self.pool_tag else None
        with connection.cursor() as cur:
            if pool_tag is None:
                cur.execute("SELECT find_new_ip_pool_lease(%d, %d::boolean, null)" % (self.pk, 0))
            else:
                cur.execute("SELECT find_new_ip_pool_lease(%d, %d::boolean, %s)" % (self.pk, 0, pool_tag))
            free_ip = cur.fetchone()
        return ip_address(free_ip[0]) if free_ip and free_ip[0] else None

    @staticmethod
    def find_ip_pool_by_ip(ip_addr: str):
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_ip_pool_by_ip(%s::inet)",
                        (ip_addr,))
            res = cur.fetchone()
        if isinstance(res[0], int) and res[0] > 0:
            return NetworkIpPool(
                pk=res[0], network=res[1],
                kind=res[2], description=res[3],
                ip_start=res[4], ip_end=res[5],
                vlan_if_id=res[6],
                gateway=res[7], is_dynamic=res[8]
            )
        return None

    class Meta:
        db_table = 'networks_ip_pool'
        verbose_name = _('Network ip pool')
        verbose_name_plural = _('Network ip pools')
        ordering = 'network',


class CustomerIpLeaseModelQuerySet(models.QuerySet):
    def active_leases(self) -> models.QuerySet:
        """
        Filter by time, where lease time does not expired
        :return: new QuerySet
        """
        expire_time = datetime.now() - timedelta(seconds=DHCP_DEFAULT_LEASE_TIME)
        return self.filter(lease_time__lt=expire_time)


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


class CustomerIpLeaseModel(models.Model):
    ip_address = models.GenericIPAddressField(_('Ip address'), unique=True)
    pool = models.ForeignKey(NetworkIpPool, on_delete=models.CASCADE)
    lease_time = models.DateTimeField(_('Lease time'), auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    mac_address = MACAddressField(verbose_name=_('Mac address'), null=True, default=None)
    is_dynamic = models.BooleanField(_('Is synamic'), default=False)

    objects = CustomerIpLeaseModelQuerySet.as_manager()

    def __str__(self):
        return "%s [%s]" % (self.ip_address, self.mac_address)

    @staticmethod
    def fetch_subscriber_lease(customer_mac: str, device_mac: str, device_port: int = 0, is_dynamic: bool = True,
                               pool_tag: str = None):
        customer_mac = str(EUI(customer_mac))
        device_mac = str(EUI(device_mac))
        device_port = int(device_port)
        is_dynamic = 1 if is_dynamic else 0
        try:
            with connection.cursor() as cur:
                if pool_tag is None:
                    cur.execute(
                        "SELECT * from fetch_subscriber_lease"
                        "(%s::macaddr, %s::macaddr, %s::smallint, %s::boolean, null)",
                        (customer_mac, device_mac, device_port, is_dynamic))
                else:
                    cur.execute(
                        "SELECT * from fetch_subscriber_lease"
                        "(%s::macaddr, %s::macaddr, %s::smallint, %s::boolean, %s)",
                        (customer_mac, device_mac, device_port, is_dynamic, pool_tag[:32]))
                res = cur.fetchone()
            if len(res) == 8:
                v_id, v_ip_address, v_pool_id, v_lease_time, v_mac_address, v_customer_id, v_is_dynamic, is_assigned = res
                if v_id is None:
                    return None
                if is_assigned:
                    # New lease, makes signal for gateway
                    on_new_lease_assigned(v_id, v_ip_address, v_pool_id, v_lease_time,
                                          v_mac_address,
                                          v_customer_id, v_is_dynamic, is_assigned)
                return CustomerIpLeaseModel(
                    pk=v_id, ip_address=v_ip_address, pool_id=v_pool_id,
                    lease_time=v_lease_time, customer_id=v_customer_id,
                    mac_address=v_mac_address, is_dynamic=v_is_dynamic
                )
            else:
                raise DhcpRequestError('8 results expected from sql procedure'
                                       ' "fetch_subscriber_lease", got %d' % len(res))
        except InternalError as err:
            raise DhcpRequestError(err)

    @staticmethod
    def find_customer_id_by_device_credentials(device_mac: str, device_port: int = 0) -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_customer_by_device_credentials(%s::macaddr, %s::smallint)",
                        (device_mac, device_port))
            res = cur.fetchone()
        return res[0] if len(res) > 0 else None

    @staticmethod
    def get_service_permit_by_ip(ip_addr: str) -> bool:
        with connection.cursor() as cur:
            cur.execute("select * from find_service_permit(%s::inet)", [ip_addr])
            res = cur.fetchone()
        return res[0] if len(res) > 0 else None

    @process_lock()
    def ping_icmp(self, num_count=10, arp=False) -> bool:
        host_ip = str(self.ip_address)
        return icmp_ping(ip_addr=host_ip, count=num_count, arp=arp)

    @staticmethod
    def dhcp_commit_lease_add_update(client_ip: str, mac_addr: str,
                                     dev_mac: str,
                                     dev_port: int) -> str:
        """
        When external system assign ip address for customer
        then it ip address may be store to billing via this method.
        :param client_ip: client ip address
        :param mac_addr: client mac address
        :param dev_mac: device mac address
        :param dev_port: device port number
        :return: str about result
        """
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM dhcp_commit_lease_add_update"
                            "(%s::inet, %s::macaddr, %s::macaddr, %s::smallint)",
                            (client_ip, mac_addr, dev_mac, str(dev_port)))
                res = cur.fetchone()
            return "Assigned %s" % (res[1] or 'null')
        except InternalError as err:
            raise DhcpRequestError(str(err))

    class Meta:
        db_table = 'networks_ip_leases'
        verbose_name = _('IP lease')
        verbose_name_plural = _('IP leases')
        unique_together = ('ip_address', 'mac_address', 'pool', 'customer')
        ordering = 'id',

