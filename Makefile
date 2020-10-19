SHELL := /bin/bash

.SHELLFLAGS = -c -o pipefail -e

.PHONY: all $(MAKECMDGOALS)

.SILENT:

all: lint test build install

init:
	python -m pip install .[tests]

lint:
	black .
	flake8

test:
	pytest --cov=zmfcli
	python -m pep517.check .

build:
	python -m pep517.build .

install: build
	python -m pip install dist/*