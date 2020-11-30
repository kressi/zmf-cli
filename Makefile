SHELL := /bin/bash

.SHELLFLAGS = -c -o pipefail -e

.PHONY: all $(MAKECMDGOALS)

.SILENT:

all: clean lint build install test

init:
	python -m pip install .[tests]
	python -m pip install build

clean:
	rm -rf dist build

lint:
	black .
	flake8
	mypy src

build:
	python -m build .

install: build
	python -m pip install dist/*

test:
	pytest --override-ini log_cli=true --cov-report term-missing --cov zmfcli
