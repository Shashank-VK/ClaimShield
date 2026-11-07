# 60-30-10 colour rule — research (7 Nov 2026)

Borrowed from interior design, applied to UI. Sources: UXPin (2026 UI
palette guide), Orbix (palette types), colorpalettefinder, Mockitt,
uiguides, Splunk dashboard colour discipline, ui-color-system skill.

## The rule

A composition heuristic, not a measurement: roughly 60% dominant, 30%
secondary, 10% accent. "It says almost nothing about hue and almost
everything about proportion." Aim for the feel — two-thirds, one-third,
a sliver — not pixel-perfect percentages. If three colours appear in
equal amounts the eye doesn't know where to look ("if everything is
shouting, nothing is heard").

| Share | Role | Where it goes | Typical choice |
|-------|------|---------------|----------------|
| **60%** | Dominant | Page background, large surfaces, empty space. Sets the mood; usually the colour people *don't* notice | A neutral — off-white / light grey, or in dark mode a near-black like `#0F1115` / `#121212`–`#1E1E1E`. Never pure black (harsh, tiring) |
| **30%** | Secondary | Cards, sidebars, nav bars, supporting surfaces. Structure + a second layer of contrast, never demands attention | Often a muted tint of the brand colour, or a mid-tone / complementary neutral |
| **10%** | Accent | Primary buttons, links, active states, key highlights only. The throw pillow — small on purpose, that is what makes it pop (Von Restorff / isolation effect) | The brand colour at full strength |

## The details that matter

- **Separation:** a **10–15% lightness difference in HSL** between dominant
  and secondary creates clean separation without tension (Orbix). Below
  that the layers melt into each other; above it they start competing.
- **Accent discipline:** "If the user sees this colour, it MUST be
  clickable." Using the accent for non-interactive decoration is a UX
  failure. Accent carries CTAs, links and active states — nothing else.
- **Dark mode:** proportions stay, only the dominant changes to a dark
  neutral. Bright accents need slight desaturation (20–30%) or they glow.
  Use lightness for elevation, not shadows. Borders need to be brighter
  than you think in dark mode.
- **Neutrals are exempt:** black/white text sits outside the count (they
  aren't colours). 70–80% of an interface is grey — grey is what makes
  colour shine.
- **Semantic colours sit outside the ratio:** status colours (red/green/
  amber) are data ink, not decoration — their own small budget, never
  bleeding into the interface palette (Splunk: 60% canvas/chrome,
  30% data ink, 10% accent/status).
- **The ratio doesn't guarantee contrast:** WCAG AA still applies
  (4.5:1 normal text, 3:1 large). A harmonious palette can still be
  unreadable.

## Audit of the desk (before the fix)

| Role | Desk mapping | Verdict |
|------|-------------|---------|
| 60% dominant | Canvas `#0B0E13` (near-black, cool-tinted, not pure black) + moonlit canopy as the visible field | ✓ Correct |
| 30% secondary | Glass panels `rgba(17,21,28,0.3)` — dark navy tint | ✗ **Too close to the dominant.** `#0B0E13` is ~6% lightness; the panel tint `#11151C` is ~8% — a ~2% gap, far under the 10–15% separation. Where the canopy is dark the panels melt into the canvas; the separation came only from the canopy showing through, not from the colour itself |
| 10% accent | Action Blue `#2997ff` / `#0071e3` on the primary Beat 4 button, logo check, stat numbers, proof links | ✓ Mostly correct — all interactive/emphasis, small area. **Gap:** the active nav state was neutral white, but the rule puts active states in the accent |

## What changed

- **Secondary tint lifted to a muted tint of the brand blue** (the
  research's preferred secondary): dark `--panel` tint `#11151C` →
  `#232B38` (~18% lightness, an ~12% lift over the canvas — inside the
  10–15% band), `--panel-raised` `#171C24` → `#2A3342`, `--chrome`
  (topbar/disclaimer) and `--glass-strong` lifted to the same slate
  family. Opacities unchanged (30%/38%/80%/92%) — the glass, refraction
  and readability work is untouched; only the tint moved.
- **Accent now carries the active nav state:** `--nav-active` neutral
  white 0.10 → blue tint `rgba(41,151,255,0.14)` dark /
  `rgba(0,113,227,0.10)` light. Text stays ink for contrast; the pill
  itself is the accent.
- **Light theme:** secondary (white panels on `#F5F5F7`) and accent
  (`#0071E3`) already follow the standard pattern — separation there
  comes from the rim + lift shadow, not the fill. Only the active-nav
  tint changed.
- **Semantic colours untouched:** approve `#30d158`, veto `#ff453a`,
  blocked `#ffd60a` stay verdict-only, outside the 60-30-10 budget.
