import os
import shutil
from collections import deque

from fastapi import HTTPException
from pydantic import BaseModel, Schema
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from ..bucket import Bucket
from ...server import logger

BUFFER_SIZE = 65536


class FileSystemSettings(BaseModel):
    root_dir: str = Schema(..., title="Root Directory")


class FileSystemBucket(Bucket):
    """Local file system bucket."""

    settings: FileSystemSettings = {}

    def _get_target(self, path):
        target = os.path.join(self.settings.root_dir, path)
        if (
            os.path.commonpath([target, self.settings.root_dir])
            != self.settings.root_dir
        ):
            raise HTTPException(HTTP_400_BAD_REQUEST, "escaping root_dir")
        return target

    async def get(self, path, recursive=True):
        def _get():
            target = self._get_target(path)
            if not os.path.exists(target):
                raise HTTPException(HTTP_404_NOT_FOUND)
            elif os.path.isdir(target):
                rv = []
                q = deque([iter(os.scandir(target))])
                while q:
                    it = q[-1]
                    try:
                        while True:
                            entry = next(it)
                            rv.append(
                                os.path.relpath(entry.path, self.settings.root_dir)
                            )
                            if recursive and entry.is_dir(follow_symlinks=False):
                                q.append(iter(os.scandir(entry.path)))
                                break
                    except StopIteration:
                        q.pop()
                    except PermissionError as e:
                        logger.warning(e)
                return rv
            else:
                return FileResponse(target)

        return await run_in_threadpool(_get)

    async def put(self, path, file):
        def _put():
            target = self._get_target(path)
            if os.path.exists(target):
                if os.path.isdir(target):
                    raise HTTPException(HTTP_409_CONFLICT, "cannot overwrite folder")
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
            size = 0
            with open(target, "wb") as f:
                while True:
                    chunk = file.file.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    size += len(chunk)
            return {"size": size}

        return await run_in_threadpool(_put)

    async def delete(self, path):
        target = self._get_target(path)
        shutil.rmtree(target)
