"""Select existing project test files for the stage-3 P2P gate.

Default (LC-1A.0): import/from of a changed module stem.
CF opt-in name_match: also match test filenames that contain the stem
(e.g. tests/test_split.py for a change in src/cfdemo/split.py), which
catches `from cfdemo import split_even` that never mentions `split`.
"""
import os, re

def select_p2p_files(tfiles, stems, texts, name_match=False, cap=10):
    """Return up to cap test paths selected from tfiles.

    texts: dict path -> file contents. stems: changed non-test module basenames.
    """
    sel = []
    stems = [s for s in stems if s]
    for f in sorted(tfiles):
        txt = texts.get(f, "")
        if any(re.search(r"(import|from)\s+[\w.]*\b%s\b" % re.escape(s), txt) for s in stems):
            sel.append(f)
            continue
        if name_match:
            base = os.path.splitext(os.path.basename(f))[0]
            parts = set(base.split("_"))
            if any(s in parts for s in stems):
                sel.append(f)
    return sel[:cap]
