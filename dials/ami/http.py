from requests import post
from requests.compat import urljoin

from .call import DialChannel, join_call_log
from .opts import WEB_HOST, WEB_TOKEN


def send_dial(ch: DialChannel):
    return post(
        urljoin(WEB_HOST, 'dial/dial-log/'),
        data=join_call_log(ch),
        headers={
            'Authorization': 'Token %s' % WEB_TOKEN
        }
    )
