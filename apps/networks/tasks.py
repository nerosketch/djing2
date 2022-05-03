from datetime import datetime, timedelta
from functools import wraps
from uwsgi_tasks import task, cron, TaskExecutor

from djing2.lib.logger import logger
from djing2.lib.uwsgi_lock import uwsgi
from networks import radius_commands as rc
from networks.models import CustomerIpLeaseModel


@cron(minute=-30)
def periodically_checks_for_stale_leases(signal_number):
    CustomerIpLeaseModel.objects.filter(last_update__lte=datetime.now() - timedelta(days=2), is_dynamic=True).delete()


def _radius_task_wrapper(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            uwsgi.lock()
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
        finally:
            uwsgi.unlock()
    return _wrapped


@task(executor=TaskExecutor.MULE)
@_radius_task_wrapper
def async_finish_session_task(radius_uname: str):
    ret_text = rc.finish_session(radius_uname=radius_uname)
    if ret_text is not None:
        logger.warning("async_finish_session_task: %s" % ret_text)


@task(executor=TaskExecutor.MULE)
@_radius_task_wrapper
def async_change_session_inet2guest(radius_uname: str):
    """
    Async COA RADIUS sessions inet->guest.

    :param radius_uname: radius User-Name value
    :return: nothing
    """
    ret_text = rc.change_session_inet2guest(radius_uname)
    if ret_text is not None:
        logger.warning(ret_text)


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
@task(executor=TaskExecutor.MULE)
@_radius_task_wrapper
def async_change_session_guest2inet(*args, **kwargs):
    ret_text = rc.change_session_guest2inet(*args, **kwargs)
    if ret_text is not None:
        logger.warning(ret_text)

