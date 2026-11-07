# platform/

Public source for the `driver-kernel` lane in [AGENTS.md](../AGENTS.md#contribution-lanes): Linux kernel patches, device-tree source, and packaging recipes for Apple-silicon iPad targets. Nothing has landed here yet.

## What belongs here

- Patches, device-tree source (`.dts`, `.dtsi`), Kconfig fragments, and packaging recipes as plain text.
- Each change names its exact target (model, board, build), its upstream base (project, commit, license), and its provenance. Credit upstream work in [CREDITS.md](../CREDITS.md).
- Ordinary, safe driver and packaging code is welcome. The public-lane limits below are about device actions and payloads, not about writing code.

## What does not

- Firmware, compiled kernels or modules, disk images, archives, or any binary. The public-surface gate rejects them.
- Exploit code, payloads, loaders that bypass platform security, or anything that writes to a device.
- Physical test instructions. Testing on hardware is private and follows [SECURITY.md](../SECURITY.md).

## Verification

Record the offline checks you ran: compile with a pinned toolchain, static analysis, and unit tests, with exact commands, versions, and results. State their limits. A compile, a cross-compile, or an emulator run is **verified offline** at most; it is never physical verification and never a native iPad boot (see the [claim ladder](../docs/CLAIM-LADDER.md)).

Choose a model that passed a representative task in this code. If the work reasons about boot entry, loaders, or the boot chain, run the research model preflight in [the research playbook](../docs/RESEARCH-PLAYBOOK.md) first.
