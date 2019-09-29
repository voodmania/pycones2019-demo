from starlette.applications import Starlette
from starlette.routing import Mount, Route, Router

import settings
from logger import logger
from pools import RedisPool, PostgresPool
from views import HomeView, AutocompleteView, PrevisionView
from middleware import SessionMiddleware, AuditMiddleware


# app init

app = Starlette()
app.add_middleware(SessionMiddleware)
if settings.AUDIT:
    app.add_middleware(AuditMiddleware)


# app events

@app.on_event('startup')
async def setup_pools():
    "Inicializa los pools de conexión de Redis y Postgresql"

    await RedisPool.initialize()
    await PostgresPool.initialize()

    if PostgresPool.pool and settings.AUDIT:
        await PostgresPool.pool.execute(AuditMiddleware.TABLE_CREATION)

    all_ok = all([_.pool is not None for _ in [RedisPool, PostgresPool]])
    logger.debug("[] setup_pools() ok: %s", all_ok)


@app.on_event('shutdown')
async def teardown_pools():
    "Cierra los pools de conexión de Redis y Postgresql"

    if RedisPool.pool:
        RedisPool.pool.close()

    if PostgresPool.pool:
        await PostgresPool.pool.close()

    logger.debug("[] teardown_pools()")


# app routing

app.mount('', Router([
    Route('/', endpoint=HomeView, methods=['GET']),
    Route('/autocomplete', endpoint=AutocompleteView, methods=['GET']),
    Route('/prevision/{localidad_id:int}/', endpoint=PrevisionView, methods=['GET']),
]))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
