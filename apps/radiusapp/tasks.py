"""Async tasks for radiusapp."""
from functools import wraps
from uwsgi_tasks import task, TaskExecutor, SPOOL_OK, SPOOL_RETRY

from djing2.lib.logger import logger
from radiusapp import radius_commands as rc


def _radius_task_error_wrapper(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except rc.RadiusSessionNotFoundException:
            return SPOOL_OK
        except rc.RadiusTimeoutException:
            return SPOOL_RETRY
        except rc.RadiusInvalidRequestException:
            # may raised when trying to change to already installed service
            return SPOOL_OK
        # except rc.RadiusMissingAttributeException:
        #    pass
    return _wrapped


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=5)
@_radius_task_error_wrapper
def async_finish_session_task(radius_uname: str):
    ret_text = rc.finish_session(radius_uname)
    if ret_text is not None:
        logger.warning(ret_text)
    return SPOOL_OK


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=15)
@_radius_task_error_wrapper
def async_change_session_inet2guest(radius_uname: str):
    """
    Async COA RADIUS sessions inet->guest.

    :param radius_uname: radius User-Name value
    :return: nothing
    """
    ret_text = rc.change_session_inet2guest(radius_uname)
    if ret_text is not None:
        logger.warning(ret_text)
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
@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=15)
@_radius_task_error_wrapper
def async_change_session_guest2inet(*args, **kwargs):
    ret_text = rc.change_session_guest2inet(*args, **kwargs)
    if ret_text is not None:
        logger.warning(ret_text)
    return SPOOL_OK
