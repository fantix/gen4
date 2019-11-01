ID_REGEX = "^[a-zA-Z_][a-zA-Z0-9_]*$"


async def ensure_module(conn, module):
    if not await conn.fetchall(
        "SELECT name := schema::Module.name FILTER name = <str>$module", module=module
    ):
        await conn.execute(f"CREATE MODULE {module}")
