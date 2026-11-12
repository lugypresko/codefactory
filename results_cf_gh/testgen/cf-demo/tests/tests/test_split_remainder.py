import pytest
from cfdemo import split_even

def check_split_properties(total, n, result):
    # Property 1: The returned list has length n
    assert len(result) == n

    # Property 2: sum(parts) == total
    assert sum(result) == total

    # Property 3: every element is a non-negative integer
    assert all(isinstance(x, int) and x >= 0 for x in result)

    # Property 4: elements differ by at most 1
    if n > 0: # Only relevant if there are elements to compare
        if len(result) > 1:
            assert max(result) - min(result) <= 1
        else: # For n=1, there's only one element, so diff is 0
            assert True

def test_split_even_with_remainder_basic():
    total = 10
    n = 3
    result = split_even(total, n)
    check_split_properties(total, n, result)
    # Specific assertion to fail the current buggy code
    assert result != [3, 3, 3]

def test_split_even_with_remainder_another_case():
    total = 7
    n = 3
    result = split_even(total, n)
    check_split_properties(total, n, result)
    assert result != [2, 2, 2]

def test_split_even_total_less_than_n():
    total = 2
    n = 3
    result = split_even(total, n)
    check_split_properties(total, n, result)
    assert result != [0, 0, 0]

def test_split_even_large_remainder():
    total = 10
    n = 4
    result = split_even(total, n)
    check_split_properties(total, n, result)
    assert result != [2, 2, 2, 2]

def test_split_even_total_is_zero_with_remainder_logic():
    # Although total=0 usually has no remainder, this ensures the logic holds
    # for such cases as well, preventing regressions if the fix is too specific.
    total = 0
    n = 3
    result = split_even(total, n)
    check_split_properties(total, n, result)
    assert result == [0, 0, 0] # Should pass even with the new logic

def test_split_even_one_total_multiple_parts():
    # total=1, n=3 -> should be [1, 0, 0] or permutation
    total = 1
    n = 3
    result = split_even(total, n)
    check_split_properties(total, n, result)
    assert result != [0, 0, 0]
