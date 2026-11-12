# Offline gate (publishing is not wired)

The coding agent never receives a GitHub credential. It returns a unified diff from a sandbox with no network. This repository now has the **gate** that must accept that diff before anything is published. The gate is a separate process from the agent. It is offline. It does not mint a token, push, open a pull request, approve, comment a verdict, or merge.

Publishing is a later choice. `broker/publish.py` is an interface with one method, `open_draft`, and that method always raises `NotImplementedError`. The gate does not import it. Two candidate routes are recorded at the bottom of this file and neither is implemented.

## Run the gate

```bash
python3 broker/gate.py verify \
  --task task.json \
  --diff agent.diff \
  --evidence work/runs/<id>/evidence_manifest.json \
  --repo work/repo \
  --policy task/diff_policy.json \
  --receipt work/receipt.json
```

`--policy` defaults to `task/diff_policy.json`. `--repo` is a local checkout of the **product** tree the policy describes (`cart/*` and `tests/*` at the root). After `./bootstrap.sh`, that tree is `work/repo`. It is not a path under `task/`: `task/**` is protected by the same policy, and the gate does not remap paths.

`task.json` is intake metadata. The gate checks it locally and does not talk to GitHub:

| field | meaning |
|---|---|
| `owner`, `repo`, `issue_number`, `title`, `body` | the issue the diff claims to address |
| `base_sha` | 40 hex characters, the commit the diff was built on |
| `base_ref` | local branch whose tip must still be `base_sha` (default `main`) |
| `task_key` | `{owner}/{repo}#{number}:` plus the sha256 of the issue body, UTF-8, no newline normalization |

Exit `0` prints a receipt and, with `--receipt`, writes the same JSON. Any failure exits `1`, prints `{"ok": false, "reason": "...", "detail": "..."}`, and does not write a receipt. The target branch is not moved.

### Evidence layout

The manifest is the file `evidence-seal` writes at `work/runs/<id>/evidence_manifest.json`.

- `inputs` and `outputs` keys `run/<name>` are files in that run directory (`final.diff`, `report.json`, `trajectory.json`, …).
- Keys `evals/<name>` are `work/evals/<id>/<name>`.
- `git_diff_base_final_sha256` is the sha256 of the raw diff bytes.
- `base_sha` must equal the task and the local branch tip.

Every listed hash is recomputed from the file bytes. A missing file, an extra byte, or a verdict other than `lc0_verdict: PASS` (and `decision: PASS` when that field is present) is a failure. The gate does not re-run the hidden tests and does not start Docker.

### What is refused

In this order:

| reason | condition |
|---|---|
| `TASK_INVALID` | task JSON is incomplete, or `task_key` does not match the body |
| `DIFF_TOO_LARGE` | diff is larger than 100_000 bytes |
| `BINARY_FILE` | NUL byte, `GIT binary patch`, or `Binary files` |
| `SYMLINK` | mode `120000` in the diff or in the index after apply |
| `MALFORMED_DIFF` | not a unified diff, or `git apply --check` fails |
| `PROTECTED_PATH` | any path under `.github/` or `.git/`, or a file named `CODEOWNERS` |
| `HIDDEN_TEST` | any path containing `hidden_tests` or `locked_p2p` |
| `DIFF_HASH` | diff sha256 ≠ `git_diff_base_final_sha256` or the sealed `run/final.diff` |
| `EVIDENCE_HASH` | a sealed file is missing or its sha256 does not match |
| `VERDICT` | sealed report is not `lc0_verdict` PASS |
| `STALE_BASE` | task base, manifest base, `agent_result.base_sha`, and `refs/heads/<base_ref>` are not the same commit |
| `EXISTING_TEST` | v1.5 diff policy: a pre-existing test file changed |
| `OUT_OF_SCOPE` | v1.5 diff policy: outside `scope_paths`, or a new file that is not allowed |
| `DIFF_POLICY` | any other v1.5 policy violation, or the policy could not be evaluated |

`lib/lc0util.py` `diff_policy` is called on a temporary commit of the applied diff. That commit is not put on a branch. A sealed PASS does not override these refusals: a verdict that says PASS while the diff touches `.github/workflows` or an existing test is still refused.

### Receipt

```json
{
  "ok": true,
  "reason": "PASS",
  "task_key": "acme/widget#7:<sha256>",
  "base_sha": "<40 hex>",
  "diff_sha256": "<sha256 of agent.diff>",
  "verdict": "PASS",
  "policy": "OK",
  "checked_sha": "<local commit created only to run diff_policy>",
  "published": false
}
```

`published` is always false. There is no `pr_url`.

## Threat model

The agent and the gate are different identities. The agent’s interface ends at the diff. The gate’s job is to refuse a diff that is not exactly the sealed, passing, still-applicable change.

What the gate actually stops, and what it does not:

| Stopped | Not stopped |
|---|---|
| A diff whose bytes are not the sealed `final.diff` | A wrong PASS that the evaluator itself emitted. The gate trusts a sealed PASS; it does not re-execute hidden tests. |
| A rewritten trajectory, report, or eval file | The Docker image id recorded on the manifest. Matching it needs a local image and is not a file hash, so this gate does not compare it. |
| A base that is no longer the local branch tip | A remote branch that moved after this checkout was last updated. The comparison is local. There is no fetch. |
| `.github/`, `CODEOWNERS`, hidden tests, symlinks, binaries, oversize diffs, edits of existing tests, paths outside `cart/*` and `tests/*` | Logic smuggled into an in-scope edit of `cart/cart.py`. The v1.5 policy allows that file to change. The hidden tests are what catch a wrong product, and only if the sealed verdict is honest. |
| `git apply` that does not match the base tree | A later publisher that ignores the receipt, pushes a different diff, or merges. Nothing in this change can publish. |

