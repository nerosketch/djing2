from typing import Union

import redis
from django.conf import settings
from redis.typing import KeyT, EncodableT, ExpiryT, AbsExpiryT

REDIS_HOST = getattr(settings, 'REDIS_HOST', 'djing2redis')
REDIS_PORT = getattr(settings, 'REDIS_PORT', 6379)

_redis_connection = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    # decode_responses=True
)


class RedisProxy:
    _redis_connection: redis.Redis

    def __init__(self):
        self._redis_connection = _redis_connection

    def get(self, name: KeyT):
        return self._redis_connection.get(
            name=name,
        )

    def set(
        self,
        name: KeyT,
        value: EncodableT,
        ex: Union[ExpiryT, None] = None,
        px: Union[ExpiryT, None] = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: Union[AbsExpiryT, None] = None,
        pxat: Union[AbsExpiryT, None] = None,
    ):
        return self._redis_connection.set(
            name=name,
            value=value,
            ex=ex,
            px=px,
            nx=nx,
            xx=xx,
            keepttl=keepttl,
            get=get,
            exat=exat,
            pxat=pxat
        )


redis_proxy = RedisProxy()
