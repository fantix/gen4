# Gen3 on EdgeDB

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f819f24801bb4bf79523bc48adfdbb25)](https://www.codacy.com/manual/fantix/gen4?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fantix/gen4&amp;utm_campaign=Badge_Grade)
[![Codacy Badge](https://api.codacy.com/project/badge/Coverage/f819f24801bb4bf79523bc48adfdbb25)](https://www.codacy.com/manual/fantix/gen4?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fantix/gen4&amp;utm_campaign=Badge_Coverage)

This is a PoC project to build [Gen3](https://gen3.org/) on [EdgeDB](https://edgedb.com/).
The server is built with [FastAPI](https://fastapi.tiangolo.com/) and packaged with
[Poetry](https://poetry.eustace.io/). The API is not compatible with Gen3.


## Installation

Install required software:

* [EdgeDB](https://edgedb.com/download)
* [Python](https://www.python.org/downloads/) 3.7 or above
* [Poetry](https://poetry.eustace.io/docs/#installation)
* [Node.js](https://nodejs.org/)
* [Yarn](https://yarnpkg.com/en/docs/install#mac-stable)

Then use `make` to install the dependencies. Before that,
a [virtualenv](https://virtualenv.pypa.io/) is recommended.
If you don't manage your own, Poetry will create one for you
during `make`, and you must activate it by:

```bash
poetry shell
```


## Development

Create a file `.env` in the source code with:

```
DB_USER=...
DB_PASSWORD=...
```

Run the server (both Python and Web dev server) with auto-reloading:

```bash
gen3 run
```

Try out the website at: http://localhost:8080/.

To run tests:

```bash
pytest --cov=gen3 tests
```

### Server-only or Web-only

Run only the server:

```bash
gen3 run --no-web
```

Run only the Web dev server under `web` folder:

```bash
yarn serve
```
