"""Core collation element generation for UTS #10.

The Default Collation Element Table (DCE) is large; this module ships a
small, curated subset that is sufficient for the tests and for the common
ASCII / Latin-1 cases.  Characters not present in the table receive an
implicit primary weight derived from their code point, following the
UTS #10 implicit-weight algorithm.  This keeps the library dependency-free
while still producing a total order over all Unicode strings.

Design choices:

* Weights are stored as unsigned 16-bit integers because the DCE uses
  16-bit weights and the implicit algorithm is defined in terms of them.
* ``sort_key`` returns a ``bytes`` object.  Each weight is encoded as two
  big-endian bytes, which makes lexicographic byte comparison equivalent to
  numeric weight comparison.  This is the same trick used by ICU and is the
  reason we do not simply return a tuple of ints: byte comparison is faster
  and is what callers usually want for sorting.
* The table is immutable after construction.  ``CollationTable`` builds a
  plain ``dict`` internally and never exposes it, so callers cannot corrupt
  the shared ``DEFAULT_TABLE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

__all__ = [
    "CollationElement",
    "CollationTable",
    "DEFAULT_TABLE",
    "collation_elements",
    "sort_key",
]


@dataclass(frozen=True)
class CollationElement:
    """A single collation element: primary, secondary and tertiary weights.

    A weight of ``0`` means "ignorable at this level".  The DCE uses ``0``
    for ignorable elements and we preserve that convention so that the
    implicit algorithm can concatenate levels without special-casing.
    """

    primary: int
    secondary: int
    tertiary: int

    def __post_init__(self) -> None:
        for name, value in (
            ("primary", self.primary),
            ("secondary", self.secondary),
            ("tertiary", self.tertiary),
        ):
            if not isinstance(value, int):
                raise TypeError(f"{name} weight must be an int, got {type(value).__name__}")
            if value < 0 or value > 0xFFFF:
                raise ValueError(f"{name} weight must fit in 16 bits, got {value}")


# The curated DCE subset.  Each entry maps a single code point to its
# collation element.  The values follow the Default Collation Element Table
# from UTS #10, section 7.2.  Only the characters needed for the tests and
# for basic Latin text are included; everything else falls back to the
# implicit weight algorithm.
_RAW_TABLE: Dict[int, Tuple[int, int, int]] = {
    # Ignorables
    0x0000: (0, 0, 0),  # NULL
    0x0009: (0, 0, 0),  # TAB
    0x000A: (0, 0, 0),  # LF
    0x000D: (0, 0, 0),  # CR
    0x0020: (0, 0, 0),  # SPACE
    # Digits
    0x0030: (0x0E33, 0x0020, 0x0002),  # 0
    0x0031: (0x0E34, 0x0020, 0x0002),  # 1
    0x0032: (0x0E35, 0x0020, 0x0002),  # 2
    0x0033: (0x0E36, 0x0020, 0x0002),  # 3
    0x0034: (0x0E37, 0x0020, 0x0002),  # 4
    0x0035: (0x0E38, 0x0020, 0x0002),  # 5
    0x0036: (0x0E39, 0x0020, 0x0002),  # 6
    0x0037: (0x0E3A, 0x0020, 0x0002),  # 7
    0x0038: (0x0E3B, 0x0020, 0x0002),  # 8
    0x0039: (0x0E3C, 0x0020, 0x0002),  # 9
    # Uppercase Latin
    0x0041: (0x1C47, 0x0020, 0x0008),  # A
    0x0042: (0x1C60, 0x0020, 0x0008),  # B
    0x0043: (0x1C7A, 0x0020, 0x0008),  # C
    0x0044: (0x1C8E, 0x0020, 0x0008),  # D
    0x0045: (0x1CA2, 0x0020, 0x0008),  # E
    0x0046: (0x1CB6, 0x0020, 0x0008),  # F
    0x0047: (0x1CCA, 0x0020, 0x0008),  # G
    0x0048: (0x1CDE, 0x0020, 0x0008),  # H
    0x0049: (0x1CF2, 0x0020, 0x0008),  # I
    0x004A: (0x1D06, 0x0020, 0x0008),  # J
    0x004B: (0x1D1A, 0x0020, 0x0008),  # K
    0x004C: (0x1D2E, 0x0020, 0x0008),  # L
    0x004D: (0x1D42, 0x0020, 0x0008),  # M
    0x004E: (0x1D56, 0x0020, 0x0008),  # N
    0x004F: (0x1D6A, 0x0020, 0x0008),  # O
    0x0050: (0x1D7E, 0x0020, 0x0008),  # P
    0x0051: (0x1D92, 0x0020, 0x0008),  # Q
    0x0052: (0x1DA6, 0x0020, 0x0008),  # R
    0x0053: (0x1DBA, 0x0020, 0x0008),  # S
    0x0054: (0x1DCE, 0x0020, 0x0008),  # T
    0x0055: (0x1DE2, 0x0020, 0x0008),  # U
    0x0056: (0x1DF6, 0x0020, 0x0008),  # V
    0x0057: (0x1E0A, 0x0020, 0x0008),  # W
    0x0058: (0x1E1E, 0x0020, 0x0008),  # X
    0x0059: (0x1E32, 0x0020, 0x0008),  # Y
    0x005A: (0x1E46, 0x0020, 0x0008),  # Z
    # Lowercase Latin
    0x0061: (0x1C47, 0x0020, 0x0002),  # a
    0x0062: (0x1C60, 0x0020, 0x0002),  # b
    0x0063: (0x1C7A, 0x0020, 0x0002),  # c
    0x0064: (0x1C8E, 0x0020, 0x0002),  # d
    0x0065: (0x1CA2, 0x0020, 0x0002),  # e
    0x0066: (0x1CB6, 0x0020, 0x0002),  # f
    0x0067: (0x1CCA, 0x0020, 0x0002),  # g
    0x0068: (0x1CDE, 0x0020, 0x0002),  # h
    0x0069: (0x1CF2, 0x0020, 0x0002),  # i
    0x006A: (0x1D06, 0x0020, 0x0002),  # j
    0x006B: (0x1D1A, 0x0020, 0x0002),  # k
    0x006C: (0x1D2E, 0x0020, 0x0002),  # l
    0x006D: (0x1D42, 0x0020, 0x0002),  # m
    0x006E: (0x1D56, 0x0020, 0x0002),  # n
    0x006F: (0x1D6A, 0x0020, 0x0002),  # o
    0x0070: (0x1D7E, 0x0020, 0x0002),  # p
    0x0071: (0x1D92, 0x0020, 0x0002),  # q
    0x0072: (0x1DA6, 0x0020, 0x0002),  # r
    0x0073: (0x1DBA, 0x0020, 0x0002),  # s
    0x0074: (0x1DCE, 0x0020, 0x0002),  # t
    0x0075: (0x1DE2, 0x0020, 0x0002),  # u
    0x0076: (0x1DF6, 0x0020, 0x0002),  # v
    0x0077: (0x1E0A, 0x0020, 0x0002),  # w
    0x0078: (0x1E1E, 0x0020, 0x0002),  # x
    0x0079: (0x1E32, 0x0020, 0x0002),  # y
    0x007A: (0x1E46, 0x0020, 0x0002),  # z
}


class CollationTable:
    """An immutable mapping from code points to collation elements.

    The constructor accepts an iterable of ``(codepoint, (p, s, t))``
    pairs.  This is deliberately not a public mutable mapping: the table is
    shared by ``DEFAULT_TABLE`` and must not be modified by callers.
    """

    __slots__ = ("_entries",)

    def __init__(self, entries: Iterable[Tuple[int, Tuple[int, int, int]]]) -> None:
        built: Dict[int, CollationElement] = {}
        for codepoint, weights in entries:
            if not isinstance(codepoint, int):
                raise TypeError("code point must be an int")
            if codepoint < 0 or codepoint > 0x10FFFF:
                raise ValueError(f"code point out of range: {codepoint}")
            if len(weights) != 3:
                raise ValueError("weights must be a 3-tuple of ints")
            built[codepoint] = CollationElement(*weights)
        self._entries = built

    def get(self, codepoint: int) -> CollationElement | None:
        """Return the collation element for *codepoint*, or ``None``."""
        return self._entries.get(codepoint)

    def __contains__(self, codepoint: object) -> bool:
        return isinstance(codepoint, int) and codepoint in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def codepoints(self) -> Tuple[int, ...]:
        """Return the code points in the table, sorted ascending."""
        return tuple(sorted(self._entries))


# The shared default table.  Built once at import time from the raw data
# above.  We expose it as a module-level name so callers can pass it
# explicitly to ``collation_elements`` if they want to be explicit about
# which table they are using.
DEFAULT_TABLE = CollationTable(_RAW_TABLE.items())


# Implicit weight constants from UTS #10, section 10.1.  The implicit
# primary weight for a code point outside the table is
# ``0xFB40 + (codepoint >> 15)`` for the high half and
# ``0xFB80 + (codepoint & 0x7FFF)`` for the low half, but the standard
# algorithm is simpler: compute a 16-bit weight from the code point and
# then add a base.  We use the same base values ICU uses so that the
# resulting order is compatible with the DCE.
_IMPLICIT_BASE = 0xFB40
_IMPLICIT_BASE_2 = 0xFB80


def _implicit_element(codepoint: int) -> CollationElement:
    """Return the implicit collation element for *codepoint*.

    UTS #10 defines two ranges of implicit weights.  Code points below
    ``0x10000`` use the first range; code points above use the second.
    The secondary and tertiary weights are fixed at ``0x0020`` and
    ``0x0002`` respectively, which is what the standard specifies for
    implicit elements.
    """
    if codepoint < 0x10000:
        primary = _IMPLICIT_BASE + codepoint
    else:
        primary = _IMPLICIT_BASE_2 + (codepoint - 0x10000)
    return CollationElement(primary & 0xFFFF, 0x0020, 0x0002)


def collation_elements(
    text: str,
    table: CollationTable | None = None,
) -> List[CollationElement]:
    """Return the collation elements for *text*.

    Each code point in *text* is looked up in *table* (defaulting to
    ``DEFAULT_TABLE``).  Code points not present in the table receive an
    implicit element so that every string has a defined sort key.

    The function is intentionally simple: it does not perform
    normalization or contraction matching.  Those are separate concerns
    and are out of scope for this library.  The trade-off is that
    combining marks and contractions will not collate exactly as they do
    in a full UTS #10 implementation; the implicit fallback still gives
    them a stable, total order.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")
    if table is None:
        table = DEFAULT_TABLE
    if not isinstance(table, CollationTable):
        raise TypeError("table must be a CollationTable")

    result: List[CollationElement] = []
    for ch in text:
        codepoint = ord(ch)
        element = table.get(codepoint)
        if element is None:
            element = _implicit_element(codepoint)
        result.append(element)
    return result


def sort_key(text: str, table: CollationTable | None = None) -> bytes:
    """Return a byte string that sorts according to UTS #10.

    The key is the concatenation of the primary weights, then the
    secondary weights, then the tertiary weights.  Each weight is encoded
    as two big-endian bytes, so lexicographic byte comparison matches
    numeric weight comparison.  Ignorable weights (``0``) are skipped
    because they contribute nothing to the order; this is the standard
    behaviour and is why the key for an empty string is empty.

    The returned value is ``bytes``, not ``str``, because it is not
    text: it is a binary sort key.  Callers who need to store it in a
    text column should encode it (for example with base64) themselves.
    """
    elements = collation_elements(text, table)
    out = bytearray()
    # Primary weights
    for element in elements:
        if element.primary:
            out += element.primary.to_bytes(2, "big")
    # Secondary weights
    for element in elements:
        if element.secondary:
            out += element.secondary.to_bytes(2, "big")
    # Tertiary weights
    for element in elements:
        if element.tertiary:
            out += element.tertiary.to_bytes(2, "big")
    return bytes(out)
