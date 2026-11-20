"""Tests for simple_unicode_collation_element.core.

These tests are deterministic: they do not touch the clock, the network,
 or the filesystem.  They exercise the exported API and the edge cases the
 implementation actually handles (implicit weights, ignorables, type
 errors, and byte-level sort-key ordering).
"""

import unittest

from simple_unicode_collation_element import (
    CollationElement,
    CollationTable,
    DEFAULT_TABLE,
    collation_elements,
    sort_key,
)


class CollationElementTests(unittest.TestCase):
    def test_accepts_valid_weights(self) -> None:
        element = CollationElement(1, 2, 3)
        self.assertEqual((element.primary, element.secondary, element.tertiary), (1, 2, 3))

    def test_rejects_non_int_weights(self) -> None:
        with self.assertRaises(TypeError):
            CollationElement("1", 2, 3)  # type: ignore[arg-type]

    def test_rejects_out_of_range_weights(self) -> None:
        with self.assertRaises(ValueError):
            CollationElement(0x10000, 0, 0)

    def test_is_hashable(self) -> None:
        self.assertEqual(hash(CollationElement(1, 2, 3)), hash(CollationElement(1, 2, 3)))


class CollationTableTests(unittest.TestCase):
    def test_get_returns_none_for_missing(self) -> None:
        table = CollationTable([])
        self.assertIsNone(table.get(0x41))

    def test_get_returns_element(self) -> None:
        table = CollationTable([(0x41, (10, 20, 30))])
        self.assertEqual(table.get(0x41), CollationElement(10, 20, 30))

    def test_contains_and_len(self) -> None:
        table = CollationTable([(0x41, (10, 20, 30)), (0x42, (11, 21, 31))])
        self.assertIn(0x41, table)
        self.assertNotIn(0x43, table)
        self.assertEqual(len(table), 2)

    def test_codepoints_are_sorted(self) -> None:
        table = CollationTable([(0x42, (1, 2, 3)), (0x41, (1, 2, 3))])
        self.assertEqual(table.codepoints(), (0x41, 0x42))

    def test_rejects_out_of_range_codepoint(self) -> None:
        with self.assertRaises(ValueError):
            CollationTable([(0x110000, (1, 2, 3))])

    def test_rejects_wrong_weight_arity(self) -> None:
        with self.assertRaises(ValueError):
            CollationTable([(0x41, (1, 2))])  # type: ignore[arg-type]


class CollationElementsTests(unittest.TestCase):
    def test_empty_string_yields_no_elements(self) -> None:
        self.assertEqual(collation_elements(""), [])

    def test_known_character_uses_table(self) -> None:
        elements = collation_elements("a")
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0], CollationElement(0x1C47, 0x0020, 0x0002))

    def test_unknown_character_uses_implicit_weight(self) -> None:
        # U+4E00 is not in the curated table, so it must fall back to the
        # implicit algorithm.  The expected primary weight is
        # 0xFB40 + 0x4E00 = 0x14940, masked to 16 bits = 0x4940.
        elements = collation_elements("\u4e00")
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].primary, (0xFB40 + 0x4E00) & 0xFFFF)
        self.assertEqual(elements[0].secondary, 0x0020)
        self.assertEqual(elements[0].tertiary, 0x0002)

    def test_astral_character_uses_second_implicit_range(self) -> None:
        # U+1F600 is above 0x10000, so the second implicit base applies.
        elements = collation_elements("\U0001F600")
        self.assertEqual(len(elements), 1)
        expected = (0xFB80 + (0x1F600 - 0x10000)) & 0xFFFF
        self.assertEqual(elements[0].primary, expected)

    def test_rejects_non_string(self) -> None:
        with self.assertRaises(TypeError):
            collation_elements(b"abc")  # type: ignore[arg-type]

    def test_rejects_non_table(self) -> None:
        with self.assertRaises(TypeError):
            collation_elements("a", table={})  # type: ignore[arg-type]

    def test_explicit_table_is_used(self) -> None:
        table = CollationTable([(0x41, (1, 2, 3))])
        elements = collation_elements("A", table=table)
        self.assertEqual(elements, [CollationElement(1, 2, 3)])


class SortKeyTests(unittest.TestCase):
    def test_empty_string_has_empty_key(self) -> None:
        self.assertEqual(sort_key(""), b"")

    def test_ignorable_character_has_empty_key(self) -> None:
        # SPACE is ignorable at all levels in the curated table.
        self.assertEqual(sort_key(" "), b"")

    def test_key_is_bytes(self) -> None:
        self.assertIsInstance(sort_key("a"), bytes)

    def test_case_insensitive_primary_order(self) -> None:
        # 'a' and 'A' share a primary weight, so their primary bytes are
        # equal.  The tertiary weights differ, which is what makes the
        # full keys differ.
        key_a = sort_key("a")
        key_A = sort_key("A")
        self.assertNotEqual(key_a, key_A)
        self.assertEqual(key_a[:2], key_A[:2])

    def test_primary_order_is_numeric(self) -> None:
        # 'a' has primary 0x1C47, 'b' has 0x1C60, so 'a' sorts before 'b'.
        self.assertLess(sort_key("a"), sort_key("b"))

    def test_primary_weights_are_concatenated_before_secondary(self) -> None:
        # The key for "ab" must start with the primary weight of 'a',
        # then the primary of 'b', then the secondary weights.
        key = sort_key("ab")
        self.assertEqual(key[:2], (0x1C47).to_bytes(2, "big"))
        self.assertEqual(key[2:4], (0x1C60).to_bytes(2, "big"))
        # Secondary weights follow the two primaries.
        self.assertEqual(key[4:6], (0x0020).to_bytes(2, "big"))

    def test_deterministic_across_calls(self) -> None:
        self.assertEqual(sort_key("hello"), sort_key("hello"))

    def test_implicit_character_sorts_after_latin(self) -> None:
        # The implicit primary for U+4E00 is 0x4940, which is greater
        # than the Latin primaries, so it sorts after them.
        self.assertGreater(sort_key("\u4e00"), sort_key("z"))

    def test_explicit_table_is_used(self) -> None:
        table = CollationTable([(0x41, (1, 0, 0))])
        self.assertEqual(sort_key("A", table=table), b"\x00\x01")


class DefaultTableTests(unittest.TestCase):
    def test_default_table_is_a_collation_table(self) -> None:
        self.assertIsInstance(DEFAULT_TABLE, CollationTable)

    def test_default_table_contains_ascii_letters(self) -> None:
        self.assertIn(0x41, DEFAULT_TABLE)
        self.assertIn(0x7A, DEFAULT_TABLE)

    def test_default_table_is_not_mutated_by_use(self) -> None:
        before = len(DEFAULT_TABLE)
        sort_key("abc")
        self.assertEqual(len(DEFAULT_TABLE), before)


if __name__ == "__main__":
    unittest.main()
