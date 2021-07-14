"""Async tasks for radiusapp."""
from typing import Tuple
import logging
from uwsgi_tasks import task, TaskExecutor, SPOOL_OK, SPOOL_RETRY

from radiusapp.models import CustomerRadiusSession
from radiusapp import radius_commands as rc


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=30)
def radius_batch_stop_customer_services_task(customer_ids: Tuple[int]):
    """
    Async COA RADIUS sessions inet->guest.

    :param customer_ids: customers.models.Customer ids
    :return: nothing
    """
    # FIXME: pass to task only data, not params for queryset
    sessions = (
        CustomerRadiusSession.objects.filter(customer_id__in=customer_ids).only("pk", "radius_username").iterator()
    )
    for session in sessions:
        try:
            if not session.radius_coa_inet2guest():
                logging.info('Session "%s" not changed inet -> guest' % session)
        except rc.RadiusBaseException as err:
            logging.error(str(err))
    return SPOOL_OK


Доделать обработку исключений

@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=5)
def async_finish_session_task(radius_uname: str):
    try:
        ret_text = rc.finish_session(radius_uname)
        if ret_text is not None:
            logging.warning(ret_text)
        return SPOOL_OK
    except rc.RadiusSessionNotFoundException as e:
        return SPOOL_OK
    except rc.RadiusTimeoutException as e:
        return SPOOL_RETRY
    except rc.RadiusInvalidRequestException as e:
        pass
    except rc.RadiusMissingAttributeException as e:
        pass


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=5)
def async_change_session_inet2guest(radius_uname: str):
    rc.change_session_inet2guest(radius_uname)
    return SPOOL_OK


#
# Call like this:
# async_change_session_guest2inet(
#     radius_uname: str,
#     speed_in: int,
#     speed_out: int,
#     speed_in_burst: int,
#     speed_out_burst: int
# )
#
@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=5)
def async_change_session_guest2inet(*args, **kwargs):
    rc.change_session_guest2inet(*args, **kwargs)
    return SPOOL_OK
