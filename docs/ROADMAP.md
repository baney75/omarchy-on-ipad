# Roadmap

The roadmap is dependency ordered. Dates do not override evidence gates.

## 0. Public research infrastructure

- [x] Sanitized fresh-history repository
- [x] Structured progress and contribution schemas
- [x] Live GitHub Pages dashboard source
- [x] Agent, security, attribution, and governance contracts
- [ ] Public deployment and first external device contribution

## 1. Evidence and safe bench

- [x] Reference model/build and firmware inventory
- [x] Offline Omarchy ARM and J522 integration artifacts
- [x] Read-only public device collector
- [ ] Demonstrated recovery and restore confidence appropriate to later testing

## 2. Native execution entry

- [ ] Exact production-device execution authority
- [ ] Repeatable, nonpersistent controlled execution with safe return
- [ ] Reviewed first-stage handoff contract for a Linux kernel

## 3. Linux in RAM

- [ ] Start a minimal kernel and initramfs on real Apple-silicon iPad hardware
- [ ] Establish a calibrated observation channel
- [ ] Repeat three RAM boots
- [ ] Return normally to iPadOS after each run

## 4. Hardware bring-up

- [ ] Device tree and interrupt/resource map
- [ ] Internal display
- [ ] Touch
- [ ] Apple Pencil input and charging
- [ ] USB
- [ ] Safe storage access
- [ ] Power/thermal management
- [ ] Networking

## 5. Omarchy integration

- [x] Verified upstream ARM userspace source
- [x] Offline J522 platform delta
- [ ] Full package ownership and lifecycle review
- [ ] Boot and run the real userspace on hardware
- [ ] Update and rollback verification

## 6. Untethered installed system

- [ ] Recovery and storage safety accepted
- [ ] Installation transaction and rollback accepted
- [ ] Ordinary power-button startup without another computer
- [ ] Ten consecutive cold boots
- [ ] Full display, touch, Pencil, storage, network, power, update, rollback, and recovery acceptance
