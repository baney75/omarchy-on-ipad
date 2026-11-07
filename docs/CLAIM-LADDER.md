# Claim ladder

Every public statement uses the lowest level that the evidence proves.

| State | Meaning | Minimum evidence |
| --- | --- | --- |
| Prepared | Written or staged, not checked | Reviewable artifact and named future check |
| Verified offline | A check that could fail passed without the target hardware | Exact inputs, command/test, output, and hashes |
| Verified physical | A check that could fail passed on identified real hardware | Exact model/build, bounded operation, before/after evidence, and unchanged safety conditions |
| Complete | Every named acceptance check passed in its required environment | Full checklist, reproducible receipts, and maintainer review |

Additional dashboard states:

- **Active:** bounded work is under way; there is no passing result yet.
- **Blocked:** a named prerequisite is missing.

## Claims this repository will not blur

- A source string is not a live interface.
- A compiled artifact is not a boot.
- QEMU execution is not physical iPad execution.
- An app-hosted VM is not native Linux.
- A one-time host-assisted boot is not untethered.
- Persistent files are not persistent execution.
- A userspace crash or disclosure is not kernel code execution.
- Kernel code execution is not automatically boot-chain authority.
- A Linux RAM boot is not an installed Omarchy system.
- One successful boot is not a reliable cold-start path.

If a claim could reasonably be read at a higher level, rewrite it before merging.
