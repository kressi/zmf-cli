#!/usr/bin/env python


# https://github.com/pypa/pip/issues/7953
import site
import sys
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]


# https://setuptools.readthedocs.io/en/latest/setuptools.html#id4
# https://snarky.ca/what-the-heck-is-pyproject-toml/
import setuptools

if __name__ == "__main__":
    setuptools.setup()