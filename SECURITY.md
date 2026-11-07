# Security policy

## Report privately

If you found a possible native-entry path, platform vulnerability, security bypass, unsafe device operation, credential exposure, CI compromise, or privacy leak, do **not** open a public issue or pull request.

Use [GitHub private vulnerability reporting](https://github.com/baney75/omarchy-on-ipad/security/advisories/new). Include the affected model/build, the smallest reproducible description, impact, preconditions, and whether any physical device operation occurred. Do not attach copyrighted firmware, personal identifiers, signing assets, credentials, or a weaponized payload.

If private reporting is temporarily unavailable, open a public issue containing only: “Private security contact needed.” Include no technical details.

## Coordinated handling

Maintainers will:

1. acknowledge a complete report when available;
2. reproduce offline or with benign diagnostics first;
3. separate crash/read/write/control-flow evidence from assumptions;
4. coordinate with the affected upstream or vendor when appropriate;
5. publish only after remediation or a responsible disclosure decision;
6. credit reporters who want public credit.

No response-time guarantee is offered. This is a volunteer research project, not a supported security product.

## Physical-device gate

Public contributions may use only the documented read-only collection lane. A possible malformed, exploitative, recovery, reboot, storage-writing, persistence, or firmware operation stays private and requires all of the following before any authorized-device test:

- exact model and build applicability;
- a concrete, operation-specific hypothesis and stop conditions;
- offline evidence that the operation can discriminate the hypothesis;
- independent review proportional to risk;
- explicit owner authorization for that exact operation;
- a recovery plan that has been read back and accepted.

General project approval is not approval for a specific risky device action.

## Repository and CI security

- Workflows use least privilege and pinned action commits.
- Untrusted pull requests never receive deployment credentials.
- The public-surface gate rejects local paths, common credential formats, production-shaped device identifiers, private host labels, archives, executables, firmware, disk images, and oversized files.
- ClamAV scans repository content in CI as a defense-in-depth signal. Antivirus is not proof that a file is safe.
- Gitleaks scans Git history. A passing secret scanner does not replace review.
- Pages deploys only from `main` after the build job passes.

## Supported versions

Only the current `main` branch receives security fixes. Research results identify their own device and build scope; never assume applicability to another model or OS build.

## Safe harbor

Good-faith research on devices and accounts you own or are explicitly authorized to test is welcome when it respects privacy, applicable law, third-party terms, coordinated disclosure, and this repository's safety gates. This policy does not grant authorization over Apple systems, third-party devices, networks, services, or intellectual property.
