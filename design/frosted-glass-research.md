# Frosted glass — research (7 Nov 2026)

How frosted glass is actually done, researched before rebuilding the desk's
glass. Sources: [Liquid glass CSS, dev.to](https://dev.to/vitalbadjo/liquid-glass-css-the-apple-liquid-glass-effect-with-css-only-plus-svg-refraction-1hkd)
(Apple Liquid Glass, 2025), [Microsoft Learn — Acrylic material](https://docs.microsoft.com/en-us/windows/apps/design/style/acrylic?wt.md_id=MVP_266673),
Apple HIG materials, and the liquid-glass skill repos (axot, TurtIeSocks, iMxSquash).

## The finding: glass is a stack of layers, not one `backdrop-filter`

> "Glass is a stack of optical layers, not one `backdrop-filter`. The most
> common failure is doing only layer 1 (blur) and wondering why it looks
> flat and cheap." — liquid-glass-css skill

That was exactly our failure: blur + tint only. The five layers:

| # | Layer | What it does | CSS |
|---|-------|--------------|-----|
| 1 | **Tint** | Faint wash so the pane reads as a material, not a hole | `background: rgba(255,255,255,.1)` dark / higher alpha light |
| 2 | **Blur + saturation** | Frosts what's behind; saturation pumps the colours back (blurring drains saturation — `saturate(180%)` is the trick that separates Apple-grade from amateur) | `backdrop-filter: blur(8–20px) saturate(180%) brightness(1.06–1.1)` |
| 3 | **Specular rim** | Thin bright edge, strongest at the top — light entering the pane. Asymmetric on purpose: top ~2× the sides, or it flattens into an outlined box | inset `box-shadow` highlights + 1px border |
| 4 | **Sheen** | Soft diagonal gloss, surface looks lit not matte | `::after` white luminance gradient, `mix-blend-mode: screen` (dark) / `normal` (light) |
| 5 | **Refraction** | The backdrop actually *bends* | `backdrop-filter: url(#filter)` with `feDisplacementMap` |

Plus **lift** (soft drop shadow, `0 8px 32px rgba(0,0,0,0.25)`) and **noise**
(2–6% grain — Fluent Acrylic bakes it in; we already have the film grain).

## The numbers

- **Blur:** premium range 12–24px for frost; Liquid Glass wants a *small*
  blur (4–10px) in the refraction chain — the saturation does the work.
  We use **12px** with the lens, 20px fallback without it.
- **Saturate:** 150–190% (we use 180%).
- **Brightness:** 1.06–1.1 in the chain.
- **Rim (dark):** border `rgba(255,255,255,0.18)`; inset top `0.55`,
  bottom `0.30`, sides `0.20`. **Light:** border `rgba(255,255,255,0.65)`;
  top `0.90` white, bottom `rgba(0,0,0,0.06)` dark; more blur (12–16px)
  and higher tint alpha (0.4–0.6) because light backgrounds have less
  contrast to frost.
- **Refraction filter** (verbatim from the dev.to guide):
  `feTurbulence type="fractalNoise" baseFrequency="0.008 0.012"
  numOctaves="2" seed="9"` → `feGaussianBlur stdDeviation="1.4"` →
  `feDisplacementMap scale="60" xChannelSelector="R" yChannelSelector="G"`,
  filter region widened to `-20% / 140%` (displacement pulls pixels in
  from outside the element; the default region clips to hard lines).
  Tuning: baseFrequency 0.005–0.015 (large slow waves; 0.05+ reads as
  frosted texture, not liquid), scale 20–50 per the guide — we run 60,
  top of the usable range, because the canopy backdrop is soft and a
  mid-range warp barely reads on it in a still (verified by A/B:
  lens on vs lens off at identical blur). 80+ tears the backdrop.
- **Support:** `url(#svg-filter)` inside `backdrop-filter` works in
  **Chromium only**. Safari drops the declaration; Firefox is unreliable.
  Gate behind `@supports (backdrop-filter: url('#id'))` — and never put
  the url in an unguarded declaration, or Safari loses the blur too.
- **Background matters:** "Refraction is invisible against flat color."
  Over a photo / vivid backdrop it shows; over a flat fill it vanishes.
  (Our canopy is the vivid backdrop — this is why the refraction reads.)
- **Accessibility:** `prefers-reduced-transparency: reduce` → opaque
  panels (92%), no backdrop-filter. Contrast must hold against the
  *worst* part of the backdrop, not the average — hence the tint floor.
- **Performance:** `backdrop-filter` re-composites the backdrop every
  frame something behind it moves. SVG displacement is the expensive
  layer — keep displaced elements few and `numOctaves` at 1–2, never
  animate the noise. Blur radius is the cost knob.

## What we adopted / skipped

- **Adopted:** all five layers on the big glass surfaces
  (`.pane`, `.sidenav`, `.beats-outcome`, `.desk-stats`); plain frost
  (blur + tint, no lens) on buttons, topbar, disclaimer and chat, to keep
  the displaced-surface count low.
- **Skipped — chromatic dispersion rim** (rainbow fringe at the edge):
  it is a hue gradient, banned by the desk's taste rules.
- **Skipped — SDF edge-lens map** (hand-made displacement map, grey
  centre, bend ramping to the edges — Apple's real lens): a heavier
  build needing a per-element canvas-generated map. The turbulence
  version is the verified simple one; revisit if the wobble reads wrong.
- **Skipped — mask-image edge fade** (blur fading out at the pane
  edges): pretty on floating pills, risky for text at the edges.
- **Sheen kept subtle** (0.16 dark / 0.35 light at the corner) — it is a
  white *luminance* gradient, not a hue gradient, so it stays inside the
  taste rules.
