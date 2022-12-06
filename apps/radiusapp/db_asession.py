from asyncpg import Pool, create_pool
from asyncpg.pool import PoolAcquireContext
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from fastapi import Depends


async def pool_dep() -> Pool:
    databases = getattr(settings, 'DATABASES')
    if databases is None:
        raise ImproperlyConfigured('missing DATABASES option in settings')
    db_def = databases.get('default')
    if db_def is None:
        raise ImproperlyConfigured('missing DATABASES default option in settings')
    if db_def['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('You must use postgresql to use this app')
    db_name = db_def['NAME']
    db_user = db_def['USER']
    db_passw = db_def['PASSWORD']
    db_host = db_def['HOST']
    db_port = db_def.get('PORT', 5432)
    pool = await create_pool(
        database=db_name,
        user=db_user,
        password=db_passw,
        host=db_host,
        port=db_port
    )
    print('Ret pool', pool)
    yield pool


async def db_connection_dependency(pool: Pool = Depends(pool_dep)):
    print('Pool:', pool, type(pool))
    async with pool.acquire() as connection:
        print('Connection:', connection, type(connection))
        yield connection
