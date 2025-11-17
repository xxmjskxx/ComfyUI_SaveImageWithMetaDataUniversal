"""Initializes the 'ext' package, making it a proper Python package.

This file's presence allows for the modules within the 'ext' directory, such as 'generated_user_rules.py',
to be imported using the standard Python package syntax (e.g., '...defs.ext.<module>').
It is kept intentionally minimal to serve this primary purpose.
"""
# Make 'ext' a proper package so extension modules (like generated_user_rules.py)
# can be imported via '...defs.ext.<module>' in all Python runtimes.
# Keeping this file intentionally minimal.
