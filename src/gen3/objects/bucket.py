import json
import typing

import edgedb
import pkg_resources
from fastapi import Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Schema, ValidationError
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from .server import mod
from ..server.app import connection
from ..server.utils import ID_REGEX

SCHEMA = """\
    type Bucket {
        required property name -> str {
            constraint exclusive;
        }
        required property provider -> str;
        required property settings -> json;
        required property enabled -> bool {
            default := true;
        }
    }
"""
installed_providers = {}


@mod.get("/providers")
def get_providers():
    return {
        key: dict(
            desc=provider.__doc__,
            settings=typing.get_type_hints(provider)["settings"].schema(),
        )
        for key, provider in installed_providers.items()
    }


class Bucket(BaseModel):
    name: str = Schema(..., regex=ID_REGEX)
    provider: str
    settings: dict = {}
    enabled: bool = True

    @classmethod
    def parse_obj(cls, obj):
        if isinstance(obj, edgedb.Object):
            obj = {
                key: getattr(obj, key)
                for key in cls.schema()["properties"]
                if hasattr(obj, key)
            }
            if "settings" in obj:
                obj["settings"] = json.loads(obj["settings"])
        parent = installed_providers.get(obj.get("provider"), cls)
        if parent is cls:
            parent = super()
        return parent.parse_obj(obj)

    def dict(self, dump_json=False, **kwargs):
        rv = super().dict(**kwargs)
        if dump_json:
            if "settings" in rv:
                rv["settings"] = json.dumps(rv["settings"])
        return rv

    async def get(self, path, recursive=True):  # pragma: no cover
        raise NotImplementedError

    async def put(self, path, file):  # pragma: no cover
        raise NotImplementedError

    async def delete(self, path):  # pragma: no cover
        raise NotImplementedError


@mod.get("/buckets")
async def list_buckets(request: Request, conn=Depends(connection("objects"))):
    rv = [
        dict(
            Bucket.parse_obj(bucket).dict(exclude={"settings"}),
            installed=bucket.provider in installed_providers,
            href=request.url_for("get_bucket", bucket_name=bucket.name),
        )
        for bucket in await conn.fetchall("SELECT Bucket {name, provider, enabled}")
    ]
    return rv


@mod.post("/buckets", status_code=HTTP_201_CREATED)
async def create_bucket(
    bucket: Bucket, request: Request, conn=Depends(connection("objects"))
):
    try:
        bucket = Bucket.parse_obj(bucket.dict())
    except ValidationError as e:
        raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, e.errors())
    if not bucket.provider:
        raise HTTPException(
            HTTP_400_BAD_REQUEST, [dict(loc=["provider"], msg="must not be empty")]
        )
    try:
        rv = await conn.fetchone(
            """
                INSERT Bucket {
                    name := <str>$name,
                    provider := <str>$provider,
                    settings := to_json(<str>$settings),
                    enabled := <bool>$enabled,
                }
                """,
            **bucket.dict(dump_json=True),
        )
    except edgedb.ConstraintViolationError as e:
        raise HTTPException(HTTP_409_CONFLICT, [dict(loc=["name"], msg=str(e))])
    else:
        return dict(
            id=str(rv.id), href=request.url_for("get_bucket", bucket_name=bucket.name)
        )


async def _get_bucket(bucket_name: str, conn=Depends(connection("objects"))):
    bucket = await conn.fetchall(
        "SELECT Bucket {name, provider, enabled, settings} FILTER .name = <str>$name",
        name=bucket_name,
    )
    if bucket:
        yield Bucket.parse_obj(bucket[0])
    else:
        raise HTTPException(HTTP_404_NOT_FOUND, f"bucket {bucket_name} not found")


@mod.get("/buckets/{bucket_name}")
async def get_bucket(request: Request, bucket=Depends(_get_bucket)):
    return dict(
        bucket.dict(),
        href=request.url_for("get_bucket", bucket_name=bucket.name),
        installed=bucket.provider in installed_providers,
    )


class UpdateBucket(BaseModel):
    settings: dict = None
    enabled: bool = None


@mod.put("/buckets/{bucket_name}")
async def update_bucket(
    bucket_name: str,
    bucket: UpdateBucket,
    request: Request,
    conn=Depends(connection("objects")),
):
    sets = []
    values = dict(name=bucket_name)
    if bucket.enabled is not None:
        sets.append("enabled := <bool>$enabled")
        values["enabled"] = bucket.enabled
    if bucket.settings is not None:
        sets.append("settings := <json>$settings")
        values["settings"] = json.dumps(bucket.settings)
    if not sets:
        raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, "no update specified")

    bucket = await conn.fetchall(
        f"UPDATE Bucket FILTER .name = <str>$name SET {{{', '.join(sets)}}}", **values
    )
    if bucket:
        return dict(
            id=str(bucket[0].id),
            href=request.url_for("get_bucket", bucket_name=bucket_name),
        )
    else:
        raise HTTPException(HTTP_404_NOT_FOUND, f"bucket {bucket_name} not found")


@mod.delete("/buckets/{bucket_name}")
async def delete_bucket(
    bucket_name: str, request: Request, conn=Depends(connection("objects"))
):
    buckets = await conn.fetchall(
        "DELETE Bucket FILTER .name = <str>$name", name=bucket_name
    )
    if buckets:
        return dict(
            id=str(buckets[0].id),
            href=request.url_for("get_bucket", bucket_name=bucket_name),
        )
    else:
        raise HTTPException(HTTP_404_NOT_FOUND, f"bucket {bucket_name} not found")


@mod.get("/buckets/{bucket_name}/{path:path}")
async def get_bucket_path(
    path: str = None, bucket=Depends(_get_bucket), recursive: bool = True
):
    return await bucket.get(path, recursive=recursive)


@mod.put("/buckets/{bucket_name}/{path:path}")
async def put_bucket_path(
    path: str = None, bucket=Depends(_get_bucket), file: UploadFile = File(...)
):
    return await bucket.put(path, file)


@mod.delete("/buckets/{bucket_name}/{path:path}", status_code=HTTP_204_NO_CONTENT)
async def delete_bucket_path(path: str = None, bucket=Depends(_get_bucket)):
    await bucket.delete(path)
    return Response(status_code=HTTP_204_NO_CONTENT)


def load_extras():
    for ep in pkg_resources.iter_entry_points("gen3.objects.providers"):
        try:
            provider = ep.load()
        except pkg_resources.DistributionNotFound:  # pragma: no cover
            pass
        else:
            installed_providers[ep.name] = provider


load_extras()
