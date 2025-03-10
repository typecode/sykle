# Sykle Development Guide

Version 0.7.0 - Updated to use `docker compose` instead of `docker-compose` command

## Commands
- Install: `make install` or `pip3 install -e .`
- Run tests: `python -m unittest` or `python -m nose`
- Run single test: `python -m unittest test.sykle_test.SykleTestCase.test_dc_run_env_file`
- Clean project: `make clean`

## Code Style
- Python 3.4+ compatible
- Use consistent 4-space indentation
- Follow PEP 8 naming conventions:
  - Functions/methods: snake_case
  - Classes: PascalCase
  - Constants: UPPER_SNAKE_CASE
- Imports: standard library first, then third-party, then local
- Prefer explicit error handling with try/except blocks
- Mock external dependencies in tests

## Project Structure
- CLI entrypoint: `syk` command (sykle.cli:main)
- Core functionality in `sykle/sykle.py`
- Configuration in `sykle/config.py`
- Tests use unittest framework with mock objects