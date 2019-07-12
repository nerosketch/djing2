from celery import shared_task

from customers.models import Customer
from djing2.lib import LogicError
from gateways.models import Gateway
from gateways.nas_managers import GatewayFailedResult, GatewayNetworkError, SubnetQueue


@shared_task
def customer_gw_command(customer_uid: int, command: str):
    if command not in ('add', 'sync'):
        return 'Command required'
    try:
        sb = Customer.objects.get(pk=customer_uid)
        if command == 'sync':
            r = sb.gw_sync_self()
            if isinstance(r, Exception):
                return 'CUSTOMERS SYNC ERROR: %s' % r
        elif command == 'add':
            sb.gw_add_self()
        else:
            return 'CUSTOMERS SYNC ERROR: Unknown command "%s"' % command
    except Customer.DoesNotExist:
        pass
    except (LogicError, GatewayFailedResult, GatewayNetworkError, ConnectionResetError) as e:
        return 'CUSTOMERS ERROR: %s' % e


@shared_task
def customer_gw_remove(customer_uid: int, ip_addr: str, speed: tuple, is_access: bool, gw_pk: int):
    try:
        if not isinstance(ip_addr, (str, int)):
            ip_addr = str(ip_addr)
        sq = SubnetQueue(
            name="uid%d" % customer_uid,
            network=ip_addr,
            max_limit=speed,
            is_access=is_access
        )
        gw = Gateway.objects.get(pk=gw_pk)
        mngr = gw.get_gw_manager()
        mngr.remove_user(sq)
    except (ValueError, GatewayFailedResult, GatewayNetworkError, LogicError) as e:
        return 'CUSTOMERS ERROR: %s' % e
    except Gateway.DoesNotExist:
        return 'Gateways.DoesNotExist id=%d' % gw_pk
