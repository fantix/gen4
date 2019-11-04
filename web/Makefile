all: node_modules

node_modules: package.json
	yarn
	touch -m node_modules

clean:
	rm -r dist

dist: node_modules *.js $(shell find src public)
	yarn build

.PHONY: clean
