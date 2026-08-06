"""Command-line entry points.

A package rather than a loose directory so `tests/test_build_table.py` can import
`build_table` under one unambiguous module name and assert that the committed
table regenerates. Running `python scripts/build_table.py` is unaffected.
"""
