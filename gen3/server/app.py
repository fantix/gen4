import asyncio

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
    logger.critical(
        "Creating database connection pool: %s",
        ", ".join(f"{k}={v}" for k, v in args.items() if v is not None),
    )
    assert app.pool is not None
    pool = await Pool(
        **args,
        password=str(config.DB_PASSWORD),
        on_acquire=None,
        on_connect=None,
        on_release=None,
        connection_class=edgedb.asyncio_con.AsyncIOConnection,
    )
    app.pool.set_result(pool)
    logger.critical("Database connection pool created: %s", pool)


@app.on_event("shutdown")
async def close_db_pool():
    pool = await app.pool
    logger.critical("Closing database connection pool: %s", pool)
    await pool.close()
    logger.critical("Closed database connection pool: %s", pool)


async def db_pool():
    yield await app.pool


async def connection(pool=Depends(db_pool)):
    async with pool.acquire() as conn:
        yield conn


for ep in pkg_resources.iter_entry_points("gen3.server"):
    ep.load()


@app.get("/")
async def read_root(conn=Depends(connection)):
    rv = await conn.fetchone("SELECT 'World'")
    return {"Hello": rv}


@app.get("/migrate")
async def migrate(conn=Depends(connection)):
    schemas = []

    for ep in pkg_resources.iter_entry_points("gen3.schema"):
        schemas.append(ep.load())
    eql = """\
CREATE MIGRATION migs TO {
%s
};
COMMIT MIGRATION migs;
""" % "".join(
        schemas
    )
    async with conn.transaction():
        await conn.execute(eql)
