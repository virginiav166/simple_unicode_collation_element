# simple_unicode_collation_element

Generates sort keys from Unicode strings using the Default Collation Element Table from UTS #10.

## Usage

```python
from simple_unicode_collation_element import collation_elements, sort_key

# Inspect the collation elements of a string.
for element in collation_elements("abc"):
    print(element.primary, element.secondary, element.tertiary)

# Get a binary sort key suitable for lexicographic comparison.
key = sort_key("hello")
assert isinstance(key, bytes)
assert sort_key("a") < sort_key("b")
```

The package exports `CollationElement`, `CollationTable`, `DEFAULT_TABLE`, `collation_elements`, and `sort_key`.

## Why this exists

Sorting strings by code point is wrong for most human languages: `"Z"` sorts before `"a"`, and accented letters sort far away from their unaccented forms. UTS #10 defines a collation algorithm that fixes this, but the full Default Collation Element Table is several megabytes of data. This library ships a small curated subset covering ASCII letters and digits, and falls back to the UTS #10 implicit-weight algorithm for every other code point. That gives a total, deterministic order over all Unicode strings without pulling in a data file.

The trade-off is explicit: this is not a full UTS #10 implementation. It does not normalize input, it does not handle contractions or expansions, and it does not implement the full multi-level comparison algorithm. It does produce a byte string whose lexicographic order matches the primary, secondary, and tertiary weights of the characters it knows about, plus a stable implicit order for everything else.

## The awkward edge

Characters that are not in the curated table get an implicit primary weight derived from their code point. This means, for example, that `sort_key("\u4e00")` is greater than `sort_key("z")`, because the implicit weight `0x4940` is larger than the Latin primary weights. That is the intended behaviour of the implicit algorithm, but it surprises people who expect CJK characters to sort near their Latin transliterations. If you need real CJK collation, you need the full table.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

