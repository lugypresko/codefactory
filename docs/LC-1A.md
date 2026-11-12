# LC-1A — Evaluator CI under Zero Trust

LC-1A puts the LC-0 evaluator on the path into `main`. The agent proposes a change. It does not push, open, approve, or merge that change. A separate broker and a required check do those jobs, and a person owns the verifier.

## Roles

| Actor | What it may do | What it must not have |
|---|---|---|
| Agent | Read the task it is given. Return a diff (and its local trace). | A GitHub token, git credentials, permission to push, permission to open or approve a PR, the hidden tests. |
| Broker | From a run id, a base SHA, and a diff: create `agent/<run-id>`, apply the diff, push that branch, open a PR to `main`. | Permission to push to `main`, to approve or merge, to edit rulesets, or to change the evaluator. |
| Evaluator CI | On the PR head SHA (and again in the merge queue), run the harness offline and publish a check named `evaluator`. | Secrets. Write access to repository contents. `pull_request_target`. |
| Human owner (`@lugypresko`) | Review CODEOWNERS paths. Approve. Merge through the queue. | — |

The agent process is not given `GITHUB_TOKEN`, `GH_TOKEN`, or a git remote with credentials. Its interface ends at the diff. Nothing in the agent path calls the GitHub API.

## Broker

The broker is deterministic. The same `(run-id, base SHA, diff)` produces the same branch name and the same tree.

1. Start from the recorded base SHA. Do not start from a floating branch tip.
2. Create `agent/<run-id>`. The run id is the only variable in the branch name. Re-running the same id updates that branch; it does not invent a second name.
3. Apply the diff with `git apply` (or an equivalent that fails on a fuzzy match). A diff that does not apply is an error. The broker does not ask the agent to retry inside the push step.
4. Commit with a fixed message that includes the run id and the diff hash. Author and committer are the broker identity, not the agent.
5. Push `agent/<run-id>` with a token whose only content right is pushing those branches.
6. Open a pull request into `main`. The body records the run id, the base SHA, and the diff hash. The broker does not approve, dismiss reviews, or merge.

GitHub then binds every check to the commit that was pushed. A later push to the same branch is a new head SHA. The previous `evaluator` conclusion does not carry over, and stale approvals are dismissed by the ruleset below.

## Evaluator check

Workflow: `.github/workflows/evaluator.yml`.

- Events: `pull_request` and `merge_group` only. There is no `pull_request_target`. `pull_request_target` would execute the workflow definition from `main` and would hand the job a token that can write to the base repository. This check must not have that token.
- `permissions: contents: read`. No other token scope is requested. The workflow does not read `secrets`.
- The check run name is the job id `evaluator`. That is the status-check context the ruleset requires. GitHub attaches the conclusion to the head SHA of the pull request, or to the merge-group commit when the queue runs it.
- Steps, in order: checkout (credentials not persisted), Python 3.12, `./bootstrap.sh` (Docker on `ubuntu-latest`), `./selftest.sh` (offline verdict tests, no LLM), then `./evaluate.sh` on the toy-task base commit in `VERSIONS` (`base_commit_sha`).
- Sanity expectation for that base commit: exit `1` and JSON `"decision": "FAIL"`. The base tree does not implement the feature, so a PASS here would mean the evaluator is blind. `ERROR` (exit 3), `ESCALATE` (exit 4), `PASS` (exit 0), usage errors (exit 2), a missing or unreadable report, or any other exit fails the job.
- The JSON report is uploaded as the `evaluator-reports` artifact even when the sanity step fails. A missing report fails the upload, so a run that produced no report is still red.

This LC-1A job proves the evaluator fails closed on the known-bad base. It does not yet score an agent diff. Scoring `agent/<run-id>` is a later change to the same required check, still bound to the PR head SHA.

`selftest.sh` without a saved agent run executes the offline cases and skips the end-to-end cases that need `work/runs/A-control`. Those cases need an LLM trace; CI does not call a model.

## Hidden tests (known gap)

`task/hidden_tests/` is in this repository today. The agent sandbox does not mount that directory, but anyone who can read this repo can read the tests, and so can an agent that is handed the repo.

