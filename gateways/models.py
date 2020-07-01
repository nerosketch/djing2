from django.db import models, connection
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from .gw_facade import GatewayTypes, GatewayFacade, GatewayNetworkError


class Gateway(models.Model):
    title = models.CharField(_('Title'), max_length=127, unique=True)
    ip_address = models.GenericIPAddressField(_('Ip address'), unique=True)
    ip_port = models.PositiveSmallIntegerField(_('Port'))
    auth_login = models.CharField(_('Auth login'), max_length=64)
    auth_passw = EncryptedCharField(_('Auth password'), max_length=127)
    gw_type = models.PositiveSmallIntegerField(_('Type'),
                                               choices=GatewayTypes.choices,
                                               default=GatewayTypes.MIKROTIK)
    is_default = models.BooleanField(_('Is default'), default=False)
    enabled = models.BooleanField(_('Enabled'), default=True)

    def get_gw_manager(self) -> GatewayFacade:
        try:
            if hasattr(self, '_gw_mngr'):
                o = getattr(self, '_gw_mngr')
            else:
                o = GatewayFacade(self.gw_type, login=self.auth_login,
                                  password=self.auth_passw,
                                  ip=self.ip_address,
                                  port=int(self.ip_port),
                                  enabled=bool(self.enabled))
                setattr(self, '_gw_mngr', o)
            return o
        except ConnectionResetError:
            raise GatewayNetworkError('ConnectionResetError')

    @staticmethod
    def get_user_credentials_by_ip(gw_id: int):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ip_address, speed_in, speed_out FROM"
                " fetch_customers_srvnet_credentials_by_gw(%s::integer)",
                (str(gw_id),))
            while True:
                ip_address, speed_in, speed_out = cur.fetchone()
                if ip_address is None:
                    break
                yield ip_address, speed_in, speed_out

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'gateways'
        verbose_name = _('Network access server. Gateway')
        verbose_name_plural = _('Network access servers. Gateways')
        ordering = 'ip_address',
