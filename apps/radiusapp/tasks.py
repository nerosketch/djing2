"""Async tasks for radiusapp."""
from typing import Tuple
import logging
from uwsgi_tasks import task

from radiusapp.models import CustomerRadiusSession
from .radius_commands import finish_session, change_session_inet2guest, change_session_guest2inet


@task()
def radius_batch_stop_customer_services_task(customer_ids: Tuple[int]):
    """
    Async COA RADIUS sessions inet->guest.

    :param customer_ids: customers.models.Customer ids
    :return: nothing
    """
    # TODO: Можно перепроверять сменилась ли услуга у абона,
    #  чтоб понять есть-ли всё ещё смысл останавливать его услугу,
    #  а то к моменту, когда до него дойдёт очередь останавливаться,
    #  он мог уже подключить себе новую услугу.
    sessions = (
        CustomerRadiusSession.objects.filter(customer_id__in=customer_ids).only("pk", "radius_username").iterator()
    )
    for session in sessions:
        if session.radius_coa_inet2guest():
            logging.info('Session "%s" changed inet -> guest' % session)
        else:
            logging.info('Session "%s" not changed inet -> guest' % session)


# @task()
# def async_finish_session_task(radius_uname: str):
#     finish_session(radius_uname)

async_finish_session_task = task(finish_session)


# @task()
# def async_change_session_inet2guest(radius_uname: str):
#     change_session_inet2guest(
#         radius_uname=radius_uname
#     )

#
# Call like this:
# async_change_session_inet2guest(radius_uname: str)
#
async_change_session_inet2guest = task(change_session_inet2guest)


# @task()
# def async_change_session_guest2inet(
#     radius_uname: str,
#     speed_in: int,
#     speed_out: int,
#     speed_in_burst: int,
#     speed_out_burst: int):
#     change_session_guest2inet(
#         radius_uname=radius_uname,
#         speed_in=speed_in,
#         speed_out=speed_out,
#         speed_in_burst=speed_in_burst,
#         speed_out_burst=speed_out_burst
#     )

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
async_change_session_guest2inet = task(change_session_guest2inet)
