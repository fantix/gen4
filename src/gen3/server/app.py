import asyncio

import click
import edgedb
import pkg_resources
from fastapi import FastAPI, Depends, APIRouter
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from . import logger, config
from .utils import ensure_module


class Application(FastAPI):
    def __init__(self):
        super().__init__(
            title="Gen3 Data Commons",
            version=pkg_resources.get_distribution("gen3").version,
            debug=config.DEBUG,
            openapi_url=config.SERVER_URL_PREFIX + "/openapi.json",
            docs_url=None,
            redoc_url=None,
            swagger_ui_oauth2_redirect_url=None,
        )
        self._pool = None

    @property
    def pool(self):
        if self._pool is None:
            self._pool = asyncio.Future()
        return self._pool

    def pop_pool(self):
        try:
            return self._pool
        finally:
            self._pool = None


app = Application()
api = APIRouter()


class Pool(edgedb.AsyncIOPool):
    def __repr__(self):
        # noinspection PyProtectedMember
        return "<{classname} max={max} min={min} cur={cur} use={use}>".format(
            classname=self.__class__.__name__,
            max=self._maxsize,
            min=self._minsize,
            cur=len(
                [0 for con in self._holders if con._con and not con._con.is_closed()]
            ),
            use=len([0 for con in self._holders if con._in_use]),
        )

    @property
    def colored_repr(self):
        # noinspection PyProtectedMember
        return "<{classname} max={max} min={min} cur={cur} use={use}>".format(
            classname=click.style(self.__class__.__name__, fg="green"),
            max=click.style(repr(self._maxsize), fg="cyan"),
            min=click.style(repr(self._minsize), fg="cyan"),
            cur=click.style(
                repr(
                    len(
                        [
                            0
                            for con in self._holders
                            if con._con and not con._con.is_closed()
                        ]
                    )
                ),
                fg="cyan",
            ),
            use=click.style(
                repr(len([0 for con in self._holders if con._in_use])), fg="cyan"
            ),
        )


class Connection(edgedb.asyncio_con.AsyncIOConnection):
    def transaction(self, *, isolation=None, readonly=None, deferrable=None):
        return Transaction(self, isolation, readonly, deferrable)


class _Commit(BaseException):
    pass


class _Rollback(BaseException):
    pass


class Transaction(edgedb.transaction.AsyncIOTransaction):
    async def __aenter__(self):
        await super().__aenter__()
        return self

    async def __aexit__(self, extype, ex, tb):
        if extype is not None and extype is not _Commit:
            await super().__aexit__(extype, ex, tb)
            if extype is _Rollback:
                return True
        else:
            await super().__aexit__(None, None, None)

    def raise_commit(self):
        raise _Commit()

    def raise_rollback(self):
        raise _Rollback()


class ClientDisconnectMiddleware:
    def __init__(self, app_):
        self._app = app_

    async def __call__(self, scope, receive, send):
        loop = asyncio.get_running_loop()
        rv = loop.create_task(self._app(scope, receive, send))
        waiter = None
        cancelled = False
        if scope["type"] == "http":

            def add_close_watcher():
                nonlocal waiter

                async def wait_closed():
                    nonlocal cancelled
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            if not rv.done():
                                cancelled = True
                                rv.cancel()
                            break

                waiter = loop.create_task(wait_closed())

            scope["add_close_watcher"] = add_close_watcher
        try:
            await rv
        except asyncio.CancelledError:
            if not cancelled:
                raise
        if waiter and not waiter.done():
            waiter.cancel()


@app.on_event("startup")
async def create_db_pool():
    args = dict(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        admin=config.DB_ADMIN,
        database=config.DB_DATABASE,
        timeout=config.DB_CONNECT_TIMEOUT,
        min_size=config.DB_MIN_SIZE,
        max_size=config.DB_MAX_SIZE,
    )
    args_not_none = [(k, v) for k, v in args.items() if v is not None]
    msg = "Creating database connection pool: "
    logger.info(
        msg + ", ".join(f"{k}={v}" for k, v in args.items() if v is not None),
        extra={
            "color_message": msg
            + ", ".join(
                f"{k}={click.style(repr(v), fg='cyan')}" for k, v in args_not_none
            )
        },
    )
    assert app.pool is not None
    pool = await Pool(
        **args,
        password=str(config.DB_PASSWORD),
        on_acquire=None,
        on_connect=None,
        on_release=None,
        connection_class=Connection,
    )
    app.pool.set_result(pool)
    msg = "Database connection pool created: "
    logger.info(msg + repr(pool), extra={"color_message": msg + pool.colored_repr})


@app.on_event("shutdown")
async def close_db_pool():
    pool = await app.pop_pool()
    msg = "Closing database connection pool: "
    logger.info(msg + repr(pool), extra={"color_message": msg + pool.colored_repr})
    await pool.close()
    msg = "Closed database connection pool: "
    logger.info(msg + repr(pool), extra={"color_message": msg + pool.colored_repr})


async def db_pool():
    yield await app.pool


