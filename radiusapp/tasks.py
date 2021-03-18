from time import sleep
from typing import Tuple
import logging
from uwsgi_tasks import task

from djing2.lib import safe_int
from radiusapp.models import CustomerRadiusSession


@task()
def radius_batch_stop_customer_services_task(customer_ids: Tuple[int],
                                             delay_interval=100):
    # TODO: Можно перепроверять сменилась ли услуга у абона,
    # чтоб понять есть-ли всё ещё смысл его переавторизовывать,
    # а то к моменту когда до него дойдёт очередь переавторизовываться
    # он мог уже подключить себе ту же услугу
    sessions = CustomerRadiusSession.objects.filter(
        customer_id__in=customer_ids
    ).only('pk', 'radius_username').iterator()
    for session in sessions:
        r = session.finish_session()
        if r:
            logging.info('Session "%s" finished' % session)
        else:
            logging.info('Session "%s" not finished' % session)
        sleep(delay_interval / 1000)


@task()
def radius_stop_customer_session_task(customer_id: int, delay_interval=100):
    customer_id = safe_int(customer_id)
    session = CustomerRadiusSession.objects.filter(
        customer_id=customer_id
    ).first()
    if session is None:
        logging.exception(
            'session with customer_id="%d" not found' % customer_id)
    if session.finish_session():
        logging.info('Session "%s" finished' % session)
    else:
        logging.info('Session "%s" not finished' % session)
    sleep(delay_interval / 1000)
