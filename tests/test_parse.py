"""Tests for utils.parse_size and parse_pages."""
import pytest

from pdf_tool.utils import parse_size, parse_pages


def test_parse_size_units():
    assert parse_size("4MB") == 4 * 1024 ** 2
    assert parse_size("500KB") == 500 * 1024
    assert parse_size("1GB") == 1024 ** 3
    assert parse_size("4194304") == 4194304
    assert parse_size(" 4 mb ") == 4 * 1024 ** 2


def test_parse_pages_basic():
    assert parse_pages("1,3-5,8", 10) == [1, 3, 4, 5, 8]


def test_parse_pages_discrete_noncontiguous():
    # The exact case that was broken before: 1,8,11-13 must NOT expand to 1..13.
    assert parse_pages("1,8,11-13", 13) == [1, 8, 11, 12, 13]


def test_parse_pages_reversed_range():
    assert parse_pages("5-2", 10) == [2, 3, 4, 5]


def test_parse_pages_duplicates_preserved():
    assert parse_pages("1,1,3", 5) == [1, 1, 3]


def test_parse_pages_out_of_range():
    with pytest.raises(ValueError):
        parse_pages("1-99", 5)


def test_parse_pages_empty_spec():
    with pytest.raises(ValueError):
        parse_pages("", 5)


def test_parse_pages_allow_empty():
    assert parse_pages("", 5, allow_empty=True) == []


def test_parse_pages_bad_token():
    with pytest.raises(ValueError):
        parse_pages("1-abc", 5)