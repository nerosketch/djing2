from ipaddress import ip_address, ip_network

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from netfields import MACAddressField

from customers.models.customer import Customer
from groupapp.models import Group


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
        ordering = ('-id',)
        verbose_name = _('Vlan')
        verbose_name_plural = _('Vlan list')


class NetworkIpPool(models.Model):
    _netw_cache = None

    network = models.GenericIPAddressField(
        verbose_name=_('Ip network address'),
        help_text=_('Ip address of network. For example: '
                    '192.168.1.0 or fde8:6789:1234:1::'),
        unique=True
    )
    net_mask = models.PositiveSmallIntegerField(
        verbose_name=_('Network mask'),
        default=24
    )
    NETWORK_KINDS = (
        (0, _('Not defined')),
        (1, _('Internet')),
        (2, _('Guest')),
        (3, _('Trusted')),
        (4, _('Devices')),
        (5, _('Admin'))
    )
    kind = models.PositiveSmallIntegerField(
        _('Kind of network'),
        choices=NETWORK_KINDS, default=0
    )
    description = models.CharField(_('Description'), max_length=64)

    # Usable ip range
    ip_start = models.GenericIPAddressField(_('Start work ip range'))
    ip_end = models.GenericIPAddressField(_('End work ip range'))

    vlan_if = models.ForeignKey(
        VlanIf, verbose_name=_('Vlan interface'),
        on_delete=models.CASCADE, blank=True,
        null=True, default=None
    )

    gateway = models.GenericIPAddressField(_('Gateway ip address'))
    # Default lease time is one hour
    lease_time = models.PositiveSmallIntegerField(_('Lease time seconds'), default=3600)

    def __str__(self):
        return "%s: %s/%d" % (self.description, self.network, self.net_mask)

    def clean(self):
        errs = {}
        if self.network is None:
            errs['network'] = ValidationError(
                _('Network is invalid'),
                code='invalid'
            )

        try:
            net = ip_network("%s/%d" % (self.network, self.net_mask))
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
        if errs:
            raise ValidationError(errs)

        other_nets = NetworkIpPool.objects.exclude(
            pk=self.pk
        ).only('network').order_by('network')
        if not other_nets.exists():
            return
        for other_net in other_nets.iterator():
            other_net_netw = ip_network("%s/%d" % (other_net.network, self.net_mask))
            if net.overlaps(other_net_netw):
                errs['network'] = ValidationError(
                    _('Network is overlaps with %(other_network)s'),
                    params={
                        'other_network': str(other_net_netw)
                    }
                )
                raise ValidationError(errs)

    # def get_free_ip(self, employed_ips: Optional[Generator]):
    #     """
    #     Find free ip in network.
    #     :param employed_ips: Sorted from less to more
    #      ip addresses from current network.
    #     :return: single found ip or None
    #     """
    #     network = self.network
    #     work_range_start_ip = ip_address(self.ip_start)
    #     work_range_end_ip = ip_address(self.ip_end)
    #     if employed_ips is None:
    #         for ip in network.network:
    #             if work_range_start_ip <= ip <= work_range_end_ip:
    #                 return ip
    #         return
    #     for ip in network.network:
    #         if ip < work_range_start_ip:
    #             continue
    #         elif ip > work_range_end_ip:
    #             break  # Not found
    #         try:
    #             used_ip = next(employed_ips)
    #         except StopIteration:
    #             return ip
    #         if used_ip is None:
    #             return ip
    #         used_ip = ip_address(used_ip)
    #         if ip < used_ip:
    #             return ip

    class Meta:
        db_table = 'networks_ip_pool'
        verbose_name = _('Network ip pool')
        verbose_name_plural = _('Network ip pools')
        ordering = ('network',)


class CustomerIpLease(models.Model):
    ip_address = models.GenericIPAddressField(_('Ip address'))
    pool = models.ForeignKey(NetworkIpPool, on_delete=models.CASCADE)
    lease_time = models.DateTimeField(_('Lease time'), auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    customer_mac = MACAddressField(verbose_name=_('Customer mac address'))

    class Meta:
        db_table = 'networks_ip_leases'
        verbose_name = _('Customer ip lease')
        verbose_name_plural = _('Customer ip leases')
