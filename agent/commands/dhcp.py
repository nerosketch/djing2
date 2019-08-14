from typing import Optional
from django.core.exceptions import MultipleObjectsReturned
from customers.models import Customer
from devices.models import Device, Port


def dhcp_commit(client_ip: str, client_mac: str,
                switch_mac: str, switch_port: int) -> Optional[str]:
    try:
        dev = Device.objects.get(mac_addr=switch_mac)
        mngr_class = dev.get_manager_klass()

        if mngr_class.get_is_use_device_port():
            customer = Customer.objects.get(
                dev_port__device=dev,
                dev_port__num=switch_port,
                device=dev, is_active=True
            )
        else:
            customer = Customer.objects.get(device=dev, is_active=True)
        if not customer.is_dynamic_ip:
            return 'User settings is not dynamic'
        if client_ip == str(customer.ip_address):
            return 'Ip has already attached'
        customer.attach_ip_addr(client_ip, strict=False)
        if customer.is_access():
            r = customer.gw_sync_self()
            return r or None
        else:
            return 'User %s is not access to service' % customer.username
    except Customer.DoesNotExist:
        return "User with device with mac '%s' does not exist" % switch_mac
    except Device.DoesNotExist:
        return 'Device with mac %s not found' % switch_mac
    except Port.DoesNotExist:
        return 'Port %(switch_port)d on device with mac %(switch_mac)s does not exist' % {
            'switch_port': int(switch_port),
            'switch_mac': switch_mac
        }
    except MultipleObjectsReturned as e:
        return 'MultipleObjectsReturned:' + ' '.join(
            (type(e), e, str(switch_port))
        )


def dhcp_expiry(client_ip: str) -> Optional[str]:
    customer = Customer.objects.filter(
        ip_address=client_ip, is_active=True
    ).exclude(current_service=None).first()
    if customer is None:
        return "Subscriber with ip %s does not exist" % client_ip
    else:
        is_freed = customer.free_ip_addr()
        if is_freed:
            customer.gw_sync_self()


def dhcp_release(client_ip: str) -> Optional[str]:
    return dhcp_expiry(client_ip)
