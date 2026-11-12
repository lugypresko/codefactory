import pytest
from cfdemo.split import split_even

def test_split_even_remainder_basic():
    total = 10
    n = 3
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts: # only check if parts is not empty
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"

def test_split_even_remainder_large_numbers():
    total = 100
    n = 7
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts:
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"

def test_split_even_remainder_n_greater_than_total():
    total = 5
    n = 7
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts:
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"

def test_split_even_remainder_zero_total():
    total = 0
    n = 5
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts:
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"

def test_split_even_remainder_n_is_one():
    total = 100
    n = 1
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts:
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"

def test_split_even_remainder_no_remainder():
    total = 12
    n = 3
    parts = split_even(total, n)
    assert sum(parts) == total, f"Sum of parts ({sum(parts)}) does not equal total ({total})"
    assert len(parts) == n, f"Length of parts ({len(parts)}) does not equal n ({n})"
    assert all(isinstance(p, int) and p >= 0 for p in parts), "Parts must be non-negative integers"
    if parts:
        assert max(parts) - min(parts) <= 1, f"Parts differ by more than 1: {parts}"
