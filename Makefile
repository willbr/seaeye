OS := $(shell uname)

ifeq ($(OS),Darwin)
	PYTHON := python3
else
	PYTHON := python
endif

all:
	$(PYTHON) -m seaeye.eval ./tests/double.ci

wall:
	watchexec --clear --restart "make all"

install:
	$(PYTHON) -m pip install -e .