def connection(module=None):
    async def _connection(pool=Depends(db_pool)):
        async with pool.acquire() as conn:
            if module is not None:
                await conn.execute(f"SET MODULE {module}")
            try:
                yield conn
            finally:
                if module is not None:
                    await conn.execute("RESET MODULE")

    return _connection


def load_extras():
    app.add_middleware(ClientDisconnectMiddleware)

    if config.SERVER_WEB_DIR:
        msg = "Serving Web files from: "
        logger.info(
            msg + "%s",
            config.SERVER_WEB_DIR,
            extra={"color_message": msg + click.style("%s", fg="cyan")},
        )
        web = StaticFiles(directory=config.SERVER_WEB_DIR)

        async def default(scope, receive, send):
            path = web.get_path(scope)
            if path.startswith("api/"):
                await app.router.not_found(scope, receive, send)
            else:
                response = await web.get_response(path, scope)
                if response.status_code == 404:
                    response = await web.get_response("index.html", scope)
                await response(scope, receive, send)

        app.router.default = default

    if config.SERVER_USE_FORWARDED_HOST:
        logger.info("Enabled handling X-Forwarded-Host.")

        class ProxyHeadersMiddleware:
            def __init__(self, app_):
                self.app = app_

            async def __call__(self, scope, receive, send):
                if scope["type"] in ("http", "websocket"):
                    headers = dict(scope["headers"])

                    if b"x-forwarded-host" in headers:
                        x_forwarded_host = headers[b"x-forwarded-host"].decode("ascii")
                        (host, sep, port) = x_forwarded_host.partition(":")
                        if sep is None:
                            scope["server"] = (host, 0)
                        else:
                            scope["server"] = (host, int(port))

                        if b"host" in headers:
                            headers[b"host"] = headers[b"x-forwarded-host"]
                            scope["headers"] = list(headers.items())

                await self.app(scope, receive, send)

        app.add_middleware(ProxyHeadersMiddleware)

    msg = "Start to load extra modules, enabled modules: "
    logger.info(
        msg + "%s",
        ", ".join(config.SERVER_ENABLED_MODULES),
        extra={"color_message": msg + click.style("%s", fg="cyan")},
    )
    for ep in pkg_resources.iter_entry_points("gen3.server"):
        if ep.name in config.SERVER_ENABLED_MODULES:
            mod = ep.load()
            for sub_ep in pkg_resources.iter_entry_points(f"gen3.server.{ep.name}"):
                sub_ep.load()
            msg = "Loaded module: "
            logger.info(
                msg + "%s",
                ep.name,
                extra={"color_message": msg + click.style("%s", fg="cyan")},
            )
            mod.init_app(app, api)
        else:
            msg = "Skipped module: "
            logger.info(
                msg + "%s",
                ep.name,
                extra={"color_message": msg + click.style("%s", fg="yellow")},
            )
    app.include_router(api, prefix=config.SERVER_URL_PREFIX)


@api.get("/migrate")
async def migrate(conn=Depends(connection())):
    schemas = {}

    for ep in pkg_resources.iter_entry_points("gen3.schema"):
        for mod in config.SERVER_ENABLED_MODULES:
            if ep.name.startswith(mod):
                schemas.setdefault(mod, []).append(ep.load())
    for module, sdls in schemas.items():
        async with conn.transaction() as tx:
            await ensure_module(conn, module)
            eql = f"""\
CREATE MIGRATION {module}::migs TO {{
{''.join(sdls)}}}"""
            logger.critical(
                "Migrating %s schema to:\n%s",
                module,
                eql,
                extra={
                    "color_message": "Migrating "
                    + click.style("%s", fg="cyan")
                    + " schema to:\n%s"
                },
            )
            await conn.execute(eql)
            try:
                await conn.execute(f"COMMIT MIGRATION {module}::migs;")
            except edgedb.errors.InternalServerError:
                # bug in EdgeDB
                tx.raise_rollback()


@api.get("/version")
def get_version():
    return pkg_resources.get_distribution("gen3").version


@api.route("/docs", include_in_schema=False)
def swagger_ui_html(_):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <title>{app.title}</title>
    <style>
    body {{
      position: relative;
    }}
    #height-change-listener {{
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      height: 100%;
      width: 0;
      border: 0;
      background-color: transparent;
    }}
    </style>
    </head>
    <body>
    <iframe id="height-change-listener" tabindex="-1"></iframe>
    <div id="swagger-ui">
    </div>
    <script
    src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    function HideTopbarPlugin() {{
      // this plugin overrides the Topbar component to return nothing
      return {{ components: {{
          info: function() {{ return null }}
        }}
      }}
    }}

    const ui = SwaggerUIBundle({{
        url: '{app.openapi_url}',
        dom_id: '#swagger-ui',
        presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
          plugins: [
    SwaggerUIBundle.plugins.DownloadUrl,
    HideTopbarPlugin
  ],

        layout: "BaseLayout",
        deepLinking: true,
        onComplete: function () {{
            window.parent.document.dispatchEvent(new CustomEvent('swagger-load'))
        }}
    }})

    document.getElementById('height-change-listener').contentWindow.addEventListener(
        'resize', function () {{
            window.parent.document.dispatchEvent(new CustomEvent('swagger-resize'))
    }})
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


load_extras()
