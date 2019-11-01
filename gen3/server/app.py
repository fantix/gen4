import asyncio

import click
import edgedb
import pkg_resources
from fastapi import FastAPI, Depends

from . import logger, config


class Application(FastAPI):
    def __init__(self):
        super().__init__(
            title="Gen3 Data Commons",
            version=pkg_resources.get_distribution("gen3").version,
        )
        self._pool = None

    @property
    def pool(self):
        if self._pool is None:
            self._pool = asyncio.Future()
        return self._pool


app = Application()


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
    pool = await app.pool
    msg = "Closing database connection pool: "
    logger.info(msg + repr(pool), extra={"color_message": msg + pool.colored_repr})
    await pool.close()
    msg = "Closed database connection pool: "
    logger.info(msg + repr(pool), extra={"color_message": msg + pool.colored_repr})


async def db_pool():
    yield await app.pool


async def connection(pool=Depends(db_pool)):
    async with pool.acquire() as conn:
        yield conn


def load_extras():
    msg = "Start to load extra modules, enabled prefixes: "
    logger.info(
        msg + "%s",
        ", ".join(config.SERVER_ENABLED_MODULES),
        extra={"color_message": msg + click.style("%s", fg="cyan")},
    )
    for ep in pkg_resources.iter_entry_points("gen3.server"):
        for mod in config.SERVER_ENABLED_MODULES:
            if ep.name.startswith(mod):
                ep.load()
                msg = "Loaded module: "
                logger.info(
                    msg + "%s",
                    ep.name,
                    extra={"color_message": msg + click.style("%s", fg="cyan")},
                )
                break
        else:
            msg = "Skipped module: "
            logger.info(
                msg + "%s",
                ep.name,
                extra={"color_message": msg + click.style("%s", fg="yellow")},
            )


@app.get("/")
async def read_root(conn=Depends(connection)):
    rv = await conn.fetchone("SELECT 'World'")
    return {"Hello": rv}


@app.get("/migrate")
async def migrate(conn=Depends(connection)):
    schemas = []

    for ep in pkg_resources.iter_entry_points("gen3.schema"):
        for mod in config.SERVER_ENABLED_MODULES:
            if ep.name.startswith(mod):
                schemas.append(ep.load())
    eql = """\
CREATE MIGRATION migs TO {
%s}""" % "".join(
        schemas
    )
    logger.critical("Migrating default schema to:\n" + eql)
    async with conn.transaction() as tx:
        await conn.execute(eql)
        try:
            await conn.execute("COMMIT MIGRATION migs;")
        except edgedb.errors.InternalServerError:
            # bug in EdgeDB
            tx.raise_rollback()


load_extras()