Hidden tests still live in this repository (`task/hidden_tests/`). The gate refuses a diff that touches them. Anyone who can read the repo can still read them. That gap is unchanged from `docs/LC-1A.md`.

`checked_sha` is an unreachable commit in the local object store, created so `diff_policy` can compare two commits. It is not a branch and it is not pushed. `git gc` may delete it.

## Evaluator on draft pull requests

`.github/workflows/evaluator.yml` triggers on `pull_request` and `merge_group` only. The default `pull_request` activities are `opened`, `synchronize`, and `reopened`, and GitHub runs those for draft pull requests. The workflow does not skip `github.event.pull_request.draft`. It does not use `pull_request_target`. Its token is `contents: read` and it references no secrets. This change does not alter that behavior. When a publisher exists, it must open drafts and must not add a draft skip to this workflow.

The job still evaluates the known-bad toy-task base from `VERSIONS` and expects exit 1 with decision `FAIL`. It does not yet score the agent diff. A green `evaluator` check is the sanity check described in `docs/LC-1A.md`, not a statement that the gate ran inside CI.

## Publishing (not implemented)

`Publisher.open_draft(receipt)` raises `NotImplementedError`. Do not store an app private key or an Actions secret for this change until the route is confirmed. Whichever route is chosen, it has to keep these constraints:

- The agent process still has no `GITHUB_TOKEN`, `GH_TOKEN`, or credentialed git remote.
- The publisher is a different identity from the agent. It may open a **draft** pull request. It must not merge, approve, or post a verdict comment.
- The only ref it may push is an isolated branch such as `cf/issue-<n>-<short key>`, never `main`.
- The GitHub App, if one is used, is installed only on `lugypresko/codefactory`.
- Repository permissions, and no others: Contents read and write, Pull requests read and write, Issues read, Metadata read. **No Workflows, no Administration, no Checks.** Without Workflows, GitHub rejects a push that changes `.github/workflows` even if the gate were bypassed. Without Administration, the app cannot edit the ruleset. Without Checks, it cannot mark `evaluator` green.
- The private key, if the route needs one, stays outside the repo, mode `0600`, and is never committed or logged. An installation token is minted at runtime and expires in about an hour.
- A second submit of the same task key must return the existing pull request and must not open another one.

### Candidate A — GitHub App, token minted in Actions

`actions/create-github-app-token` mints the installation token inside a workflow from the App ID and the private key stored as an Actions secret. `peter-evans/create-pull-request` can then push the already-gated commit and open the draft. The workflow that holds the secret must be the one on the default branch, must not be `pull_request_target`, and must not be a file the agent diff can change (the gate refuses `.github/**` anyway). The evaluator workflow stays secret-less.

If this route is confirmed, create the App by hand:

1. GitHub → Settings → Developer settings → GitHub Apps → New GitHub App.
2. Any name. Homepage can be `https://github.com/lugypresko/codefactory`. Uncheck the webhook; there is no webhook server.
3. Repository permissions: Contents **Read and write**, Pull requests **Read and write**, Issues **Read-only**. Leave Metadata at **Read-only**. Do not add Workflows, Administration, or Checks.
4. Installation: only this account. Create the app.
5. Generate a private key. Store it outside the clone, mode `0600` (for example `~/.config/codefactory/broker.pem`). Do not put it in the repo, even as a sample.
6. Install the app on **lugypresko/codefactory only**. The installation id is the number in `https://github.com/settings/installations/<id>`. The App ID is on the app’s settings page.
7. Put the App ID and the private key in Actions secrets for the workflow that will mint the token. Do not put them in the agent sandbox.

### Candidate B — GitHub App, token minted by a local broker

Same app, same permissions, same install, same private-key location. A local process would mint the RS256 JWT and exchange it for an installation token. That code is intentionally absent.

## Ruleset, after pull requests exist

`docs/LC-1A.md` already has the ruleset JSON. Applying it needs an account with repository administration. An earlier attempt from this automation returned 403, and `GET /repos/lugypresko/codefactory/rulesets` was empty. This change does not apply it.

Once pull requests are opened by an app identity rather than by a person, an admin applies that JSON with `bypass_actors` left empty. The settings that matter:

| setting | value | why |
|---|---|---|
| Required approving reviews | `1` | a second identity has to approve |
| Require review from Code Owners | `true` | `.github/**`, `task/**`, `evaluate.sh`, `lib/**`, and `docker/**` need `@lugypresko` |
| Dismiss stale reviews on push | `true` | a new commit on the branch drops the old approval |
| Required status check | context `evaluator`, strict | the check must pass against the latest `main` |
| Block force pushes and deletion | on | the app cannot rewrite `main` |
| Bypass actors | empty | the app is not an exception |

Do not add the app as a code owner and do not add it to `bypass_actors`. Pull-request write is enough for the app to *call* the approve or merge API if someone later writes that call. The ruleset is what makes the call fail. The publisher must not contain the call. `require_code_owner_review` is what stops the app satisfying the review by itself, as long as the app is not a code owner.

After the first green `evaluator` run, the status check can be pinned to the GitHub Actions integration id from that check run, so another app cannot satisfy the context name. That step is also in `docs/LC-1A.md`.
