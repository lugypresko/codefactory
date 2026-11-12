"""Minimize a pytest log to failing test ids + assertion/exception message lines (no test source, no gt)."""
import re
CAP = 2000
_E = re.compile(r"^E\s+.*")

def _sections(log):
    """Split a pytest --tb=short log into {node_id: raw section} when possible."""
    out, cur, buf = {}, None, []
    for line in (log or "").splitlines():
        m = re.match(r"^_+ (.+) _+$", line.strip())
        if m and "FAILURES" not in m.group(1) and "ERRORS" not in m.group(1):
            if cur: out.setdefault(cur, []).append("\n".join(buf))
            cur, buf = m.group(1).strip(), []
            continue
        buf.append(line)
    if cur: out.setdefault(cur, []).append("\n".join(buf))
    return out

def _e_lines(section):
    """Keep only pytest 'E ' assertion/exception lines; drop source ('>') and code context."""
    return [ln for ln in section.splitlines() if _E.match(ln.rstrip())]

def _match(unit, sections):
    if unit in sections: return sections[unit]
    # unit may be a full node id; headers often use the function name only
    tail = unit.split("::")[-1]
    hits = [s for k, v in sections.items() if k == tail or k.endswith(tail) or tail in k for s in v]
    return hits

def minimize(log, unit_ids, cap=CAP):
    """Return a truncated string: one block per unit id, then its E-lines (if any)."""
    sections = _sections(log)
    chunks = []
    for u in unit_ids or []:
        e = []
        for sec in _match(u, sections):
            e.extend(_e_lines(sec))
        # de-dupe preserving order
        seen, uniq = set(), []
        for ln in e:
            if ln not in seen:
                seen.add(ln); uniq.append(ln)
        chunks.append(u if not uniq else u + "\n" + "\n".join(uniq))
    text = "\n\n".join(chunks)
    if cap and len(text) > cap:
        text = text[:cap] + "\n...[truncated]"
    return text
