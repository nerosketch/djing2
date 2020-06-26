from uwsgi_tasks import task, TaskExecutor

# from customers.models import Customer


@task(executor=TaskExecutor.SPOOLER)
def customer_gw_command_sync(customer_id: int):
    pass
    # try:
    #     customer = Customer.objects.get(pk=customer_id)
    #     r = customer.gw_sync_self()
    #
    #
    #     if self.gateway is None:
    #         raise LogicError(_('gateway required'))
    #     try:
    #         agent_struct = self.build_agent_struct()
    #         if agent_struct is not None:
    #             mngr = self.gateway.get_gw_manager()
    #             mngr.update_user(agent_struct)
    #     except (GatewayFailedResult, GatewayNetworkError, ConnectionResetError) as e:
    #         print('ERROR:', e)
    #         return e
    #     except LogicError:
    #         pass
    #
    #
    #     if isinstance(r, Exception):
    #         return 'Customer Sync Error: %s' % r
    # except Customer.DoesNotExist:
    #     pass
    # except Exception as er
    #     return 'Unexpected error: "%s"' % er


@task(executir=TaskExecutor.SPOOLER)
def customer_gw_command_add(customer_id: int):
    pass
    # try:
    #     customer = Customer.objects.get(pk=customer_id)
    #     r = customer.gw_add_self()
    #
    #
    #     if self.gateway is None:
    #         raise LogicError(_('gateway required'))
    #     try:
    #         agent_struct = self.build_agent_struct()
    #         if agent_struct is not None:
    #             mngr = self.gateway.get_gw_manager()
    #             mngr.add_user(agent_struct)
    #     except (GatewayFailedResult, GatewayNetworkError, ConnectionResetError) as e:
    #         print('ERROR:', e)
    #         return e
    #     except LogicError:
    #         pass
    #
    #
    #
    #     if isinstance(r, Exception):
    #         return 'Customer Adding Error: %s' % r
    # except Customer.DoesNotExist:
    #     pass
    # except Exception as er
    #     return 'Unexpected error: "%s"' % er


@task(executor=TaskExecutor.SPOOLER)
def customer_gw_command_remove(customer_id: int):
    pass
    # try:
    #     if not isinstance(ip_addr, (str, int)):
    #         ip_addr = str(ip_addr)
    #     sq = SubnetQueue(
    #         name="uid%d" % customer_uid,
    #         network=ip_addr,
    #         max_limit=speed,
    #         is_access=is_access
    #     )
    #     nas = NASModel.objects.get(pk=nas_pk)
    #     mngr = nas.get_nas_manager()
    #     mngr.remove_user(sq)
    # except (ValueError, NasFailedResult, NasNetworkError, LogicError) as e:
    #     return 'ABONAPP ERROR: %s' % e
    # except NASModel.DoesNotExist:
    #     return 'NASModel.DoesNotExist id=%d' % nas_pk
