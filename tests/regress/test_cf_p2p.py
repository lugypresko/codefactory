"""CF opt-in P2P matching finds tests/test_split.py; LC-1A.0 import-only default does not."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "lib"))
from p2p_gate import select_p2p_files

TFILE = "tests/test_split.py"
# The project test imports the function from the package, not the module stem `split`.
TEXT = "import pytest\nfrom cfdemo import split_even\n\ndef test_split_even_two_equal_parts():\n    assert split_even(10, 2) == [5, 5]\n"
STEMS = ["split"]

def test_default_import_match_misses_package_import():
    sel = select_p2p_files([TFILE], STEMS, {TFILE: TEXT}, name_match=False)
    assert sel == []

def test_cf_name_match_selects_test_split():
    sel = select_p2p_files([TFILE], STEMS, {TFILE: TEXT}, name_match=True)
    assert sel == [TFILE]

def test_does_not_select_unrelated_or_generated_without_stem():
    others = {
        "tests/test_other.py": "def test_x():\n    assert True\n",
        TFILE: TEXT,
    }
    sel = select_p2p_files(list(others), STEMS, others, name_match=True)
    assert sel == [TFILE]

def test_import_match_still_works_when_module_is_imported():
    txt = "from cfdemo.split import split_even\n"
    sel = select_p2p_files([TFILE], STEMS, {TFILE: txt}, name_match=False)
    assert sel == [TFILE]

if __name__ == "__main__":
    test_default_import_match_misses_package_import()
    test_cf_name_match_selects_test_split()
    test_does_not_select_unrelated_or_generated_without_stem()
    test_import_match_still_works_when_module_is_imported()
    print("cf_p2p ok")
