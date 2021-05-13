"""Async tasks for radiusapp."""
from typing import Tuple
import logging
from uwsgi_tasks import task, TaskExecutor, SPOOL_OK, SPOOL_RETRY

from radiusapp.models import CustomerRadiusSession
from .radius_commands import finish_session, change_session_inet2guest, change_session_guest2inet


@task()
def radius_batch_stop_customer_services_task(customer_ids: Tuple[int]):
    """
    Async COA RADIUS sessions inet->guest.

    :param customer_ids: customers.models.Customer ids
    :return: nothing
    """
    sessions = (
        CustomerRadiusSession.objects.filter(customer_id__in=customer_ids).only("pk", "radius_username").iterator()
    )
    for session in sessions:
        if session.radius_coa_inet2guest():
            logging.info('Session "%s" changed inet -> guest' % session)
        else:
            logging.info('Session "%s" not changed inet -> guest' % session)


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_count=3, retry_timeout=5)
def async_finish_session_task(radius_uname: str):
    try:
        if finish_session(radius_uname):
            return SPOOL_OK
    except Exception:
        pass
    return SPOOL_RETRY


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_count=2, retry_timeout=5)
def async_change_session_inet2guest(radius_uname: str):
    try:
        if change_session_inet2guest(radius_uname):
            return SPOOL_OK
    except Exception:
        pass
    return SPOOL_RETRY


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
@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_count=2, retry_timeout=5)
def async_change_session_guest2inet(*args, **kwargs):
    try:
        if change_session_guest2inet(*args, **kwargs):
            return SPOOL_OK
    except Exception:
        pass
    return SPOOL_RETRY
