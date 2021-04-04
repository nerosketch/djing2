"""Async tasks for radiusapp."""
from time import sleep
from typing import Tuple
import logging
from uwsgi_tasks import task

from djing2.lib import safe_int
from radiusapp.models import CustomerRadiusSession


@task()
def radius_batch_stop_customer_services_task(customer_ids: Tuple[int], delay_interval=100):
    """
    Async resetting RADIUS sessions for customers.

    :param customer_ids: customers.models.Customer ids
    :param delay_interval: time to sleep after reset in ms.
    :return: nothing
    """
    # TODO: Можно перепроверять сменилась ли услуга у абона,
    # чтоб понять есть-ли всё ещё смысл его переавторизовывать,
    # а то к моменту когда до него дойдёт очередь переавторизовываться
    # он мог уже подключить себе ту же услугу
    sessions = (
        CustomerRadiusSession.objects.filter(customer_id__in=customer_ids).only("pk", "radius_username").iterator()
    )
    for session in sessions:
        if session.finish_session():
            logging.info('Session "%s" finished' % session)
        else:
            logging.info('Session "%s" not finished' % session)
        sleep(delay_interval / 1000)


@task()
def radius_stop_customer_session_task(customer_id: int, delay_interval=100):
    """
    Async resetting RADIUS session 4 single customer.

    :param customer_id: customers.models.Customer id.
    :param delay_interval: time to sleep after reset each session in ms.
    :return: nothing
    """
    customer_id = safe_int(customer_id)
    sessions = CustomerRadiusSession.objects.filter(customer_id=customer_id).iterator()
    for session in sessions:
        if session.finish_session():
            logging.info('Session "%s", 4 customer_id="%d" finished.' % (session, customer_id))
        else:
            logging.info('Session "%s", 4 customer_id="%d" not finished.' % (session, customer_id))
        sleep(delay_interval / 1000)