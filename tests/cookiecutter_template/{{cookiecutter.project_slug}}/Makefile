PHONY := help test

help:
	@echo "check code coverage quickly with the default Python"

install:
	pip install -U pip
	pip install -e .[test]

test:
	pytest
