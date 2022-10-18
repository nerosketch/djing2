from functools import wraps
from starlette import status
from fastapi import HTTPException


def catch_customers_errs(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TimeoutError as e:
            raise HTTPException(
                detail=str(e),
                status_code=status.HTTP_408_REQUEST_TIMEOUT
            ) from e

    return wrapper
