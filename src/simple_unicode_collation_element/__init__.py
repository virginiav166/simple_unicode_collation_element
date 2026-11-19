"""Public API for the simple_unicode_collation_element package.

This package generates sort keys from Unicode strings using the Default
Collation Element Table from UTS #10.  The implementation is intentionally
self-contained and depends only on the Python standard library.
"""

from .core import (
    CollationElement,
    CollationTable,
    DEFAULT_TABLE,
    collation_elements,
    sort_key,
)

__all__ = [
    "CollationElement",
    "CollationTable",
    "DEFAULT_TABLE",
    "collation_elements",
    "sort_key",
]
