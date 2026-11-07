# Omarchy on iPad — dashboard design brief

## Purpose

Build the public front door for an open, evidence-driven effort to run Omarchy natively on Apple-silicon iPads. The site must show the real state at a glance, help qualified contributors pick useful work, and never imply that Linux has booted or Omarchy is installed before evidence exists.

## Audience

- iPad owners with a Mac who can safely collect device-specific evidence;
- Linux, Asahi, boot-chain, kernel, display, touch, power, networking, and Arch/Omarchy contributors;
- security researchers who can evaluate entry paths through coordinated disclosure;
- curious supporters who need an honest, plain-English progress view.

## Brand character

Precise, ambitious, open, calm. It should feel like a serious hardware bring-up lab rather than a jailbreak download page, product launch, Apple imitation, or cyberpunk exploit site.

## Required first-screen content

1. Unofficial/community-research label.
2. Clear goal: native, untethered Omarchy on Apple-silicon iPad hardware.
3. Current truth: no native Linux boot and no installed Omarchy yet.
4. Overall progress derived from milestone checks, not a made-up percentage.
5. Primary actions: “See the live work” and “Contribute a device result.”

## Dashboard requirements

- Render from `data/progress.json` and `data/contributions/*.json` through a zero-dependency Python builder.
- Show milestone states: blocked, active, prepared, verified offline, verified physical, complete.
- Show exact pass counts and evidence timestamps.
- Show active workstreams, blockers, recent verified updates, device/build coverage, and safe contribution requests.
- Clearly distinguish verified facts, hypotheses, and blocked work.
- Responsive at 390 px and 1280 px; accessible keyboard navigation, visible focus, reduced-motion support, and WCAG AA body-text contrast.
- No external fonts, analytics, trackers, cookies, client framework, remote images, or runtime secrets.
- Progressive enhancement only. Core state must be readable without JavaScript.

## Visual direction

Use a dark technical canvas with warm ivory text, electric chartreuse as the “live/verified” signal, cool periwinkle for links and active research, amber for prepared work, and coral only for blocked/risk states. Use crisp editorial typography, generous whitespace, subtle grid lines, and restrained rounded geometry. Avoid Apple logos, iPad silhouettes that copy Apple advertising, Omarchy’s existing mark, terminal clichés, skulls, locks, neon hacker imagery, glassmorphism, and fake telemetry.

The mark should be original and simple: a rounded tablet/window frame intersected by a rising horizon or boot-path line, with an open gap to represent the unresolved entry path. It must work in one color and at 24 px.

## Implementation ownership

The design agent owns only `site/` (templates, CSS, small local assets, and client-side progressive enhancement). The primary agent owns data schemas, the Python build, CI, documentation, security policy, and publication. Do not edit outside `site/`. Other work may land concurrently; do not revert it.

## Done check

`site/` contains a polished semantic HTML template, one self-contained CSS file, optional small progressive-enhancement JavaScript, and original SVG logo assets. It uses explicit placeholders that a Python builder can replace from repository data. No dependencies or network calls.

