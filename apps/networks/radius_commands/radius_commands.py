import os
from typing import Optional
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException
from starlette import status
from pyrad.client import Client, Timeout
from pyrad import packet
from pyrad import dictionary


options = getattr(settings, 'RADIUSAPP_OPTIONS')
if options is None:
    raise ImproperlyConfigured('You must specified RADIUSAPP_OPTIONS in settings')

ADDRESS = options.get('server_host')
SECRET = options.get('secret')

if not all([ADDRESS, SECRET]):
    raise ImproperlyConfigured("You must set 'server_host' and 'secret' options to RADIUSAPP_OPTIONS dict")
del options


def _abspath(fname):
    curdir = os.path.dirname(__file__)
    return os.path.join(curdir, fname)


class RadiusBaseException(APIException):
    pass


class RadiusSessionNotFoundException(RadiusBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _('Radius session not found error')


class RadiusTimeoutException(RadiusBaseException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_detail = _('Radius timeout error')


class RadiusInvalidRequestException(RadiusBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Radius invalid request')


class RadiusMissingAttributeException(RadiusBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Radius missing attibute')


class RadiusInteract:
    client = Client(server=ADDRESS, secret=SECRET, dict=dictionary.Dictionary(_abspath("dictionary")))
    # client.timeout = 30

    def coa_inet2guest(self, uname: str):
        # FIXME: move params to radius config
        attrs = {
            'User-Name': uname,
            'ERX-Service-Deactivate': 'SERVICE-INET',
            'ERX-Service-Activate:1': 'SERVICE-GUEST',
            'ERX-Service-Acct-Interval:1': 600,
            'ERX-Service-Statistics:1': 2
        }
        return self.coa(**attrs)

    def coa_guest2inet(self, uname: str, speed_in: int, speed_out: int, speed_in_burst: int, speed_out_burst: int):
        attrs = {
            'User-Name': uname,
            'ERX-Service-Deactivate': 'SERVICE-GUEST',
            'ERX-Service-Activate:1': f'SERVICE-INET({speed_in},{speed_in_burst},{speed_out},{speed_out_burst})',
            'ERX-Service-Acct-Interval:1': 600,
            'ERX-Service-Statistics:1': 2
        }
        return self.coa(**attrs)

    def coa(self, **attrs):
        # create coa request
        request = self.client.CreateCoAPacket(**attrs)
        return self._process_request(request)

    def disconnect(self, uname: str):
        attrs = {
            "User-Name": uname
        }
        # create disconnect request
        request = self.client.CreateCoAPacket(code=packet.DisconnectRequest, **attrs)
        return self._process_request(request)

    def _process_request(self, request) -> Optional[str]:
        try:
            res = self.client.SendPacket(request)
            if res.code in (packet.CoAACK, packet.AccessAccept, packet.DisconnectACK):
                # ok
                return 'ok'
            res_keys = res.keys()
            exception = None
            if 'Error-Cause' in res_keys:
                errs = res.get('Error-Cause')
                if 'Session-Context-Not-Found' in errs:
                    exception = RadiusSessionNotFoundException
                elif 'Invalid-Request' in errs:
                    exception = RadiusInvalidRequestException
                elif 'Missing-Attribute' in errs:
                    exception = RadiusMissingAttributeException

                res_keys.remove('Error-Cause')
            # get err text
            res_text = b'\n\n'.join(b'\n'.join(res.get(i)) for i in res_keys)
            res_text = res_text.decode()
            if exception is not None:
                raise exception(res_text)
            return res_text
        except Timeout as e:
            raise RadiusTimeoutException(e) from e


_rad_interact_instance = RadiusInteract()


def _filter_uname(uname: str) -> str:
    _uname = str(uname)
    _uname = _uname.replace('"', "")
    _uname = _uname.replace("'", "")
    return _uname


def finish_session(radius_uname: str):
    """Send radius disconnect packet to BRAS."""
    if not radius_uname:
        return
    uname = _filter_uname(radius_uname)
    return _rad_interact_instance.disconnect(uname=uname)


def change_session_inet2guest(radius_uname: str):
    if not radius_uname:
        return
    uname = _filter_uname(radius_uname)
    # COA inet -> guest
    return _rad_interact_instance.coa_inet2guest(uname=uname)


def change_session_guest2inet(
    radius_uname: str, speed_in: int, speed_out: int, speed_in_burst: int, speed_out_burst: int
):
    """
    Send COA via radclient, change guest service type to inet service type.
    :param radius_uname: User-Name from radius
    :param speed_in: Customer service input speed in bits/s
    :param speed_out: Customer service output speed in bits/s
    :param speed_in_burst: Customer service input speed burst
    :param speed_out_burst: Customer service output speed burst
    :return: boolean, is return code of script is equal 0
    """
    if not radius_uname:
        return
    uname = _filter_uname(radius_uname)
    speed_in = int(speed_in)
    speed_out = int(speed_out)
    speed_in_burst, speed_out_burst = int(speed_in_burst), int(speed_out_burst)

    # COA guest -> inet
    return _rad_interact_instance.coa_guest2inet(
        uname=uname,
        speed_in=speed_in,
        speed_out=speed_out,
        speed_in_burst=speed_in_burst,
        speed_out_burst=speed_out_burst
    )
