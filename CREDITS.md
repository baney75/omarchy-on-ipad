# Credits and upstream work

This project is possible because other communities published software, documentation, hardware research, and working precedents. Credit does not imply endorsement.

## Core upstreams

| Project | What this effort learns or uses | License / status |
| --- | --- | --- |
| [Omarchy](https://github.com/omacom/omarchy) | The target desktop system and ARM userspace | MIT; `OMARCHY` is a 37signals LLC trademark |
| [Omarchy ISO](https://github.com/omacom/omarchy-iso) | Official ARM image construction and verification flow | See upstream repository |
| [Asahi Linux](https://asahilinux.org/) | Apple-silicon Linux architecture, documentation, and supported-Mac precedent | Multiple upstream licenses |
| [m1n1](https://github.com/AsahiLinux/m1n1) | Apple-silicon bootloader and hardware experimentation framework | GPL-2.0 |
| [Asahi Linux kernel](https://github.com/AsahiLinux/linux) | Apple-silicon kernel drivers and device-tree precedent | Linux kernel licenses |
| [Linux](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/) | Kernel and Apple T8103 device-tree foundations | GPL-2.0 with Linux syscall note |

## Device and tablet precedents

| Project | Contribution to the public map | License / status |
| --- | --- | --- |
| [Orchard Linux](https://github.com/OrchardLinux/orchard) | Experimental Linux work on older Apple mobile devices | See upstream repository |
| [Omarchy A](https://github.com/OrchardLinux/omarchy-a) | Tablet-oriented Omarchy experiment for A-series devices | See upstream repository; not M1 iPad proof |
| [Hoolock Linux](https://github.com/HoolockLinux) | Older-device Linux bring-up and touch documentation | See individual upstream repositories |
| [Project Sandcastle](https://projectsandcastle.org/) | Native Linux/Android precedent on supported older Apple hardware | See upstream project |

## Platform documentation

- [Apple Platform Security](https://support.apple.com/guide/security/welcome/web) documents the public iPad boot and runtime security model.
- [Apple developer documentation](https://developer.apple.com/documentation/) defines public development and device-management interfaces.
- [Arch Linux](https://archlinux.org/) provides the upstream distribution foundation used by Omarchy.

## This repository

- Donovan Baney initiated and maintains the effort, owns the reference device, and is accountable for published project claims.
- The public dashboard identity and mark are original work commissioned for this repository. They intentionally do not copy Apple or Omarchy marks.
- Contributors are credited through Git history, contribution records, releases, and research notes when they request public credit.

## Reuse policy

No Apple firmware, decrypted system binary, signing asset, third-party logo, or upstream source tree is redistributed here. Citations and exact hashes identify locally reviewed artifacts without transferring their copyright. If you find an attribution or license error, open an issue without attaching the disputed material.
