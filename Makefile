all: server web
server:
	poetry install -E server
web:
	$(MAKE) -C web

.PHONY: server web
