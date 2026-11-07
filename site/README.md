# site/

The static GitHub Pages dashboard: a template, partials, one stylesheet, one small script, and original SVG marks. Nothing here loads from the network. The Python builder (owned outside `site/`) fills the placeholders from `data/progress.json` and `data/contributions/*.json`.

## Layout

```
site/
  templates/index.html          page shell
  templates/partials/*.html     one fragment per repeated item
  assets/site.css               all styles; tokens at the top
  assets/site.js                optional; adds "(3 hours ago)" after <time data-relative>
  assets/mark.svg               mark, chartreuse
  assets/mark-mono.svg          mark, currentColor (one-color use)
  assets/wordmark.svg           mark + name, for READMEs and social cards
  assets/favicon.svg            mark on the dark canvas
```

Publish `index.html` at the output root and copy `assets/` beside it. The page references `assets/...` relatively.

## Placeholder rules

- `{{NAME}}` takes plain text. The builder must HTML-escape it (`html.escape(value, quote=True)`). These also appear inside attributes.
- `{{{NAME}}}` takes HTML the builder has already rendered from partials. It is inserted raw.
- Names are `UPPER_SNAKE`. Fail the build if any `{{` survives, so a missing value never ships.

```python
import html, re
def fill(tpl, ctx):
    tpl = re.sub(r"\{\{\{([A-Z0-9_]+)\}\}\}", lambda m: str(ctx[m[1]]), tpl)
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", lambda m: html.escape(str(ctx[m[1]]), quote=True), tpl)
```

### index.html

| Placeholder | Source |
| --- | --- |
| `PROJECT_NAME`, `PROJECT_TAGLINE` | `project.name`, `project.tagline` |
| `GOAL_SUMMARY`, `CURRENT_TRUTH` | `goal.summary`, `goal.current_truth` |
| `REFERENCE_TARGET`, `REFERENCE_BUILD` | `goal.reference_target`, `goal.reference_build` |
| `CHECKS_PASSED`, `CHECKS_TOTAL` | sum of `milestones[].passed` and `milestones[].total`. Never a hand-set percentage. |
| `MILESTONES_COMPLETE`, `MILESTONES_TOTAL` | count of milestones with `state == "complete"`; count of milestones |
| `COUNT_PHYSICAL_LINUX_BOOTS`, `COUNT_UNTETHERED_COLD_BOOTS`, `COUNT_INSTALLED_SYSTEMS`, `COUNT_CONTRIBUTOR_DEVICES` | `counts.*` |
| `UPDATED_AT` / `UPDATED_AT_LABEL` | `project.updated_at` as ISO 8601 / human label, e.g. `7 Nov 2026, 19:00 UTC` |
| `GENERATED_AT` / `GENERATED_AT_LABEL` | build time, same two forms |
| `COMMIT_SHORT`, `COMMIT_URL` | short SHA of the built commit and its URL |
| `REPO_URL`, `LIVE_WORK_URL`, `CONTRIBUTE_URL`, `SECURITY_URL` | repository, live work view (issues, project board, or `#work`), contribution guide, security policy |
| `SITE_URL`, `SOCIAL_IMAGE_URL` | canonical Pages URL and its absolute social-card image URL |
| `{{{MILESTONE_ITEMS}}}` | `milestone.html` per milestone, in path order |
| `{{{LEDGER_VERIFIED_ITEMS}}}` | `ledger-item.html` per verified fact (e.g. updates in a `verified_*` state) |
| `{{{LEDGER_HYPOTHESIS_ITEMS}}}` | `ledger-item.html` per open, unproven idea |
| `{{{LEDGER_BLOCKED_ITEMS}}}` | `ledger-item.html` per blocked milestone or workstream |
| `{{{WORKSTREAM_ITEMS}}}` | `workstream.html` per workstream |
| `{{{UPDATE_ITEMS}}}` | `update.html` per update, newest first |
| `{{{COVERAGE_ROWS}}}` | `coverage-row.html` per coverage entry |
| `{{{REQUEST_ITEMS}}}` | `request.html` per safe contribution request |

When a list is empty, render `empty.html` (an `<li>`) with a plain sentence such as "No hypotheses recorded yet." In the coverage table use `empty-row.html`.

### Partials

