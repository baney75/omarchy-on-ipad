# Contribution API and submission

How people and agents find the project contract, prepare a record, and submit it. Everything here runs offline. Nothing in this repository asks for, stores, or handles a token or password.

## Discovery

The published site serves a versioned machine contract, generated from repository data on every build:

| Endpoint | Contents |
| --- | --- |
| [`llms.txt`](https://baney75.github.io/omarchy-on-ipad/llms.txt) | Plain-text summary: current truth, installation state, lanes, research preflight, links |
| [`api/v1/index.json`](https://baney75.github.io/omarchy-on-ipad/api/v1/index.json) | Contract index: endpoints, schemas, policies, lanes, lane rules, commands, review states, research contract |
| [`api/v1/progress.json`](https://baney75.github.io/omarchy-on-ipad/api/v1/progress.json) | `data/progress.json` with derived check totals |
| [`api/v1/registry.json`](https://baney75.github.io/omarchy-on-ipad/api/v1/registry.json) | Reviewed contribution records and the devices being worked on |
| [`api/v1/installation.json`](https://baney75.github.io/omarchy-on-ipad/api/v1/installation.json) | Installation availability and release requirements |

Schemas live under [`schemas/`](../schemas/) and are published at `/schemas/`. A breaking change to any endpoint ships under a new `api/v2/` path; `contract_version` names the version.

## Lanes

Pick one lane before you start: `python3 tools/contribute.py lanes`. The lanes and their checks are listed in [AGENTS.md](../AGENTS.md#contribution-lanes). Only `offline-research` uses the model preflight.

## Prepare a record

```sh
python3 tools/contribute.py new --id <id> --contributor <github-handle> --workstream <workstream-id> \
  --model <iPadN,N> --board <JNNNAP> --os-build <build> --agent "<human, or provider/model-id and version>" \
  --claim "<one bounded claim>" --evidence <kind>:contributions/<github-handle>/<file>
python3 tools/contribute.py check data/contributions/<id>.json
make check && make build
```

Rules the validator enforces:

- the filename equals the `id`; the `status` is `submitted` and there is no `review` block;
- evidence lives under `contributions/<your-handle>/` or `docs/`, with no symbolic links, dot segments, or hidden files, and is one of `.txt .json .md .csv .log .png` up to 2 MiB;
- every evidence hash matches its file;
- the safety flags stay in the read-only lane;
- `research-task` evidence must pass `research check --final`;
- `check` also scans the record and its text evidence for identifiers, credentials, emails, addresses, and local paths.

## Review states

| State | Meaning | In the registry |
| --- | --- | --- |
| `submitted` | Opened by a contributor; not reviewed | Counted, not listed |
| `verified_offline` | Reviewed: a check that could fail passed on artifacts | Listed |
| `verified_physical` | Reviewed: a check that could fail passed on identified hardware | Listed |
| `rejected` | Reviewed: the evidence did not support the claim | Listed |

Only a maintainer named in `.github/CODEOWNERS`, who is not the contributor, may add the `review` block (`reviewer`, `reviewed_at`, `pull_request`, `summary`) and set a reviewed state. A review block in a contributor's own pull request is refused by `tools/contribute.py check` and by maintainers. A listed record means it was reviewed for inclusion, not that it is universal proof or a safety guarantee.

## Submit

```sh
python3 tools/contribute.py submit-plan data/contributions/<id>.json
```

This prints the commands; it runs none of them. In a clone of your own fork, they are:

```sh
make check && make build
git switch -c contrib/<id>
git add -- data/contributions/<id>.json contributions/<github-handle>/<file>
git commit -m "Add contribution record <id>"
python3 tools/contribute.py pr-body data/contributions/<id>.json > "${TMPDIR:-/tmp}/omarchy-pr-<id>.md"
git push --set-upstream origin contrib/<id>
gh pr create --repo baney75/omarchy-on-ipad --base main --head <github-handle>:contrib/<id> \
  --title "Contribution: <id>" --body-file "${TMPDIR:-/tmp}/omarchy-pr-<id>.md"
```

`gh` uses the login you already have. Never paste a token into a prompt, a file, or an agent. A maintainer reviews and merges; do not merge your own pull request, and nothing merges automatically.

## Installation

[`data/installation.json`](../data/installation.json) is the single source of truth. Its state is `unavailable`: no iPad installer, image, or release exists. The validator refuses `available` unless every milestone is complete, progress records installed systems and untethered cold boots, and each release lists exact model, board, and build compatibility, SHA-256 hashes and sizes, a source commit and attestation, reviewed `verified_physical` records for install, recovery, and rollback on compatible devices, at least three cold boots, and two different reviewers (human and security). Until then the site offers no download or install command.
