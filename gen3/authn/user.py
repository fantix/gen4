from fastapi import Depends

from ..server.app import app, connection

SCHEMA = """\
    type User {
        required property username -> str;
    }
"""


@app.get("/user")
async def get_current_user(conn=Depends(connection)):
    async with conn.transaction():
        pass
