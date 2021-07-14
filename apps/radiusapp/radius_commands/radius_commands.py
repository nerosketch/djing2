import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pyrad.client import Client
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


class RadiusInteract:
    client = Client(server=ADDRESS, secret=SECRET, dict=dictionary.Dictionary(_abspath("dictionary")))
    # client.timeout = 30

    def coa_inet2guest(self, uname: str):
        attrs = {
            'User-Name': uname,
            'ERX-Service-Deactivate': 'SERVICE-INET',
            'ERX-Service-Activate:1': 'SERVICE-GUEST'
        }
        return self.coa(uname=uname, **attrs)

    def coa_guest2inet(self, uname: str, speed_in: int, speed_out: int, speed_in_burst: int, speed_out_burst: int):
        attrs = {
            'User-Name': uname,
            'ERX-Service-Deactivate': 'SERVICE-GUEST',
            'ERX-Service-Activate:1': f'SERVICE-INET({speed_in},{speed_in_burst},{speed_out},{speed_out_burst})'
        }
        return self.coa(uname=uname, **attrs)

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

    def _process_request(self, request):
        res = self.client.SendPacket(request)
        if res.code in (packet.CoAACK, packet.AccessAccept, packet.DisconnectACK):
            # ok
            pass
        for i in res.keys():
            print("%s: %s" % (i, res.get(i)))
        return res


_rad_interact_instance = RadiusInteract()


def _filter_uname(uname: str) -> str:
    _uname = str(uname)
    _uname = _uname.replace('"', "")
    _uname = _uname.replace("'", "")
    return _uname


def finish_session(radius_uname: str) -> bool:
    """Send radius disconnect packet to BRAS."""
    if not radius_uname:
        return False
    uname = _filter_uname(radius_uname)
    return _rad_interact_instance.disconnect(uname=uname)


def change_session_inet2guest(radius_uname: str) -> bool:
    if not radius_uname:
        return False
    uname = _filter_uname(radius_uname)
    # COA inet -> guest
    return _rad_interact_instance.coa_inet2guest(uname=uname)


def change_session_guest2inet(
    radius_uname: str, speed_in: int, speed_out: int, speed_in_burst: int, speed_out_burst: int
) -> bool:
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
        return False
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
