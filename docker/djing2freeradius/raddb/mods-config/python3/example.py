#! /usr/bin/env python3
#
# Python module example file
# Miguel A.L. Paraz <mparaz@mparaz.com>
#
# $Id: 5d437f446e8938beb1d458dc332e4081bf3d5144 $

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


def post_auth(p):
    print("*** post_auth ***")
    radiusd.radlog(radiusd.L_INFO, '*** post_auth ***')
    update_dict = {
        'config': (('Pool-Name', 'v104_10_152_2_0_23'),)
    }

    return radiusd.RLM_MODULE_OK, update_dict

    if isinstance(p, dict):
        vid = p.get('NAS-Port-Id')
        if vid is None:
            guest_net_name = pools.guest_net.get('name', 'DEFAULT')
            update_dict = {
                'config': (('Pool-Name', guest_net_name),)
            }
        else:
            pool_net = pools.pool_dict.get(vid)
            if pool_net is None:
                update_dict = pools.guest_net
            else:
                pool_net_name = pool_net.get('name')
                if pool_net_name is None:
                    guest_net_name = pools.guest_net.get('name', 'DEFAULT')
                    update_dict = {
                        'config': (('Pool-Name', guest_net_name),)
                    }
                else:
                    update_dict = {
                        'config': (('Pool-Name', pool_net_name),)
                    }

    # This is true when using pass_all_vps_dict
    if isinstance(p, dict):
        print("Request:", p["request"])
        print("Reply:", p["reply"])
        print("Config:", p["config"])
        print("State:", p["session-state"])
        print("Proxy-Request:", p["proxy-request"])
        print("Proxy-Reply:", p["proxy-reply"])

    else:
        print(p)

    # Dictionary representing changes we want to make to the different VPS
    # update_dict = {
    #      "request": (("User-Password", ":=", "A new password"),),
    #      "reply": (("Reply-Message", "The module is doing its job"),
    #                ("User-Name", "NewUserName")),
    #      "config": (("Cleartext-Password", "A new password"),),
    # }

    return radiusd.RLM_MODULE_OK, update_dict
    # Alternatively, you could use the legacy 3-tuple output
    # (only reply and config can be updated)
    # return radiusd.RLM_MODULE_OK, update_dict["reply"], update_dict["config"]


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
