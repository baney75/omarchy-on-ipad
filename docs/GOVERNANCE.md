# Governance

## Decision model

Donovan Baney is the initial maintainer and final publisher of project-level claims. Technical authority comes from reproducible evidence, not title or model output.

Maintainers may delegate bounded implementation and review, but retain responsibility for:

- headline progress and claim-state changes;
- physical-device safety and authorization;
- coordinated disclosure;
- workflow permissions and publication;
- licensing, attribution, and trademark boundaries.

## Contribution review

Routine documentation and tests require one maintainer review. Changes to progress counts, security policy, workflows, schemas, collectors, device instructions, or trademark language require explicit maintainer review and all CI gates.

A contribution can be accurate yet remain unmerged if it exposes private data, creates unreasonable physical risk, lacks redistribution rights, duplicates work, or cannot change an implementation decision.

## Progress updates

The dashboard is rebuilt from the default branch. External records first land as pull requests. A merged contribution may appear in the activity feed before it changes a milestone count. Counts change only after evidence meets the claim ladder.

## Project changes

Material changes to scope, governance, safety policy, or naming should use a public issue or discussion unless disclosure itself would be unsafe. Security-sensitive changes follow `SECURITY.md`.

## Succession

Additional maintainers may be added after sustained, evidence-quality contributions and demonstrated respect for privacy and device safety. If the project becomes inactive, the repository remains an evidence archive; forks must preserve upstream licenses and should not imply endorsement.
