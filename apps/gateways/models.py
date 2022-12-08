from django.contrib.sites.models import Site
from django.db import models, connection
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from djing2.lib import MyChoicesAdapter
from djing2.models import BaseAbstractModel
from .gw_facade import GATEWAY_TYPES, GatewayFacade, GatewayNetworkError


class GatewayClassChoices(models.IntegerChoices):
    UNKNOWN = 0, 'unknown'
    SGSN = 1, 'sgsn'       # узел обслуживания абонентов GPRS
    GGSN = 2, 'ggsn'       # узел обеспечивающий маршрутизацию данных между GPRS Core network (GTP) и внешними IP сетями
    SMSC = 3, 'smsc'       # SMS-центр
    GMSC = 4, 'gmsc'       # базовая сеть GSM
    HSS = 5, 'hss'         # сервер домашних абонентов
    PSTN = 6, 'pstn'       # телефонная сеть общего пользования
    VOIP_GW = 7, 'voip-gw' # VOIP-шлюз
    AAA = 8, 'aaa'         # AAA-сервер(RADIUS сервер)
    NAT = 9, 'nat'         # NAT-сервер


class Gateway(BaseAbstractModel):
    title = models.CharField(_("Title"), max_length=127, unique=True)
    ip_address = models.GenericIPAddressField(_("Ip address"), unique=True)
    ip_port = models.PositiveSmallIntegerField(_("Port"))
    auth_login = models.CharField(_("Auth login"), max_length=64)
    auth_passw = EncryptedCharField(_("Auth password"), max_length=127)
    gw_type = models.PositiveSmallIntegerField(_("Type"), choices=MyChoicesAdapter(GATEWAY_TYPES), default=0)
    gw_class = models.PositiveSmallIntegerField(
        _("Gateway class"),
        choices=GatewayClassChoices.choices,
        default=GatewayClassChoices.UNKNOWN
    )
    is_default = models.BooleanField(_("Is default"), default=False)
    enabled = models.BooleanField(_("Enabled"), default=True)
    create_time = models.DateTimeField(_("Create time"), auto_now_add=True)
    place = models.CharField(
        _("Device place address"),
        max_length=256,
        null=True,
        blank=True,
        default=None
    )

    sites = models.ManyToManyField(Site, blank=True)

    def get_gw_manager(self) -> GatewayFacade:
        try:
            if hasattr(self, "_gw_mngr"):
                o = getattr(self, "_gw_mngr")
            else:
                o = GatewayFacade(
                    self.gw_type,
                    login=self.auth_login,
                    password=self.auth_passw,
                    ip=self.ip_address,
                    port=int(self.ip_port),
                    enabled=bool(self.enabled),
                )
                setattr(self, "_gw_mngr", o)
            return o
        except ConnectionResetError as ce:
            raise GatewayNetworkError("ConnectionResetError") from ce

    @staticmethod
    def get_user_credentials_by_gw(gw_id: int):
        sql = (
            "SELECT "
                "c.baseaccount_ptr_id, "
                "nil.id, "
                "nil.lease_time, "
                "nil.mac_address, "
                "nil.ip_address, "
                "s.speed_in, "
                "s.speed_out, "
                "s.speed_burst, "
                "cs.start_time, "
                "cs.deadline "
            "FROM customers c "
               "LEFT JOIN networks_ip_leases nil ON (nil.customer_id = c.baseaccount_ptr_id) "
               "LEFT JOIN customer_service cs ON (cs.customer_id = c.baseaccount_ptr_id) "
               "LEFT JOIN services s ON (s.id = cs.service_id) "
               "LEFT JOIN base_accounts ba ON (ba.id = c.baseaccount_ptr_id) "
            "WHERE c.gateway_id = %s::integer AND ba.is_active AND "
               "c.baseaccount_ptr_id IS NOT NULL AND cs.id IS NOT NULL AND nil.ip_address IS NOT NULL"
        )
        with connection.cursor() as cur:
            cur.execute(sql=sql, params=[str(gw_id)])
            els = cur.fetchone()
            while els:
                # (customer_id, lease_id, lease_time, lease_mac, ip_address,
                #  speed_in, speed_out, speed_burst, service_start_time,
                #  service_deadline)
                yield els
                els = cur.fetchone()

    def __str__(self):
        return self.title

    class Meta:
        db_table = "gateways"
        verbose_name = _("Network access server. Gateway")
        verbose_name_plural = _("Network access servers. Gateways")
