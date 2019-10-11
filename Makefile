.PHONY: clean-pyc clean-build install

install:
	pip3 install -e .
	syk plugins install

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
