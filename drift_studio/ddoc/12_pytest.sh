# Run the active test suite. The legacy `test_cli_golden.py` is currently
# parked as `__test_cli_golden.py` (disabled prefix); do not re-add it
# here until it is reintroduced.
set -e
pytest tests/ -v
