from django.utils.translation import gettext_lazy as _
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from djing2.lib import MyChoicesAdapter
from gateways.nas_managers import GW_TYPES, GatewayNetworkError


class Gateway(models.Model):
    title = models.CharField(_('Title'), max_length=127, unique=True)
    ip_address = models.GenericIPAddressField(_('Ip address'), unique=True)
    ip_port = models.PositiveSmallIntegerField(_('Port'))
    auth_login = models.CharField(_('Auth login'), max_length=64)
    auth_passw = EncryptedCharField(_('Auth password'), max_length=127)
    gw_type = models.PositiveSmallIntegerField(_('Type'), choices=MyChoicesAdapter(GW_TYPES), default=0)
    is_default = models.BooleanField(_('Is default'), default=False)
    enabled = models.BooleanField(_('Enabled'), default=True)

    def get_gw_manager_klass(self):
        try:
            return next(klass for code, klass in GW_TYPES if code == int(self.gw_type))
        except StopIteration:
            raise TypeError(_('One of nas types implementation is not found'))

    def get_gw_manager(self):
        try:
            klass = self.get_gw_manager_klass()
            if hasattr(self, '_gw_mngr'):
                o = getattr(self, '_gw_mngr')
            else:
                o = klass(
                    login=self.auth_login,
                    password=self.auth_passw,
                    ip=self.ip_address,
                    port=int(self.ip_port),
                    enabled=bool(self.enabled)
                )
                setattr(self, '_gw_mngr', o)
            return o
        except ConnectionResetError:
            raise GatewayNetworkError('ConnectionResetError')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'gateways'
        verbose_name = _('Network access server. Gateway')
        verbose_name_plural = _('Network access servers. Gateways')
        ordering = 'ip_address',
