"""Frozen selection rule (written before any verification or generation run).
Source: nebius/SWE-rebench-leaderboard parquet splits 2026_01, 2026_02, 2026_03 (sha256 in data/SHA256SUMS).
Rule:
  1. sort all rows by created_at DESC (tie-break instance_id ASC)
  2. drop rows with a non-empty `interface` field (*_interface variants carry an augmented, non-original problem statement)
  3. require docker_image, patch, test_patch, FAIL_TO_PASS non-empty
  4. require Docker Hub compressed image size <= 3.0 GB (box infra limit) and an amd64 image
  5. at most one instance per repo (first in order wins)
  6. walk the list in order; verify each on this box (verify.py); the first 12 that verify are the sample.
     Failures are logged in data/verification_log.jsonl with the reason and are NOT retried with tweaks.
"""
import json, urllib.request, time
rows = json.load(open('data/all_rows.json'))
rows.sort(key=lambda r: (r['created_at'], ''), reverse=True)
rows = sorted(rows, key=lambda r: r['instance_id']); rows.sort(key=lambda r: r['created_at'], reverse=True)
out, seen = [], set()
def hub(img):
    name, tag = img.split(':') if ':' in img else (img, 'latest')
    ns, repo = name.split('/', 1)
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(f'https://hub.docker.com/v2/repositories/{ns}/{repo}/tags/{tag}', timeout=30))
        except Exception as e:
            time.sleep(5 * (i + 1)); err = e
    return {'error': str(err)}
for r in rows:
    rec = {'instance_id': r['instance_id'], 'repo': r['repo'], 'created_at': r['created_at']}
    why = None
    if r.get('interface'): why = 'interface_variant'
    elif not (r['docker_image'] and r['patch'] and r['test_patch'] and r['FAIL_TO_PASS']): why = 'missing_fields'
    elif r['repo'] in seen: why = 'repo_already_selected_earlier'
    else:
        h = hub(r['docker_image'])
        size = h.get('full_size'); archs = [i.get('architecture') for i in h.get('images', [])]
        rec.update(size_gb=round(size / 1e9, 2) if size else None, archs=archs)
        if not size: why = 'hub_lookup_failed:' + str(h.get('error') or h.get('message'))[:80]
        elif 'amd64' not in archs: why = 'no_amd64'
        elif size > 3.0e9: why = 'image_too_large'
        else: seen.add(r['repo'])
    rec['excluded'] = why
    out.append(rec)
    if sum(1 for o in out if not o['excluded']) >= 30: break
json.dump(out, open('data/candidates.json', 'w'), indent=1)
for o in out: print(o['created_at'], o['instance_id'], o.get('size_gb'), o['excluded'])
