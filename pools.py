import asyncpg
import aioredis

import settings
from logger import logger


class GenericPool():
    "Pool de conexiones genérico"

    pool = None


class RedisPool(GenericPool):
    "Pool de conexiones al Redis"

    @classmethod
    async def initialize(cls):
        try:
            cls.pool = await aioredis.create_pool(
                settings.REDIS_URL,
                maxsize=100,
                create_connection_timeout=0.5,
            )
        except aioredis.errors.RedisError as exc:
            logger.error("[] RedisPool.initialize() error: %s", exc)


class PostgresPool(GenericPool):
    "Pool de conexiones a la base de datos"

    @classmethod
    async def initialize(cls):
        try:
            cls.pool = await asyncpg.create_pool(
                max_size=25,
                max_queries=1000,
                max_inactive_connection_lifetime=10.0,
                host=settings.PG_HOST,
                port=settings.PG_PORT,
                user=settings.PG_USER,
                password=settings.PG_PASS,
                database=settings.PG_DATABASE,
            )
        except asyncpg.exceptions.PostgresError as exc:
            logger.error("[] PostgresPool.initialize() error: %s", exc)


__all__ = ["RedisPool", "PostgresPool"]
