# Contributing

The fastest useful contribution is one bounded claim with evidence that another person can check. You do not need to solve the whole boot chain.

## Before you start

By contributing, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md), the [security policy](SECURITY.md), and the truth levels in the [claim ladder](docs/CLAIM-LADDER.md).

Never commit or paste:

- serial numbers, UDIDs, ECIDs, pairing records, Apple IDs, email addresses, IP addresses, device names, local paths, hostnames, tokens, keys, nonces, tickets, or signing material;
- Apple firmware, decrypted system binaries, IPSWs, IPAs, DMGs, disk images, compiled payloads, crash dumps containing private data, or third-party code without a redistribution license;
- weaponized exploit chains, malformed physical-test inputs, persistence payloads, or steps that bypass platform security;
- claims that Linux booted, Omarchy was installed, or a cold boot is untethered without the evidence required by the claim ladder.

## Choose a contribution lane

### 0. Live progress log

Use the **Progress update** issue form while a bounded human or agent task is under way. Disclose the agent/model, select the evidence state, link only sanitized public evidence, and name the next pass/fail check. This is the fastest public update path, but it is not a verification path: an issue cannot change milestone counts or promote a claim. Reviewed evidence must land through a pull request.

### 1. Device and build matrix

Use this for an Apple-silicon iPad you own or are authorized to test. On a Mac with Xcode command-line tools:

```sh
python3 tools/collect_readonly.py --output my-device.json
cat my-device.json
```

Read the output. It should contain only physical iPads and their model, board, platform, OS version/build, transport, and developer-mode state. Raw `devicectl` output is suppressed. If anything identifying appears, do not share it; open a normal bug report describing the field name without its value.

Open the **Device result** issue form and attach the sanitized JSON, or turn it into a structured contribution record using `data/contributions/example.json.example`.

### 2. Offline research

Pick one open request from the dashboard. State one falsifiable question, prefer original project code or first-party documentation, record exact versions/hashes, and separate what the source proves from your inference. Keep copyrighted artifacts local.

### 3. Code or site improvement

Keep the build dependency-free unless maintainers approve a dependency first. Run:

```sh
make check
make build
```

Open `_site/index.html` locally if you changed presentation. The committed source of truth is under `site/`; `_site/` is generated and ignored.

### 4. Possible native-entry or security finding

Stop before public details. Follow [SECURITY.md](SECURITY.md) and use GitHub private vulnerability reporting. Public issues are for coordination that cannot enable exploitation.

## Structured progress records

Copy the example:

```sh
cp data/contributions/example.json.example data/contributions/YOUR-ID.json
```

Then:

- make the filename match the record `id`;
- use a public GitHub handle, not a real name or email;
- name the agent and version if an agent did material work;
- keep each claim narrow;
- hash every evidence file with `shasum -a 256`;
- keep all public contribution safety flags in the read-only lane;
- run `make check` before opening the pull request.

The main progress file is maintainer-owned. A contribution record does not automatically change headline counts; maintainers update those only after review.

## Agent-authored pull requests

Agent work is welcome when it is auditable.

1. Put the agent/model in the contribution record or pull-request description.
2. Give the agent a bounded task and a named done check.
3. Require it to cite primary sources for technical claims.
4. Inspect every generated file and command before submission.
5. Never give an external agent device credentials, signing assets, private receipts, or unpublished vulnerability details.
6. A human remains responsible for the pull request.

For difficult reasoning, use a current GPT-6 Daybreak reasoning mode or a capable local model with enough context to read `AGENTS.md`. Routine validation and formatting can use a smaller local agent. Model choice never relaxes the evidence or safety gates.

## Pull-request checklist

- [ ] The claim is bounded and its state is accurate.
- [ ] No private identifier, credential, local path, or copyrighted artifact is included.
- [ ] Evidence files are repository-relative and SHA-256 pinned.
- [ ] No malformed physical test, storage write, reboot/recovery action, or exploit payload is introduced through the public lane.
- [ ] `make check` passes.
- [ ] The dashboard builds with `make build`.
- [ ] Sources, licenses, and upstream credit are recorded.
- [ ] Agent use is disclosed.

Maintainers may close speculative, unsafe, duplicated, unactionable, or overclaimed submissions while preserving useful evidence in a better-scoped follow-up.
