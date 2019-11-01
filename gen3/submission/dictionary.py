import io
from typing import Dict

import edgedb
from fastapi import Depends, Path, UploadFile, File, HTTPException
from pfb.reader import PFBReader
from pydantic import BaseModel
from starlette.responses import Response

from ..server import logger
from ..server.app import app, connection
from ..utils import ensure_module

_TYPES = {"string": "str", "boolean": "bool", "float": "float64", "long": "int64"}
_ESCAPE = {"Case": "Case_"}


def _make_node_name(name):
    rv = name.title().replace("_", "")
    return _ESCAPE.get(rv, rv)


@app.post("/submissions/{schema}/schema")
async def update_schema(
    conn=Depends(connection()),
    schema: str = Path(..., regex="^[a-zA-Z_][a-zA-Z0-9_]*$"),
    file: UploadFile = File(...),
):
    schema = "gen3_" + schema
    migration_eql = io.StringIO()
    print(f"CREATE MIGRATION {schema}::mig TO {{", file=migration_eql)
    with PFBReader(file.file) as pfb:
        nodes = {}
        for node in pfb.metadata["nodes"]:
            nodes[node["name"]] = node
        for node in pfb.schema:
            node = dict(node)
            if node["type"] == "record":
                nodes[node["name"]]["fields"] = [
                    dict(field) for field in node["fields"]
                ]
            else:
                logger.warning(
                    "Skipping node of unknown type %s: %s", node["type"], node
                )
        enums = {}
        for node in nodes.values():
            node_name = _make_node_name(node["name"])
            print(f"    type {node_name} {{", file=migration_eql)
            for field in node["fields"]:
                types = field["type"]
                if isinstance(types, str):
                    types = [types]

                required = True
                type_ = None
                for t in types:
                    if isinstance(t, list):
                        t = dict(t)
                        if t["type"] == "enum":
                            enum_type = f"{node_name}_{field['name']}_t"
                            enums.setdefault(enum_type, set()).update(t["symbols"])
                            assert type_ in (
                                None,
                                enum_type,
                            ), "union type is not supported"
                            type_ = enum_type
                        else:
                            logger.warning(
                                "Skipping %s.%s type %s", node_name, field["name"], t
                            )
                    elif t == "null":
                        required = False
                    else:
                        assert type_ is None, "union type is not supported"
                        type_ = t

                if type_ is None:
                    logger.warning("Skipping null type field: %s", field)
                else:
                    print(
                        f"        {'required ' if required else ''}"
                        f"property {field['name']} -> {_TYPES.get(type_, type_)};",
                        file=migration_eql,
                    )
            for link in node["links"]:
                migration_eql.write("        ")
                if link["multiplicity"] in {"ONE_TO_MANY", "MANY_TO_MANY"}:
                    migration_eql.write("multi ")
                migration_eql.write(
                    f"link {link['name']} -> {_make_node_name(link['dst'])}"
                )
                if link["multiplicity"] == "ONE_TO_ONE":
                    print(" {", file=migration_eql)
                    print("            constraint exclusive;", file=migration_eql)
                    print("        }", file=migration_eql)
                else:
                    print(";", file=migration_eql)
            print("    }", file=migration_eql)
        for enum_name, symbols in enums.items():
            print(f"    scalar type {enum_name} extending str {{", file=migration_eql)
            print(f"        constraint one_of ('", file=migration_eql, end="")
            migration_eql.write("', '".join(symbols))
            print("');", file=migration_eql)
            print("    }", file=migration_eql)
        print("}", file=migration_eql)

    logger.critical("Migrating schema of %s to:\n%s", schema, migration_eql.getvalue())
    async with conn.transaction() as tx:
        await ensure_module(conn, schema)
        await conn.execute(migration_eql.getvalue())
        try:
            await conn.fetchall(f"COMMIT MIGRATION {schema}::mig")
        except edgedb.errors.InternalServerError:
            # bug in EdgeDB
            tx.raise_rollback()
    return schema


class Query(BaseModel):
    query: str
    args: Dict[str, str] = {}


@app.post("/submissions/{schema}/edgeql")
async def query_edgeql(
    query: Query,
    conn=Depends(connection()),
    schema: str = Path(..., regex="^[a-zA-Z_][a-zA-Z0-9_]*$"),
):
    schema = "gen3_" + schema
    await conn.execute(f"SET MODULE {schema}")
    try:
        return Response(
            await conn.fetchall_json(query.query, **query.args),
            media_type="application/json",
        )
    except edgedb.errors.QueryError as e:
        raise HTTPException(400, str(e))
    finally:
        await conn.execute("RESET MODULE")
