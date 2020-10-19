SHELL := /bin/bash

.SHELLFLAGS = -c -o pipefail -e

.PHONY: all $(MAKECMDGOALS)

.SILENT:

all: lint test build install

init:
	python -m pip install .[tests]
	python -m pip install build

lint:
	black .
	flake8

test:
	pytest --cov=zmfcli

build:
	python -m build .

install: build
	python -m pip install dist/*