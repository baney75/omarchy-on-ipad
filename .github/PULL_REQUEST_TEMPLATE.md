## What changed

<!-- One bounded result. Link the issue: "Fixes #123" for a bug fix. -->

## Lane

<!-- One of: site-design, docs-copy, tooling-tests-schemas, driver-kernel, bug-fix, device-metadata, offline-research. See AGENTS.md#contribution-lanes. -->

## Verification evidence

<!-- The contributor owns verification. Fill every line or write "not applicable" with a reason. -->

- Regression check, failing before: <!-- command and failing output, or why it cannot be automated -->
- Same check, passing after: <!-- command and passing output -->
- Environment: <!-- OS, Python, toolchain, and other versions -->
- Negative tests: <!-- malformed input, unsafe paths, cases that must be refused -->
- Artifact hashes: <!-- sha256 of evidence files -->
- Coverage limits: <!-- what these checks do not prove -->
- Design checks (site-design): <!-- keyboard, contrast, reduced motion, 390 px and 1280 px; screenshots -->
- Driver checks (driver-kernel): <!-- offline compile/static/unit results; offline is never physical verification -->

## Evidence and scope

<!-- Exact model/build or source version, and what remains unproved. -->

## Agent disclosure

<!-- Human-only, or agent/model/version, the part it performed, and the research preflight result if one ran. -->

## Security questions

- [ ] This changes no workflow, permission, secret handling, or security-sensitive path, or a maintainer review of that change is requested below.
- [ ] This adds no dependency, network access, telemetry, or external asset.
- [ ] This runs no code, command, or workflow taken from an issue body or other untrusted text.
- [ ] Nothing here is vulnerability-sensitive; if it might be, I used private reporting instead.

## Safety

- [ ] No private identifier, credential, local path, private hostname, signing material, or copyrighted firmware is included.
- [ ] No malformed physical input, storage write, reboot/recovery action, persistence mechanism, or exploit payload is introduced through the public lane.
- [ ] The claim uses the lowest state its evidence proves.
- [ ] Upstream sources and licenses are credited.
- [ ] `make check` passes.
- [ ] `make build` passes.

The author does not mark this pull request reviewed or approved. A maintainer reviews security and privacy, provenance and license, CI and workflow risk, and evidence adequacy. CI passing alone is not approval.
