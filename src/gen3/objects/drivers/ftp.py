import asyncio
import mimetypes
import os
import socket

import aioftp
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

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
            stat = await client.stat(full_path)
            preview = files = None
            if stat["type"] == "dir":
                type_ = "Directory"
                mime = "inode/directory"
                files = []
                async for item, props in client.list(full_path, recursive=recursive):
                    files.append(
                        dict(
                            name=str(item.relative_to(full_path)),
                            dir=props["type"] == "dir",
                            size=props.get("size", 0),
                            mtime=props["modify"],
                            mime=mimetypes.guess_type(str(item), False)[0],
                        )
                    )
            else:
                await client.command("TYPE I", "200")
                ip, port = await client._do_epsv()
                if ip in ("0.0.0.0", None):
                    ip = client.server_host

                def get_bytes():
                    s = socket.create_connection((ip, port), timeout=1)
                    buf = s.recv(1024)
                    s.close()
                    # noinspection PyBroadException
                    try:
                        preview_ = buf.decode()
                    except Exception:
                        preview_ = None
                    return self.guess_type(full_path, buf), preview_

                fut = asyncio.ensure_future(run_in_threadpool(get_bytes))
                await client.command(f"RETR {full_path}", "1xx")
                (mime, type_), preview = await fut
                await client.command(None, ["2xx", "451"], "1xx")

            return dict(
                name=path,
                dir=stat["type"] == "dir",
                size=stat.get("size", 0),
                mtime=stat["modify"],
                type=type_,
                mime=mime,
                files=files,
                preview=preview,
            )

    async def download(self, path):
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
            client.close()
            self._lock.release()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()
        if exc_val is not None:
            await self.close()

    async def close(self):
        async with self._lock:
            client, self._client = self._client, None
            if self._expire is not None:
                self._expire.cancel()
                self._expire = None
            _cache.pop(self._name, None)
            if client:
                # noinspection PyBroadException
                try:
                    await asyncio.wait_for(client.quit(), 0.1)
                except Exception:
                    pass


@app.on_event("shutdown")
async def clear_ftp_cache():
    fs = []
    while _cache:
        client = _cache.popitem()[1]
        fs.append(client.close())
    await asyncio.wait(fs)
