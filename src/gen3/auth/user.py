from fastapi import Depends

from .server import mod
from ..server.app import connection

SCHEMA = """\
    type User {
        required property username -> str;
    }
"""


@mod.get("/user")
async def get_current_user(conn=Depends(connection("auth"))):
    async with conn.transaction():
        return await conn.fetchall("SELECT User { username }")
