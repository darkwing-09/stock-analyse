---
name: Stock Analyse dashboard
description: A quant desk at night. Near-black ground, hairline edges, one cool accent that behaves like light (spotlight beams, a glow that follows the pointer, a point travelling around the live chip). Data in tabular Geist; nothing decorative that is not light or data.

colors:
  ground: "#080808"            # page
  surface: "#0f0f0f"           # panels
  surface-2: "#141414"         # nested rows, hover fills
  surface-3: "#1a1a1a"
  line: "rgba(255,255,255,0.08)"        # default hairline
  line-strong: "rgba(255,255,255,0.14)" # tooltips, switches
  fg: "#ededed"                # headings, values (17:1)
  fg-2: "#a1a1aa"              # body, secondary (7.8:1)
  fg-3: "#8b8b8b"              # labels, meta (5.9:1)
  accent: "#3b82f6"            # focus, selection, active, glow source
  accent-soft: "#60a5fa"       # small accent text (7.9:1)
  accent-pale: "#93c5fd"       # highlight on the glow ring
  series-strategy: "#3b82f6"   # validated pair on #080808 with series-nifty
  series-nifty: "#d95926"
  series-aqua: "#199e70"       # third categorical slot (exit reasons)
  series-yellow: "#c98500"     # fourth slot, rarely shown
  good: "#0ca30c"              # icons and dots only
  bad: "#d03b3b"               # icons and dots only (4.17:1, never as text)

typography:
  family: Geist Variable (one family); Geist Mono only for shell commands
  numerals: tabular-nums everywhere data appears (.num)
  scale: 12 label · 13 meta · 14 table/body-compact · 15 body · 20 h2 · 24 stat · 32 h1 · 36–40 headline number
  tracking: -0.02em on headings and the headline number; 0.01em on 12px labels

motion:
  arrive: 0.5s cubic-bezier(0.16,1,0.3,1), rise 12px out of a 6px blur, sections staggered 60–80ms (settles < 450ms)
  title: words resolve out of a blur, 60ms apart
  layout: one spring (stiffness 520, damping 42) for every sliding pill
  feedback: 150–300ms; hover never moves the hovered element
  ambient: spotlight beams drift 9s each way; the live chip's light orbits in 4.5s
  reduced-motion: beams static, no blur or stagger, pills jump, charts draw instantly
---

# Stock Analyse dashboard

## World

The surface is a dark desk; light is the only ornament. Three things carry it:

1. **Spotlight beams** behind the header (two cool radial sweeps, hue 210, opacity ≤ 0.08) over a chart-paper dot grid that fades out before the first panel.
2. **Glow cards.** Every panel is `#0f0f0f` with a 1px `white/8` edge. When the pointer is inside, a 520px radial wash (accent at 9%) follows it and a 90° conic highlight lights the edge at the pointer's bearing from the card centre.
3. **The live chip.** The market regime pill has a point of light orbiting its edge; the dot and label carry the status, the light only says "live".

Everything else is restraint: no gradient text, no coloured side stripes, no glass except the sticky nav over scrolling content.

## Rules

- Accent is for focus, the active tab or chip, the suggested-portfolio tick, the score bar and the strategy series. It is never a background.
- Gains and losses are shown by an arrow icon in `good` / `bad` next to a number in `fg`. Red and green never colour text.
- Charts: strategy solid 2px blue with a 3px halo; Nifty 1.5px dashed orange; grid `white/6`; axes `#8b8b8b` 11px; tooltip `#0c0c0c/95` with a strong hairline.
- Tables: 12px muted headers, 14px rows, `white/5` row rules, radial blue spotlight under the pointer, rows stagger in 30ms apart (capped at 12).
- Controls are standard: buttons, radio chips, a switch, sortable headers. Pills slide with the shared spring.
- Every section has loading (shimmer skeleton), empty (title, one sentence, the exact command with a copy button) and unreachable-server states.
- Panels: radius 16px, padding 20px (24px on the hero panel). Nested elements use radius 12px and `white/5` rings, never a second panel.
- Mobile: tabs become a full-width pill group under the bar; the bento collapses to one column; tables scroll horizontally.
