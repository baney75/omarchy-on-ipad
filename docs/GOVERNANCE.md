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

## Contributor vetting

Public contribution and trusted roles are different things.

- **Anyone may contribute.** New external contributors open issues and pull requests with no trust, merge rights, deployment credentials, or device access. A merged contribution is credited by public GitHub handle in its record, its pull request, and the registry. Credit is not a role.
- **Becoming trusted.** A candidate shows scoped, reproducible work across reviewed pull requests, with clean provenance, privacy, and security compliance. The repository owner, Donovan Baney, decides explicitly and records the decision in a reviewed pull request that adds the person to `.github/CODEOWNERS` or this file.
- **Never automatic.** No role follows from a model label, a test score, a contribution count, or an agent's own claim. No workflow grants repository access or collaborator privileges; the owner makes that change by hand in the repository settings.
- **What vetting uses.** Only the public GitHub handle and public work history. Maintainers never collect legal names, government IDs, contact details, or other private personal data for vetting.
- **Trusted is not exempt.** Trusted contributors and maintainers still pass every check and the security review. A maintainer never reviews their own record.
- **Revocation.** The owner may revoke a role at any time by a reviewed pull request that removes it, and by removing access in the repository settings. Past records, reviews, and pull requests stay in history as the audit trail; nothing is deleted to revoke a role.

No trusted roster exists yet beyond the owner listed in `.github/CODEOWNERS`.

## Progress updates

The dashboard is rebuilt from the default branch. External records first land as pull requests. A merged contribution may appear in the activity feed before it changes a milestone count. Counts change only after evidence meets the claim ladder.

## Project changes

Material changes to scope, governance, safety policy, or naming should use a public issue or discussion unless disclosure itself would be unsafe. Security-sensitive changes follow `SECURITY.md`.

## Succession

Additional maintainers may be added after sustained, evidence-quality contributions and demonstrated respect for privacy and device safety. If the project becomes inactive, the repository remains an evidence archive; forks must preserve upstream licenses and should not imply endorsement.
