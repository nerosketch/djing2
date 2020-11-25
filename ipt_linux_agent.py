#!/usr/bin/env python3
import os
from typing import Tuple

from requests import get as httpget


def diff_set(one: set, two: set) -> Tuple[set, set]:
    list_for_del = (one ^ two) - one
    list_for_add = one - two
    return list_for_add, list_for_del


def get_users_from_biling() -> list:
    credentials = httpget('https://web-domain/api/gateways/fetch_customers_srvnet_credentials_by_gw/', {
        'gw_id': 7
    }, headers={
        'Authorization': 'Token ffffffffffffffffffffffffffffffffffff',
        'Content-type': 'application/json'
    })
    if credentials.status_code != 200:
        exit(1)
    return credentials.json()


class IptRatelimitIntrfc:
    pfile = '/proc/net/ipt_ratelimit/name0'

    @classmethod
    def _w2rl(cls, cmd: str) -> None:
        with open(cls.pfile, 'w') as f:
            f.write("%s\n" % cmd)

    @classmethod
    def _r4rl(cls) -> list:
        with open(cls.pfile, 'r') as f:
            res = f.readlines()
        return res

    @classmethod
    def _ips_a(cls, ip: str):
        os.system("/usr/sbin/ipset add uallowed %s" % ip)

    @classmethod
    def _ips_d(cls, ip: str):
        os.system("/usr/sbin/ipset del uallowed %s" % ip)

    @classmethod
    def add_customer(cls, ip: str, speed: int):
        cls._w2rl(cmd='+%s %d' % (ip, speed))
        cls._ips_a(ip)

    @classmethod
    def del_customer(cls, ip: str):
        cls._w2rl(cmd='@-%s' % ip)
        cls._ips_d(ip)

    @classmethod
    def update_customer(cls, ip, speed):
        cls._r2rl(cmd='@+%s %d' % (ip, speed))

    @classmethod
    def flush_all(cls):
        cls._r2rl(cmd='/')

    @classmethod
    def read_users_from_ipt(cls):
        lns = cls._r4rl()
        if len(lns) == 0:
            return
        for ln in lns:
            if ln is None:
                continue
            # 172.17.0.0/24 cir 1000000 cbs 187500 ebs 375000; tc 0 te 0 last never; conf 0/0 0 bps, rej 0/0
            chunks = ln.split()
            if not chunks:
                continue
            ip = chunks[0]
            speed = chunks[2]
            yield ip, int(speed)


def main():
    # получим всё из билинга
    biling_users = set(
        (ip_address, int(speed_in * 1000000)) for customer_id, lease_id, lease_time,
                                                  lease_mac, ip_address, speed_in,
                                                  *other
        in get_users_from_biling()
    )

    # получим из ядра
    ipt_users = set(i for i in IptRatelimitIntrfc.read_users_from_ipt())

    nets_add, nets_del = diff_set(biling_users, ipt_users)

    for nt in nets_del:
        IptRatelimitIntrfc.del_customer(nt[0])

    for nt in nets_add:
        IptRatelimitIntrfc.add_customer(nt[0], nt[1])


if __name__ == '__main__':
    main()
