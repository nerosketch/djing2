#! /usr/bin/env python3
#
# Python module example file
# Miguel A.L. Paraz <mparaz@mparaz.com>
#
# $Id: 5d437f446e8938beb1d458dc332e4081bf3d5144 $

from collections import OrderedDict
import radiusd
import pools


# Check post_auth for the most complete example using different
# input and output formats

def instantiate(p):
    print("*** instantiate ***")
    print(p)
    # return 0 for success or -1 for failure


def authorize(p):
    print("*** authorize ***")
    radiusd.radlog(radiusd.L_INFO, '*** radlog call in authorize ***')
    print()
    print(p)
    print()
    print(radiusd.config)
    return radiusd.RLM_MODULE_OK


def preacct(p):
    print("*** preacct ***")
    print(p)
    return radiusd.RLM_MODULE_OK


def accounting(p):
    print("*** accounting ***")
    radiusd.radlog(radiusd.L_INFO, '*** radlog call in accounting (0) ***')
    print()
    print(p)
    return radiusd.RLM_MODULE_OK


def pre_proxy(p):
    print("*** pre_proxy ***")
    print(p)
    return radiusd.RLM_MODULE_OK


def post_proxy(p):
    print("*** post_proxy ***")
    print(p)
    return radiusd.RLM_MODULE_OK


guest_pool_name = pools.guest_net.get('name', 'DEFAULT')
guest_ret_tuple = (('Pool-Name', guest_pool_name), ('Auth-Type', 'Accept'))


def post_auth(p):
    # print("*** post_auth ***")

    if isinstance(p, tuple):
        p = OrderedDict(p)

    if isinstance(p, (dict, OrderedDict)):
        vid = p.get('NAS-Port-Id')
        if vid is None:
            radiusd.radlog(radiusd.L_WARN, '*** Empty vid ***')
            update_tup = guest_ret_tuple
        else:
            vid = int(vid.replace('ae0:1011-', ''))
            pool_names = pools.pool_dict.get(vid)

            if pool_names is None or len(pool_names) < 1:
                radiusd.radlog(radiusd.L_WARN, '*** Empty pool names ***')
                update_tup = guest_ret_tuple
            else:
                # FIXME: multiple names for vid
                update_tup = (('Pool-Name', pool_names[0]), ('Auth-Type', 'Accept'))
    else:
        radiusd.radlog(radiusd.L_DBG_ERR_REQ, 'p Type='+str(type(p)))
        return radiusd.RLM_MODULE_FAIL

    # Dictionary representing changes we want to make to the different VPS
    # update_dict = {
    #      "request": (("User-Password", ":=", "A new password"),),
    #      "reply": (("Reply-Message", "The module is doing its job"),
    #                ("User-Name", "NewUserName")),
    #      "config": (("Cleartext-Password", "A new password"),),
    # }

    return radiusd.RLM_MODULE_OK, (), update_tup


def recv_coa(p):
    print("*** recv_coa ***")
    print(p)
    return radiusd.RLM_MODULE_OK


def send_coa(p):
    print("*** send_coa ***")
    print(p)
    return radiusd.RLM_MODULE_OK


def detach():
    print("*** goodbye from example.py ***")
    return radiusd.RLM_MODULE_OK