| Partial | Placeholders |
| --- | --- |
| `state-badge.html` | `STATE`, `STATE_LABEL` |
| `milestone.html` | `ID`, `NAME`, `STATE`, `{{{STATE_BADGE}}}`, `SUMMARY`, `PASSED`, `TOTAL`, `{{{CHECK_PIPS}}}`, `EVIDENCE_AT`, `EVIDENCE_AT_LABEL` |
| `pip.html` | `PIP_STATE`: `pass` for each passed check, `open` for each remaining one. Render `TOTAL` pips. |
| `workstream.html` | `ID`, `NAME`, `{{{STATE_BADGE}}}`, `NEEDS`, `SKILLS` (joined with ` · `) |
| `update.html` | `DATE`, `DATE_LABEL`, `{{{STATE_BADGE}}}`, `TITLE`, `SUMMARY` |
| `ledger-item.html` | `TEXT`, `SOURCE` (state and date, or the milestone it belongs to) |
| `coverage-row.html` | `FAMILY`, `MODELS`, `BUILDS` (comma-joined), `CONTRIBUTORS`, `LEVEL` |
| `request.html` | `ID`, `TITLE`, `DETAIL`, `SAFETY` (e.g. "Read-only collection"), `WORKSTREAM_ID`, `WORKSTREAM_NAME` |
| `empty.html`, `empty-row.html` | `TEXT` |

`EVIDENCE_AT` is the timestamp of the newest evidence behind that milestone's checks. If the data has none per milestone, use `project.updated_at` and keep the label honest.

### State values

`STATE` must be one of these. The class `state--<value>` sets the color and the glyph, and the label is always printed, so color is never the only cue.

| `STATE` | `STATE_LABEL` | Color | Glyph |
| --- | --- | --- | --- |
| `blocked` | Blocked | coral `--risk` | cross |
| `active` | Active | periwinkle `--link` | ring |
| `prepared` | Prepared | amber `--prepared` | open square |
| `verified_offline` | Verified offline | chartreuse `--signal` | open diamond |
| `verified_physical` | Verified physical | chartreuse `--signal` | solid diamond |
| `complete` | Complete | chartreuse `--signal` | solid disc |

## Visual tokens

All in `:root` at the top of `site.css`.

- **Canvas:** `--bg #0f1113`, `--surface #15181b` (current-truth panel only), rules `--rule #24282d` and `--rule-strong #343a41`.
- **Text:** `--text #f3eee4` warm ivory (16.4:1), `--text-muted #b3ada2` (8.5:1), `--text-faint #8f8a81` (5.5:1, metadata only). All pass WCAG AA on `--bg`.
- **Signals:** `--signal #c8f03c` live/verified, `--link #a3adff` links and active research, `--prepared #f0b44c`, `--risk #ff8a76` for blocked work only. Healthy progress (bars, pips) is ivory, not a signal color.
- **Type:** system sans for everything, system mono for identifiers and dates. Scale `--step--1` 14px to `--step-5` 52px at about 1.25 per step. Body is 17px at a 1.55 line height.
- **Space:** 4px base: `--s-1` 4 through `--s-9` 96.
- **Shape:** three radii: `--r-sm` 4px, `--r-md` 8px, `--r-pill`.
- **Breakpoints:** 420, 560, 720 and 960px. The layout is designed at 390px first.

## Mark

A rounded window frame with a gap in its lower edge. A boot path rises through the gap and turns toward a horizon that stops short of the frame: the entry path is still open. It is drawn on a 24px grid with 2px strokes and works in one color (`mark-mono.svg` uses `currentColor`). It is original. Do not swap in Apple or Omarchy marks.

## Accessibility and behavior

- Skip link, landmark regions, one `h1`, ordered headings, and a labeled `<progress>` for overall checks.
- `:focus-visible` outline on every control; tap targets are 44px tall in nav and actions and at least 24px elsewhere.
- No motion besides smooth anchor scrolling, which `prefers-reduced-motion` turns off. `prefers-contrast: more` and `forced-colors` are handled.
- The page is complete without JavaScript. `site.js` only appends relative ages.
- No fonts, images, scripts or styles from other hosts; no cookies or analytics.

## Checks run on this design

Rendered from the current `progress.json` with a throwaway filler and checked with the web-design-bar `design_check.js` at 390px and 1280px: no flags (contrast, line length, line height, 4px grid, radii, nested cards, tap targets, horizontal overflow). At 390×844 the label, goal, current truth, derived progress and both actions sit above the fold.
