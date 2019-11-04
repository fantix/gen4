all: server web
server:
	poetry install -E server
web:
	$(MAKE) -C web
dist: pyproject.toml web/*.js $(shell find web/src web/public) $(shell find src -iname '*.py') $(shell find src -type d)
	$(MAKE) dist -C web
	cp -r web/dist src/gen3/server/static
	poetry build
	rm -r src/gen3/server/static
clean:
	$(MAKE) clean -C web
	rm -r dist
.PHONY: server web clean
