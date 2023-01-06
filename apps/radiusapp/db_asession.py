from typing import Optional
from asyncpg import Pool, create_pool
from asyncpg.pool import PoolConnectionProxy
from django.db import connection
from django.core.exceptions import ImproperlyConfigured
from fastapi import Depends


async def pool_dep() -> Pool:
    db_def = connection.settings_dict
    if not db_def:
        raise ImproperlyConfigured('missing DATABASES default option in settings')
    if db_def['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('You must use postgresql to use this app')
    db_name = db_def['NAME']
    db_user = db_def['USER']
    db_passw = db_def['PASSWORD']
    db_host = db_def['HOST']
    db_port = db_def.get('PORT', 5432)
    pool = await create_pool(
        statement_cache_size=0,
        database=db_name,
        user=db_user,
        password=db_passw,
        host=db_host,
        port=db_port
    )
    return pool


class PoolPers:
    _pool: Optional[Pool] = None

    async def __call__(self):
        if not self._pool:
            self._pool = await pool_dep()
        return self._pool


async def db_connection_dependency(pool: Pool = Depends(PoolPers())) -> PoolConnectionProxy:
    async with pool.acquire() as conn:
        yield conn