That is a known gap. The hidden tests and their pinned hashes move to a separate private repository. The evaluator workflow checks that repository out with a credential the agent and the broker do not have, and it checks the file hashes before and after the run, as `evaluate.sh` already does against `task/manifest.json`. Until that move, a green `evaluator` check does not mean the tests were hidden from the proposer.

`task/**` is CODEOWNERS-protected so a change to the tests that are still here requires `@lugypresko`.

## CODEOWNERS

`.github/CODEOWNERS` requires `@lugypresko` for:

- `.github/**` — workflow and owners file
- `task/**` — task statement, manifest, diff policy, hidden tests, toy repo
- `evaluate.sh`
- `lib/**`
- `docker/**`

A pull request that touches any of those paths cannot merge until that review is present. The agent has no way to grant it.

## Ruleset for `main`

One repository ruleset, enforcement `active`, target `branch`, condition `refs/heads/main`. `bypass_actors` is empty: admins do not bypass. No actor may force-push, delete `main`, or merge without the pull request rules.

Rules, in the form accepted by `POST /repos/lugypresko/codefactory/rulesets`:

```json
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["merge", "squash", "rebase"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "evaluator" }
        ]
      }
    },
    { "type": "non_fast_forward" },
    { "type": "deletion" },
    {
      "type": "merge_queue",
      "parameters": {
        "check_response_timeout_minutes": 60,
        "grouping_strategy": "ALLGREEN",
        "max_entries_to_build": 5,
        "max_entries_to_merge": 5,
        "merge_method": "MERGE",
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5
      }
    }
  ]
}
```

What each setting does:

| Setting | Rule | Value |
|---|---|---|
| Require a pull request before merging | `pull_request` | enabled |
| Required approvals | `required_approving_review_count` | `1` |
| Require review from Code Owners | `require_code_owner_review` | `true` |
| Dismiss stale pull request approvals when new commits are pushed | `dismiss_stale_reviews_on_push` | `true` |
| Require status checks to pass | `required_status_checks` | context `evaluator` |
| Require branches to be up to date before merging | `strict_required_status_checks_policy` | `true` |
| Do not skip checks when creating a branch | `do_not_enforce_on_create` | `false` |
| Block force pushes | `non_fast_forward` | enabled |
| Block deletion | `deletion` | enabled |
| Require merge queue | `merge_queue` | enabled, `ALLGREEN`, method `MERGE`, minimum group size `1` |

`require_last_push_approval` stays `false`. The control that stops the agent approving itself is that the agent has no token and is not a CODEOWNER. The human owner can approve a broker push. `required_review_thread_resolution` stays `false`; it was not part of this gate. Merge methods on the pull-request rule stay open so the queue is the restriction: the queue merges with `MERGE`, and `ALLGREEN` means every queued pull request must pass `evaluator`, not only the group head. `strict_required_status_checks_policy` is the up-to-date requirement: the check has to pass against the latest `main`. The queue re-runs `merge_group` on the merge commit, so the conclusion is for that SHA.

The status check context is the job id `evaluator`. It is not pinned to a GitHub App id in this ruleset. After the first green run, the check source can be tightened to the GitHub Actions integration id reported on that check run.

## Ruleset creation

The creation attempt is recorded below. If it failed, apply the JSON in this document with an account that has repository administration on `lugypresko/codefactory`. Do not add a bypass actor.

<!-- RULESET_RESULT -->
Attempted on 2026-11-12 with this run's GitHub token (`POST /repos/lugypresko/codefactory/rulesets`, body as above).

- Result: **403** `Resource not accessible by integration`.
- The response asks for `administration=write` (`X-Accepted-GitHub-Permissions: administration=write`). This token does not have it. `GET /user` is also 403, so there is no user identity here that can administer the repo.
- `GET /repos/lugypresko/codefactory/rulesets` returned 200 and `[]`. No ruleset exists. `main` is not protected by the settings in this document until an admin creates them.
- The same token can push branches. It cannot create rulesets, and it was not given a bypass.

An admin applies the JSON above unchanged, with `bypass_actors` left empty. After the first green `evaluator` run, the status-check entry can be tightened with the GitHub Actions `integration_id` from that check run so a different app cannot satisfy the context.
<!-- /RULESET_RESULT -->
