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

<!-- impeccable:design-map -->
Name: Portal Data Formasi CPNS 2024
Colors: primary: sky-action #0369a1; neutral: obsidian-canvas #0b0f17; semantic: status-loose-dark #34d399; primary: sky-action-hover #0284c7; primary: sky-ink-dark #38bdf8 (+20 more in the sidecar)
Fonts: Figtree (display, headline, title, body, label); JetBrains Mono (mono)
Spacing: xs 4px, sm 8px, md 12px, lg 16px, xl 24px, xxl 32px
Radius: xs 4px, sm 6px, md 8px, lg 12px, pill 9999px
North Star: "The Dual-Light Analytical Ledger"
Rules:
- The One Interactive Voice Rule. Interactive controls, active chips, and `Support Me` stay within the Sky-Slate family (`<= 10%` chromatic area) so neither mode clashes.
- The Semantic Data-Only Rule. Emerald (`{colors.status-loose-dark}` / `{colors.status-loose-light}`), Amber (`{colors.status-mod-dark}` / `{colors.status-mod-light}`), and Rose (`{colors.status-tight-dark}` / `{colors.status-tight-light}`) encode data states only: `0 Pelamar`...
- The Data-Only Monospace Rule. Reserve `JetBrains Mono` for counts, currency, formulas, UUIDs, and SQL fields; keep `.major-tag` in `Figtree`.
- The 12px Functional Floor Rule. UI labels, badges, and headers stay `>= 12px`; `<p>` stays `>= 14px`.
- The Single-Layer Container Rule. Subdivide panels with `1px` hairlines; never nest bordered cards.
Don't:
- Don't use emerald outside `0 Pelamar` or `Sangat Longgar` competition states.
- Don't use emoji glyphs, blinking dots, shimmer sweeps, gradient text, eyebrow kickers, or nested cards.
Do:
- Do hold `>= 4.5:1` contrast in both `data-theme="dark"` and `data-theme="light"`, keeping `#0f172a` badges behind white-fill SVGs like `tako_logo.svg`.
- Do right-align `.col-num` with `JetBrains Mono` `tabular-nums` and non-breaking `Rp\u00A0` / `\u00A0Jt`.
- Do keep `Support Me` catchy via pill silhouette and sky-tinted spotlight washes rather than clashing hues.
Map: frontend/index.html
Map: frontend/sumber-data.html
Map: frontend/css/app.css
Map: frontend/js/app.js
Full: .impeccable/design-full.md (read a section when you need its detail)
