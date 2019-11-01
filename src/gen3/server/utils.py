import fastapi

ID_REGEX = "^[a-zA-Z_][a-zA-Z0-9_]*$"


async def ensure_module(conn, module):
    if not await conn.fetchall(
        "SELECT name := schema::Module.name FILTER name = <str>$module", module=module
    ):
        await conn.execute(f"CREATE MODULE {module}")


class Module(fastapi.APIRouter):
    def __init__(self, **kwargs):
        super().__init__()
        self._kwargs = kwargs

    def init_app(self, app):
        app.include_router(self, **self._kwargs)
