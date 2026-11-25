---
name: Portal Data Formasi CPNS 2024
description: Dual-theme analytical workspace and open-data ledger for exploring 111,921 Indonesian SSCASN formations and PP No. 5 Tahun 2024 slips.
colors:
  sky-action: "#0369a1"
  sky-action-hover: "#0284c7"
  sky-ink-dark: "#38bdf8"
  obsidian-canvas: "#0b0f17"
  obsidian-recessed: "#080b11"
  slate-surface: "#111722"
  slate-elevated: "#171f2e"
  hairline-subtle: "#1f293b"
  hairline-strong: "#2d3b54"
  ink-primary: "#f1f5f9"
  ink-secondary: "#cbd5e1"
  ink-muted: "#94a3b8"
  ink-placeholder: "#8b9bb4"
  light-canvas: "#f4f7fb"
  light-recessed: "#edf2f7"
  light-surface: "#ffffff"
  light-hairline: "#dbe3ee"
  light-ink-primary: "#0f172a"
  light-ink-muted: "#475569"
  status-loose-dark: "#34d399"
  status-loose-light: "#047857"
  status-mod-dark: "#fbbf24"
  status-mod-light: "#92400e"
  status-tight-dark: "#fb7185"
  status-tight-light: "#be123c"
typography:
  display:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: 1.18
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.3
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.35
    fontFeature: "tnum"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.sky-action}"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.md}"
    padding: "6px 11px"
  button-primary-hover:
    backgroundColor: "{colors.sky-action-hover}"
  button-secondary:
    backgroundColor: "{colors.slate-surface}"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    padding: "6px 11px"
  button-support-pill:
    backgroundColor: "{colors.slate-elevated}"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
  input-control:
    backgroundColor: "{colors.obsidian-recessed}"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.md}"
    padding: "6px 10px"
  panel-workbench:
    backgroundColor: "{colors.slate-surface}"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.lg}"
    padding: "12px 16px"
---

# Design System: Portal Data Formasi CPNS 2024

## Overview

**Creative North Star: "The Dual-Light Analytical Ledger"**

Portal Data Formasi CPNS 2024 (`frontend/index.html`, `frontend/sumber-data.html`, `frontend/css/app.css`, `frontend/js/app.js`) is a high-density workspace for comparing 111,921 civil-service formations, applicant counts (`jumlah_ms`), and PP No. 5 Tahun 2024 slips. It defaults to Nocturnal Obsidian-Slate and switches without flash (`data-theme="light"` via `localStorage`) into Daylight Slate-Alabaster, keeping search and top rows in the first viewport while styling `Support Me` with harmonious sky-tinted washes.

**Key Characteristics:**
- Zero-FOUC Dark/Light tokens holding WCAG AA (`>= 4.5:1`) contrast across all surfaces, placeholders, and badges.
- Single sky-cyan interactive/spotlight accent paired with three semantic data-only statuses.
- Self-hosted `Figtree` UI type paired with `JetBrains Mono` (`tabular-nums`) for figures, ratios, Rupiah, and IDs.
- Single-layer containers divided by `1px` hairlines—never nested cards.

## Colors

- **Sky Action & Ink** (`{colors.sky-action}`, `{colors.sky-action-hover}`, `{colors.sky-ink-dark}`): Primary fills across both modes and dark-mode interactive ink.
- **Dark Stack** (`{colors.obsidian-canvas}`, `{colors.obsidian-recessed}`, `{colors.slate-surface}`, `{colors.slate-elevated}`): Paired with `{colors.hairline-subtle}` / `{colors.hairline-strong}` borders and `{colors.ink-primary}`–`{colors.ink-placeholder}`.
- **Light Stack** (`{colors.light-canvas}`, `{colors.light-recessed}`, `{colors.light-surface}`): Paired with `{colors.light-hairline}` and `{colors.light-ink-primary}` / `{colors.light-ink-muted}`.

### Named Rules
**The One Interactive Voice Rule.** Interactive controls, active chips, and `Support Me` stay within the Sky-Slate family (`<= 10%` chromatic area) so neither mode clashes.

**The Semantic Data-Only Rule.** Emerald (`{colors.status-loose-dark}` / `{colors.status-loose-light}`), Amber (`{colors.status-mod-dark}` / `{colors.status-mod-light}`), and Rose (`{colors.status-tight-dark}` / `{colors.status-tight-light}`) encode data states only: `0 Pelamar`/loose, moderate/indicative Tukin, and tight/deductions.

## Typography

**Display & Body:** Figtree (WOFF2) · **Mono:** JetBrains Mono (WOFF2, `tabular-nums`)
- **Scale:** Display `clamp(1.5rem, 2.6vw, 2rem)`, H1 `1.4375rem–1.625rem`, H2 `1.125rem–1.25rem`, H3 `1rem` (`>= 1.25x` steps), Body `0.875rem` (`54ch–58ch`), Label `0.75rem` floor.

**The Data-Only Monospace Rule.** Reserve `JetBrains Mono` for counts, currency, formulas, UUIDs, and SQL fields; keep `.major-tag` in `Figtree`.

**The 12px Functional Floor Rule.** UI labels, badges, and headers stay `>= 12px`; `<p>` stays `>= 14px`.

## Layout, Elevation & Shapes

`frontend/index.html` (`1640px` max) fits header, dataset strip, workbench, and top rows in the first viewport (`1440x900` & `390x844`); `frontend/sumber-data.html` (`1180px` max) uses hairline-split columns. Radii: panels `12px–14px`, controls `8px`, tags `4px`, `.btn-support-pill` `9999px`. Shadows: Popover `0 12px 28px -6px rgba(3, 7, 15, 0.78)` and Dialog `0 24px 56px -12px rgba(2, 5, 12, 0.86)`.

**The Single-Layer Container Rule.** Subdivide panels with `1px` hairlines; never nest bordered cards.

## Components

- **Buttons & Theme Toggle:** Solid `{colors.sky-action}` buttons, sky-washed `.btn-support-pill`, and `.btn-theme-toggle` (`cpns2024_theme`).
- **Inputs & Selects:** `--color-input-bg` fields (`16px` mobile floor) with custom SVG select chevrons.
- **Support Spotlight & Modals:** `.support-spotlight` pairs a `#ffffff` QRIS mount (`ID1025421073475` copy) with a `#0f172a` badge behind white-fill `tako_logo.svg` and Tako.id CTA; `.modal-dialog` (`max-height: calc(100dvh - 24px)`) runs the THP simulator.

## Do's and Don'ts

### Do:
- **Do** hold `>= 4.5:1` contrast in both `data-theme="dark"` and `data-theme="light"`, keeping `#0f172a` badges behind white-fill SVGs like `tako_logo.svg`.
- **Do** right-align `.col-num` with `JetBrains Mono` `tabular-nums` and non-breaking `Rp\u00A0` / `\u00A0Jt`.
- **Do** keep `Support Me` catchy via pill silhouette and sky-tinted spotlight washes rather than clashing hues.

### Don't:
- **Don't** use emerald outside `0 Pelamar` or `Sangat Longgar` competition states.
- **Don't** use emoji glyphs, blinking dots, shimmer sweeps, gradient text, eyebrow kickers, or nested cards.
