import asyncio
import os

import aioftp
from pydantic import BaseModel

from ..bucket import Bucket
from ...server.app import app

BUFFER_SIZE = 65536
CACHE_TIME = 300
_cache = {}


class FtpSettings(BaseModel):
    host: str
    port: int = aioftp.DEFAULT_PORT
    ssl: bool = False
    path: str = "/"
    user: str = aioftp.DEFAULT_USER
    password: str = aioftp.DEFAULT_PASSWORD


class FtpBucket(Bucket):
    """Local file system bucket."""

    settings: FtpSettings = {}

    async def get(self, path, recursive=True):
        if self.name not in _cache:
            _cache[self.name] = CachedFtpServer(self)
        async with _cache[self.name] as client:
            full_path = os.path.join(self.settings.path, path)
            if await client.is_dir(full_path):
                rv = []
                async for item, props in client.list(full_path, recursive=recursive):
                    rv.append(
                        dict(
                            name=str(item.relative_to(full_path)),
                            dir=props["type"] == "dir",
                            size=props.get("size", 0),
                            mtime=props["modify"],
                        )
                    )
                return rv
            else:
                pass

    async def put(self, path, file):
        pass

    async def delete(self, path):
        pass


class CachedFtpServer:
    def __init__(self, bucket: FtpBucket):
        self._name = bucket.name
        self._settings = bucket.settings
        self._client = None
        self._lock = asyncio.Lock()
        self._expire = None
        self._loop = asyncio.get_running_loop()

    async def __aenter__(self):
        await self._lock.acquire()
        client = self._client
        try:
            if client is None:
                client = aioftp.Client()
                await client.connect(self._settings.host, self._settings.port)
                await client.login(
                    self._settings.user, self._settings.password, aioftp.DEFAULT_ACCOUNT
                )
                self._client = client
            if self._expire is not None:
                self._expire.cancel()
                self._expire = self._loop.call_later(
                    CACHE_TIME, self._loop.create_task, self.close()
                )
            return client
        except Exception:
            await client.close()
            self._lock.release()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    async def close(self):
        if self._expire is not None:
            self._expire.cancel()
            self._expire = None
        _cache.pop(self._name, None)
        await self._client.quit()


@app.on_event("shutdown")
async def clear_ftp_cache():
    fs = []
    while _cache:
        client = _cache.popitem()[1]
        fs.append(client.close())
    await asyncio.wait(fs)
