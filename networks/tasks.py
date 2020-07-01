from datetime import datetime

from uwsgi_tasks import task, TaskExecutor

from gateways.gw_facade import GatewayFacade, GatewayTypes


@task(executor=TaskExecutor.SPOOLER)
def send_signal_dhcp2gateway_add_subscriber_task(lease_id: int, ip_address: str, pool_id: int, lease_time: datetime,
                                                 mac_address: str,
                                                 customer_id: int, is_dynamic: bool, is_assigned: bool):
    gw = GatewayFacade(GatewayTypes.LINUX)
    gw.send_command_add_customer(customer_id=customer_id)
