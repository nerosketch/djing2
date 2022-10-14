from datetime import datetime, timedelta
from functools import wraps

from djing2 import celery_app
from djing2.lib.logger import logger
from networks import radius_commands as rc
from networks.models import CustomerIpLeaseModel


@celery_app.task
def periodically_checks_for_stale_leases():
    CustomerIpLeaseModel.objects.filter(
        last_update__lte=datetime.now() - timedelta(days=2),
        is_dynamic=True
    ).release()


celery_app.add_periodic_task(
    1800,
    periodically_checks_for_stale_leases.s(),
    name='Periodically checks for stale leases'
)


def _radius_task_wrapper(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except rc.RadiusSessionNotFoundException as err:
            logger.error('Radius session not found: %s' % str(err))
        except rc.RadiusTimeoutException as err:
            logger.error('Radius timeout: %s' % str(err))
        except rc.RadiusInvalidRequestException as err:
            # may raised when trying to change to already installed service
            logger.error('Radius invalid request: %s' % str(err))
        except rc.RadiusMissingAttributeException as err:
            logger.error('Radius missing attribute: %s' % str(err))
    return _wrapped


@celery_app.task
@_radius_task_wrapper
def async_finish_session_task(radius_uname: str):
    ret_text = rc.finish_session(radius_uname=radius_uname)
    if ret_text is not None:
        logger.info("async_finish_session_task: %s" % ret_text)


@celery_app.task
@_radius_task_wrapper
def async_change_session_inet2guest(radius_uname: str):
    """
    Async COA RADIUS sessions inet->guest.

    :param radius_uname: radius User-Name value
    :return: nothing
    """
    ret_text = rc.change_session_inet2guest(radius_uname)
    if ret_text is not None:
        logger.info('inet2guest: %s' % ret_text)


@celery_app.task
@_radius_task_wrapper
def async_change_session_guest2inet(radius_uname: str, speed_in: int,
                                    speed_out: int, speed_in_burst: int,
                                    speed_out_burst: int):
    ret_text = rc.change_session_guest2inet(
        radius_uname=radius_uname,
        speed_in=speed_in,
        speed_out=speed_out,
        speed_in_burst=speed_in_burst,
        speed_out_burst=speed_out_burst
    )
    if ret_text is not None:
        logger.info('guest2inet: %s' % ret_text)


@celery_app.task
@_radius_task_wrapper
def check_if_lease_have_ib_db_task(radius_uname: str):
    uleases = CustomerIpLeaseModel.objects.filter(
        radius_username=radius_uname
    )
    if not uleases.exists():
        logger.warning('ORPHAN lease drop uname="%s"' % radius_uname)
        rc.finish_session(radius_uname=radius_uname)
