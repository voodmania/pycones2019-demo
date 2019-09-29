import pickle
import asyncio
from time import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.endpoints import HTTPEndpoint
from starlette.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

import aiohttp
from bs4 import BeautifulSoup
from asyncpg.exceptions import PostgresError

import settings
from logger import logger
from pools import RedisPool, PostgresPool


timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)


class CustomEndpoint(HTTPEndpoint):
    "Endpoint que permite configurar cacheo de datos y hace log de las peticiones"

    cache = None  # int con los segundos que se cachea la petición

    def __init__(self, scope, receive, send):
        super().__init__(scope, receive, send)
        self.session_id = None

    async def _get_response(self, request):
        handler_name = "get" if request.method == "HEAD" else request.method.lower()
        handler = getattr(self, handler_name, self.method_not_allowed)

        if asyncio.iscoroutinefunction(handler):
            return await handler(request)

        return await run_in_threadpool(handler, request)

    async def dispatch(self):
        init_time, request, response = time(), Request(self.scope, receive=self.receive), None
        self.session_id = request.state.session_id

        if RedisPool.pool and isinstance(self.cache, int):
            try:
                cache_data = await RedisPool.pool.execute(
                    "get", f"cache:{request.url.path}")

                if cache_data:
                    response = pickle.loads(cache_data)
                else:
                    response = await self._get_response(request)
                    if response.status_code == 200:  # solo guardamos en cache respuestas OK
                        await RedisPool.pool.execute(
                            "set", f"cache:{request.url.path}", pickle.dumps(response), "ex", self.cache)
            except asyncio.TimeoutError:
                logger.error(
                    "[%s] CustomEndpoint.dispatch() redis timeout, connections: %d, closed: %s",
                    self.session_id, RedisPool.pool.size, RedisPool.pool.closed
                )

        if not response:
            response = await self._get_response(request)

        logger.debug(
            "[%s] CustomEndpoint().dispatch() method: %s path: %s status_code: %s in %d ms",
            self.session_id, request.method, request.url.path, response.status_code, (time() - init_time) * 1000
        )

        await response(self.scope, self.receive, self.send)


class HomeView(CustomEndpoint):
    async def get(self, request):
        # import pdb; pdb.set_trace()
        context = {
            "request": request,
            "ultima_prevision": request.state.session.get('ultima_prevision'),
        }
        return Jinja2Templates(directory="templates").TemplateResponse("index.html", context)


class AutocompleteView(CustomEndpoint):
    async def get(self, request):
        content, status_code = {}, 200
        q = request.query_params.get('q')
        if q and PostgresPool.pool:
            try:
                results = await PostgresPool.pool.fetch(
                    "SELECT id, localidad FROM aemet WHERE unaccent(localidad) ILIKE unaccent($1) ORDER BY localidad LIMIT 10;",
                    f'%{q}%'
                )
                content = [{'value':_.get('id'), 'text':_.get('localidad')} for _ in results]
            except PostgresError as exc:
                logger.error("[%s] AutocompleteView.get(q: %s) %s", self.session_id, q, exc)
        return JSONResponse(content=content, status_code=status_code)


class PrevisionView(CustomEndpoint):
    cache = 3600

    async def get(self, request):
        content, status_code = {}, 404
        localidad_id = request.path_params.get("localidad_id")
        localidad, url_xml = await self._get_localidad_url_xml(localidad_id)
        if url_xml:
            content, status_code = await self._get_content(url_xml), 200
            content["localidad"] = localidad
            request.state.session['ultima_prevision'] = localidad, localidad_id
        else:
            logger.warning("[%s] PrevisionView.get() localidad_id: %s no encontrado", self.session_id, localidad_id)

        return JSONResponse(content=content, status_code=status_code)

    async def _get_localidad_url_xml(self, localidad_id):
        if PostgresPool.pool:
            try:
                result = await PostgresPool.pool.fetchrow("SELECT localidad, url_xml FROM aemet WHERE id = $1;", localidad_id)
                if result:
                    return result.get("localidad"), result.get("url_xml")
            except PostgresError as exc:
                logger.error("[%s] PrevisionView._get_localidad_url_xml(localidad_id: %s) %s", self.session_id, localidad_id, exc)

    async def _get_content(self, url):
        content = {}
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                logger.debug("[%s] PrevisionView._get_content(url: %s) status: %d", self.session_id, url, resp.status)
                if resp.status < 300:
                    soup = BeautifulSoup(await resp.read(), "lxml")
                    dia = soup.find_all("dia")[0]
                    content['prob_precipitacion'] = dia.select("prob_precipitacion[periodo='00-24']")[0].text
                    content['estado_cielo'] = dia.select("estado_cielo[periodo='00-24']")[0].attrs["descripcion"]
                    content['temperatura_max'] = dia.select("temperatura maxima")[0].text
                    content['temperatura_min'] = dia.select("temperatura minima")[0].text
                    content['uv_max'] = dia.select("uv_max")[0].text

        return content


__all__ = ["HomeView", "AutocompleteView", "PrevisionView"]
