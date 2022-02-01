#!/usr/bin/env python3
import os
#  from typing import Dict, Generator
from ipaddress import ip_network, IPv4Network
import requests


domain = "http://next.internet-service.com.ru/api"

s = requests.Session()


def make_req(url: str, params=None):
    return s.get(
        url,
        params=params
    )


def get_pools():
    r = make_req(
        url=f"{domain}/networks/pool/",
        params={
            'fields': 'id,network,ip_start,ip_end,vid,is_dynamic'
        }
    )
    if r.status_code != 200:
        raise RuntimeError('Unexpected return code="%d"' % r.status_code)
    return r.json()


def make_name(net: IPv4Network):
    return str(net.network_address).replace('.', '_')


def template(*, ip_start: str, ip_end: str, net: IPv4Network, vid: int) -> str:
    pool_name = make_name(net)
    return """
ippool v%(vid)d_%(pool_name)s_%(pref)d {
	filename = ${localstatedir}/pool/%(pool_name)s.ippool
	range_start = %(ip_start)s
	range_stop = %(ip_end)s
	netmask = %(mask)s
	cache_size = 4
	ip_index = ${localstatedir}/pool/%(pool_name)s.ipindex
	override = no
	maximum_timeout = 0
}""" % {
        'ip_start': ip_start,
        'ip_end': ip_end,
        'pref': net.prefixlen,
        'mask': str(net.netmask),
        'vid': vid,
        'pool_name': pool_name
        }


def main():
    names = []
    for pool in get_pools():
        is_dynamic = pool['is_dynamic']
        if not is_dynamic:
            continue
        net = pool['network']
        ip_start = pool['ip_start']
        ip_end = pool['ip_end']
        #  gateway = pool['gateway']
        vid = pool['vid']
        net = ip_network(net)
        name = f"v%(vid)d_%(pool_name)s_%(pref)d" % {
            'vid': vid,
            'pool_name': make_name(net),
            'pref': net.prefixlen
        }
        names.append(name)
        r = template(
            ip_start=ip_start,
            ip_end=ip_end,
            net=net,
            vid=int(vid)
        )
        print(r)
    for name in names:
        print(name)


if __name__ == '__main__':
    s.headers.update({
        'Authorization': f"Token {os.environ['token']}"
    })
    main()
