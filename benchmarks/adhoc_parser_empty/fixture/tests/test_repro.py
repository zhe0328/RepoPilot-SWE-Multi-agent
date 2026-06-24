"""Reproduction tests for user-reported empty-input bug (pre-authored for adhoc demo)."""

from list_parser import parse_items


def test_empty_string_returns_empty_list():
    assert parse_items("") == []


def test_single_item():
    assert parse_items("hello") == ["hello"]


def test_comma_separated_with_spaces():
    assert parse_items("a, b , c") == ["a", "b", "c"]
