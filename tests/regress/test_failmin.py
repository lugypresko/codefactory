"""Unit tests for minimized B failure output: ids + E-lines only, no test source, size cap."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "lib"))
from failmin import minimize, CAP

LOG = """
============================= test session starts ==============================
_____________________ test_split_even_remainder _____________________
tests/test_issue.py:8: in test_split_even_remainder
    assert sum(p) == 10
E       AssertionError: assert 9 == 10
E       +  where 9 = sum([3, 3, 3])
______________ TestFoo.test_other ______________
>       raise ValueError("boom")
E       ValueError: boom
=========================== short test summary info ============================
FAILED tests/test_issue.py::test_split_even_remainder - AssertionError
FAILED tests/test_issue.py::TestFoo::test_other - ValueError
"""

def test_keeps_ids_and_E_lines_drops_source():
    text = minimize(LOG, ["tests/test_issue.py::test_split_even_remainder", "tests/test_issue.py::TestFoo::test_other"])
    assert "tests/test_issue.py::test_split_even_remainder" in text
    assert "E       AssertionError: assert 9 == 10" in text
    assert "E       ValueError: boom" in text
    # no test source
    assert "assert sum(p) == 10" not in text
    assert 'raise ValueError("boom")' not in text
    assert ">       " not in text

def test_cap_truncates():
    text = minimize(LOG, ["tests/test_issue.py::test_split_even_remainder"], cap=40)
    assert text.endswith("...[truncated]")
    assert len(text) <= 40 + len("\n...[truncated]")

def test_empty_units():
    assert minimize(LOG, []) == ""

if __name__ == "__main__":
    test_keeps_ids_and_E_lines_drops_source(); test_cap_truncates(); test_empty_units()
    print("failmin ok")
