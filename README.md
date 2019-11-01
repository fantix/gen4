# Gen3 on EdgeDB

This is a PoC project to build [Gen3](https://gen3.org/) on [EdgeDB](https://edgedb.com/).
The server is built with [FastAPI](https://fastapi.tiangolo.com/) and packaged with
[Poetry](https://poetry.eustace.io/). The API is not compatible with Gen3.

## Installation
[Install EdgeDB](https://edgedb.com/download), then
[get Poetry](https://poetry.eustace.io/docs/#installation), and run in source code:

```bash
poetry install -E server
```

## Development

Create a file `.env` in the source code with:

```
DB_USER=...
DB_PASSWORD=...
```

Run the server with auto-reloading:

```bash
gen3 run --reload
```

Try out the OpenAPI documentation at: http://localhost:8000/docs.

To run tests:

```bash
pytest --cov=gen3
```