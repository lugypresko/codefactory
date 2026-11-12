import pytest
from cfdemo.intervals import merge_intervals

def test_empty_input():
    assert merge_intervals([]) == []

def test_single_interval_input():
    assert merge_intervals([[1, 5]]) == [[1, 5]]
    assert merge_intervals([[10, 20]]) == [[10, 20]]

def test_touching_intervals_merge():
    # Issue example: [1, 2] and [2, 3] should become [1, 3]
    assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]
    assert merge_intervals([[1, 5], [5, 10], [10, 15]]) == [[1, 15]]
    assert merge_intervals([[1, 5], [6, 10]]) == [[1, 5], [6, 10]] # Not touching, should remain separate

def test_overlapping_intervals_merge():
    # General overlapping case
    assert merge_intervals([[1, 5], [3, 7]]) == [[1, 7]]
    assert merge_intervals([[1, 10], [5, 15]]) == [[1, 15]]

def test_nested_intervals_merge():
    # Issue example: [2, 3] inside [1, 10]
    assert merge_intervals([[1, 10], [2, 3]]) == [[1, 10]]
    assert merge_intervals([[5, 7], [1, 10]]) == [[1, 10]]
    assert merge_intervals([[1, 10], [2, 8], [3, 7]]) == [[1, 10]]

def test_unsorted_intervals_merge():
    # Issue example: [[5, 7], [1, 3], [2, 6]] should yield [[1, 7]]
    assert merge_intervals([[5, 7], [1, 3], [2, 6]]) == [[1, 7]]
    assert merge_intervals([[10, 15], [1, 5], [3, 7]]) == [[1, 7], [10, 15]]
    assert merge_intervals([[10, 12], [1, 5], [13, 14], [3, 7]]) == [[1, 7], [10, 12], [13, 14]]

def test_complex_scenarios():
    # Mix of touching, overlapping, nested, and unsorted
    assert merge_intervals([[1, 3], [7, 9], [2, 5], [8, 10], [15, 17], [16, 18]]) == [[1, 5], [7, 10], [15, 18]]
    assert merge_intervals([[1, 2], [4, 6], [2, 4]]) == [[1, 6]]
    assert merge_intervals([[1, 10], [2, 3], [10, 12], [5, 7], [15, 20], [16, 18]]) == [[1, 12], [15, 20]]
    assert merge_intervals([[1, 5], [10, 15], [5, 10]]) == [[1, 15]] # All touching/overlapping, unsorted
