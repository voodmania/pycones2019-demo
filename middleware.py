import json
import pickle
import asyncio
import secrets

from starlette.middleware.base import BaseHTTPMiddleware

from aioredis.errors import RedisError
from asyncpg.exceptions import PostgresError, InterfaceError

import settings
from logger import logger
from pools import RedisPool, PostgresPool


class SessionMiddleware(BaseHTTPMiddleware):
    "Carga de los datos de sesión"

    async def dispatch(self, request, call_next):
        request.state.session = {}
        request.state.session_id = request.cookies.get("session_id")
        if not request.state.session_id:
            request.state.session_id = secrets.token_urlsafe()

        if RedisPool.pool:
            try:
                raw_session = await RedisPool.pool.execute(
                    "get", f"session:{request.state.session_id}")
                if raw_session:
                    request.state.session = pickle.loads(raw_session)
            except RedisError as exc:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() redis get error: %s",
                    request.state.session_id, exc
                )
            except pickle.PickleError as exc:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() loads error: %s",
                    request.state.session_id, exc
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() get timeout, connections: %d, closed: %s",
                    request.state.session_id, RedisPool.pool.size, RedisPool.pool.closed
                )

        response = await call_next(request)

        response.set_cookie("session_id", request.state.session_id)
        if RedisPool.pool:
            try:
                raw_session = pickle.dumps(request.state.session)
                await RedisPool.pool.execute(
                    "set", f"session:{request.state.session_id}", raw_session)
            except RedisError as exc:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() redis set error: %s",
                    request.state.session_id, exc
                )
            except pickle.PickleError as exc:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() dumps error: %s",
                    request.state.session_id, exc
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[%s] SessionMiddleware.dispatch() set timeout, connections: %d, closed: %s",
                    request.state.session_id, RedisPool.pool.size, RedisPool.pool.closed
                )

        return response


class AuditMiddleware(BaseHTTPMiddleware):
    "Grabación de datos de auditoría en la base de datos"

    # definición de la tabla usada para guardar los datos de auditoría
    TABLE_CREATION = """\
BEGIN;
CREATE TABLE IF NOT EXISTS audit(
    access_at Timestamp With Time Zone DEFAULT now() NOT NULL,
    session_id Character Varying(100) NOT NULL,
    method Character Varying(20),
    path Character Varying(2044) NOT NULL,
    response SmallInt,
    input JSONB,
    output JSONB
);
CREATE INDEX IF NOT EXISTS index_access_at ON audit USING btree(access_at Asc NULLS Last);
CREATE INDEX IF NOT EXISTS index_session_id ON audit USING btree(session_id Asc NULLS Last);
CREATE INDEX IF NOT EXISTS index_path ON audit USING btree(path Asc NULLS Last);
COMMIT;
"""

    TABLE_INSERT = """\
INSERT INTO audit(session_id, method, path, response, input, output)
VALUES($1, $2, $3, $4, $5, $6);
"""

    async def dispatch(self, request, call_next):
        request.state.input = None
        request.state.output = None
        response = await call_next(request)

        if PostgresPool.pool:
            try:
                await PostgresPool.pool.execute(
                    AuditMiddleware.TABLE_INSERT,
                    request.state.session_id,
                    request.method,
                    request.url.path,
                    response.status_code,
                    json.dumps(request.state.input),
                    json.dumps(request.state.output),
                    timeout=settings.POSTGRES_TIMEOUT
                )
            except TypeError as exc:
                logger.error(
                    "[%s] AuditMiddleware.dispatch() json error: %s",
                    request.state.session_id, exc
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[%s] AuditMiddleware.dispatch() timeout",
                    request.state.session_id
                )
            except (PostgresError, InterfaceError) as exc:
                logger.error(
                    "[%s] AuditMiddleware.dispatch() db error: %s",
                    request.state.session_id, exc
                )

        return response


__all__ = ["SessionMiddleware", "AuditMiddleware"]
