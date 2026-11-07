// Lilac Dusk Canopy — ported to plain JS + hand CSS (this frontend has no
// TypeScript / Tailwind / shadcn). One fragment shader, no textures, no
// assets. Raw WebGL1, React is the only import. The canvas sizes itself from
// its own box, sleeps off-screen, honours reduced motion, and paints a still
// gradient where WebGL is unavailable.
//
// Port notes vs the pasted .tsx:
// - Types stripped; Tailwind layout classes replaced by .canopy-root rules in
//   globals.css (this codebase has no Tailwind utilities).
// - Pointer listeners moved from the section to `window`: as a fixed
//   background the section sits under the desk content, so pointer events on
//   the content would never reach it — window sees them all, and the sun
//   still leans toward the cursor / a click is still a gust.

import React, { useEffect, useMemo, useRef, useState } from "react"

export const CANOPY_DEFAULTS = {
  wallTop: "#c4685f",
  wallBottom: "#cb887b",
  bounce: "#ea8571",
  light: "#ff9d76",
  hot: "#ffb48c",
  sunX: 0.12,
  sunY: 0.12,
  sunWidth: 1.38,
  sunHeight: 0.85,
  sunAngle: 0.5,
  leafAngle: 0.95,
  leafSize: 0.4,
  density: 0.6,
  blur: 0.75,
  shadow: 0.82,
  sway: 1,
  flutter: 1,
  gustiness: 0.5,
  grain: 0.045,
  flicker: 0.35,
  follow: 0.08,
  push: 1,
}

/** Overlays on the defaults, named for the light rather than the numbers. */
export const CANOPY_PRESETS = {
  apricot: {},
  "golden-hour": {
    wallTop: "#a8704a", wallBottom: "#c39468", bounce: "#e09a5c", light: "#ffcf86", hot: "#fff0c2",
    sunX: 0.9, sunY: 0.2, sunAngle: -0.55, leafAngle: -0.75, density: 0.5, blur: 0.65,
  },
  "sage-morning": {
    wallTop: "#7e8c7a", wallBottom: "#a3ad98", bounce: "#c3c7a8", light: "#f4efd6", hot: "#fffbea",
    sunX: 0.75, sunY: 0.85, sunAngle: -0.5, leafAngle: 2.3, shadow: 0.7, grain: 0.035,
  },
  "noon-plaster": {
    wallTop: "#cfc8bd", wallBottom: "#ddd7cd", bounce: "#ebe5da", light: "#fffaf1", hot: "#ffffff",
    sunX: 0.5, sunY: 0.62, sunWidth: 1.4, sunHeight: 0.9, sunAngle: 0.2, leafAngle: 1.1,
    leafSize: 0.24, density: 0.62, blur: 0.5, shadow: 0.72, grain: 0.03, flicker: 0.2,
  },
  "lilac-dusk": {
    wallTop: "#4f4366", wallBottom: "#6e5f86", bounce: "#9a6f92", light: "#f4a8a2", hot: "#ffd2b8",
    sunX: 0.15, sunY: 0.3, sunWidth: 1.0, sunHeight: 0.55, leafSize: 0.36, blur: 0.85, sway: 0.7,
  },
  moonlit: {
    wallTop: "#141a2a", wallBottom: "#222b40", bounce: "#2f3d5c", light: "#9fb6e6", hot: "#dfe8ff",
    sunX: 0.82, sunY: 0.78, sunAngle: -0.4, leafAngle: 2.4, density: 0.6, blur: 0.8,
    shadow: 0.9, sway: 0.6, flutter: 0.7, grain: 0.06, flicker: 0.15,
  },
}

// #region logic
/** "#rgb" / "#rrggbb" → 0..1 triplet; anything else is mid-grey. */
export function hexToRgb(hex) {
  let h = String(hex).trim().replace(/^#/, "")
  if (h.length === 3) h = h.replace(/./g, (c) => c + c)
  if (!/^[0-9a-f]{6}$/i.test(h)) return [0.5, 0.5, 0.5]
  const n = parseInt(h, 16)
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
}

/** Smooth 1D value noise in 0..1. Deterministic for a given t and seed. */
export function noise1(t, seed) {
  const i = Math.floor(t)
  const f = t - i
  const hash = (n) => {
    const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453
    return s - Math.floor(s)
  }
  const u = f * f * (3 - 2 * f)
  return hash(i) * (1 - u) + hash(i + 1) * u
}

/**
 * How hard the wind is blowing at time t, 0..1. Mostly a light breeze, with a
 * gust rolling through now and then; `gustiness` 0 is a steady breeze and 1 is
 * a blustery afternoon. Two octaves, so gusts have a swell and a flutter.
 */
export function gustAt(t, gustiness) {
  const g = Math.min(Math.max(gustiness, 0), 1)
  const n = noise1(t * 0.13, 1.7) * 0.7 + noise1(t * 0.41, 5.3) * 0.3
  const lo = 0.62 - g * 0.32
  const x = Math.min(Math.max((n - lo) / 0.32, 0), 1)
  return 0.25 + 0.75 * x * x * (3 - 2 * x)
}

/**
 * One step of a damped spring toward a target — the whole tree swinging after
 * a push and settling with a little overshoot. Semi-implicit Euler, sub-stepped
 * so a stalled tab cannot integrate one enormous step and fling the canopy.
 */
export function springStep(pos, vel, target, dt, stiffness, damping) {
  const steps = Math.max(1, Math.ceil(dt / (1 / 120)))
  const h = Math.min(dt, 0.25) / steps
  for (let i = 0; i < steps; i++) {
    vel += ((target - pos) * stiffness - vel * damping) * h
    pos += vel * h
  }
  return [pos, vel]
}

/** Frame-rate independent ease toward a target; k is roughly 1 / settle-time. */
export function approach(cur, target, dt, k) {
  return target + (cur - target) * Math.exp(-dt * k)
}

/**
 * The length that spans 1 wall unit: the shorter side, but never less than 62%
 * of the longer one — so a tall phone gets leaves of a sensible size instead
 * of ones scaled to its narrow width. Must match `unit` in the shader.
 */
export function wallUnit(w, h) {
  return Math.max(Math.min(w, h), Math.max(w, h) * 0.62, 1)
}

/** A point 0..1 in the box (y up) → shader wall units, centred on the box. */
export function toWall(u, v, w, h) {
  const m = wallUnit(w, h)
  return [((u - 0.5) * w) / m, ((v - 0.5) * h) / m]
}
// #endregion logic

const VERT = [
  "attribute vec2 a_pos;",
  "void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }",
].join("\n")

/*
 * The light: a soft elliptical sun patch, attenuated by two layers of leaves.
 * Each layer is a stretched cell grid with one leaf per cell, kept or dropped
 * by a slow clump field so the canopy has gaps the light can stream through.
 * Leaves are soft ellipses — the softness *is* the blur, and the far layer is
 * softer and slower, which is what reads as depth.
 */
const FRAG = [
  "precision highp float;",
  "uniform vec2 u_res;",
  "uniform float u_time;",
  "uniform float u_seed;",
  "uniform vec2 u_wind;",
  "uniform float u_gust;",
  "uniform vec3 u_pointer;",
  "uniform vec2 u_sun;",
  "uniform vec3 u_sunShape;",
  "uniform float u_leafAngle;",
  "uniform float u_leafSize;",
  "uniform float u_density;",
  "uniform float u_blur;",
  "uniform float u_shadow;",
  "uniform float u_sway;",
  "uniform float u_flutter;",
  "uniform float u_grain;",
  "uniform float u_gain;",
  "uniform vec3 u_wallTop;",
  "uniform vec3 u_wallBottom;",
  "uniform vec3 u_bounce;",
  "uniform vec3 u_light;",
  "uniform vec3 u_hot;",
  "",
  "mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c, s, -s, c); }",
  "float h21(vec2 p){ vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }",
  "vec2 h22(vec2 p){ vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973)); q += dot(q, q.yzx + 33.33); return fract((q.xx + q.yz) * q.zy); }",
  "float vnoise(vec2 p){",
  "  vec2 i = floor(p), f = fract(p);",
  "  f = f * f * (3.0 - 2.0 * f);",
  "  return mix(mix(h21(i), h21(i + vec2(1.0, 0.0)), f.x), mix(h21(i + vec2(0.0, 1.0)), h21(i + vec2(1.0, 1.0)), f.x), f.y);",
  "}",
  "",
  // Returns how much light gets through one layer, 0..1.
  "float canopy(vec2 q, float t, float blur, float seed, float flut, float tilt){",
  "  vec2 cell = vec2(1.2, 0.42);",
  "  vec2 g = q / cell;",
  "  vec2 id = floor(g);",
  "  vec2 f = fract(g);",
  "  float clear = 1.0;",
  // rows are narrow, so look two either side: a tilted leaf never gets clipped
  "  for (int j = -2; j <= 2; j++) {",
  "    for (int i = -1; i <= 1; i++) {",
  "      vec2 o = vec2(float(i), float(j));",
  "      vec2 cid = id + o;",
  "      vec2 r = h22(cid + seed * 17.0);",
  "      float r2 = h21(cid + seed * 31.0 + 7.1);",
  // the clump field: whole branches are present or missing, not single leaves
  "      float clump = vnoise(cid * vec2(0.42, 0.6) + seed * 5.0 + t * 0.015);",
  "      float keep = smoothstep(0.0, 0.25, clump + u_density - 0.75 + r2 * 0.3);",
  "      if (keep < 0.002) continue;",
  "      float ph = r2 * 6.2831;",
  "      float sp = 2.1 + r.x * 2.9;",
  "      float flick = sin(t * sp + ph) + 0.5 * sin(t * (sp * 2.3 + 1.1) + ph * 2.0);",
  "      vec2 c = o + 0.5 + (r - 0.5) * 0.55;",
  "      vec2 d = (f - c) * cell;",
  "      d += vec2(sin(t * 1.3 + ph), cos(t * 1.7 + ph * 1.3)) * 0.04 * flut;",
  // a small, bounded twist; the rest of the flutter is the leaf turning on
  // its stem, which reads on a wall as the silhouette going thin and back
  "      d = rot(tilt + (r.y - 0.5) * 0.7 + clamp(flick * flut * 0.1, -0.3, 0.3)) * d;",
  "      float len = 0.3 + 0.3 * r.x;",
  "      float wid = (0.15 + 0.11 * r.y) * (1.0 - min(flut, 1.6) * 0.22 * (0.5 + 0.5 * flick));",
  // a leaf, not an ellipse: narrower toward the tip
  "      d.y *= 1.0 + 0.5 * smoothstep(-len, len, d.x);",
  "      float k = length(d / vec2(len, wid));",
  "      float a = 1.0 - smoothstep(1.0 - blur, 1.0 + blur * 0.35, k);",
  "      clear *= 1.0 - a * keep;",
  "    }",
  "  }",
  "  return clear;",
  "}",
  "",
  "void main(){",
  "  vec2 uv = gl_FragCoord.xy / u_res;",
  "  float m = max(min(u_res.x, u_res.y), max(u_res.x, u_res.y) * 0.62);",
  "  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / m;",
  "  float t = u_time;",
  "",
  // the sun patch
  "  vec2 s = rot(-u_sunShape.z) * (p - u_sun);",
  "  float e = length(s / u_sunShape.xy);",
  "  float sun = 1.0 - smoothstep(0.2, 1.05, e);",
  "  sun = sun * sun * (3.0 - 2.0 * sun);",
  "  float core = exp(-e * e * 4.0);",
  "",
  // the pointer parts the leaves near it and makes them shiver
  "  vec2 dp = p - u_pointer.xy;",
  "  float near = u_pointer.z * exp(-dot(dp, dp) / 0.05);",
  "  float flut = u_flutter * (0.25 + 0.75 * u_gust) + near * 1.4;",
  "",
  // branches sway as a body: a slow, smooth warp of the whole leaf space
  "  vec2 w = p + u_wind;",
  "  w += vec2(sin(t * 0.43 + p.y * 1.7) + 0.5 * sin(t * 0.97 + p.x * 2.3),",
  "            cos(t * 0.37 + p.x * 1.3) + 0.5 * cos(t * 0.81 + p.y * 2.9)) * 0.045 * u_sway * (0.5 + u_gust);",
  "  w += dp * near * 0.22;",
  "",
  "  vec2 q = rot(-u_leafAngle) * w / max(u_leafSize, 0.02);",
  "  float b = clamp(u_blur, 0.0, 1.0);",
  // far layer: bigger, softer, lags the wind; near layer: sharper, moves more
  "  float far = canopy(q * 0.62 + vec2(3.7, 1.9) - u_wind * 0.6, t * 0.7, 0.55 + b * 0.45, 1.0, flut * 0.6, -0.22);",
  "  float nr = canopy(q + u_wind * 0.8, t, 0.2 + b * 0.6, 2.0, flut, 0.18);",
  "  float through = mix(1.0, far * nr, u_shadow);",
  "  float lit = sun * through * u_gain;",
  "",
  "  float diag = clamp(uv.x * 0.65 + (1.0 - uv.y) * 0.45, 0.0, 1.0);",
  "  vec3 col = mix(u_wallTop, u_wallBottom, smoothstep(0.0, 1.0, diag));",
  "  col = mix(col, u_bounce, sun * 0.55);",
  "  col = mix(col, u_light, clamp(lit, 0.0, 1.0));",
  "  col += (u_hot - u_light) * lit * core * 0.45;",
  "",
  // film grain, stepped at 24 fps so it reads as film and not as noise
  "  float n = h21(gl_FragCoord.xy + u_seed * 101.7) + h21(gl_FragCoord.xy * 1.37 - u_seed * 57.3) - 1.0;",
  "  col += n * u_grain;",
  "  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);",
  "}",
].join("\n")

const COLOR_KEYS = ["wallTop", "wallBottom", "bounce", "light", "hot"]
const FLOAT_KEYS = ["leafAngle", "leafSize", "density", "blur", "shadow", "sway", "flutter", "grain"]

export default function LilacDuskCanopy({
  height = "100svh",
  preset = "lilac-dusk",
  params,
  interactive = true,
  speed = 1,
  className = "",
  style,
  children,
}) {
  const rootRef = useRef(null)
  const canvasRef = useRef(null)
  const [failed, setFailed] = useState(false)
  const [generation, setGeneration] = useState(0)

  // Defaults < preset < explicit params. The loop reads through a ref, so
  // tuning a value never tears down the GL context.
  const P = useMemo(
    () => ({ ...CANOPY_DEFAULTS, ...(CANOPY_PRESETS[preset] ?? {}), ...(params ?? {}) }),
    [preset, params],
  )
  const live = useRef({ P, speed, interactive })
  live.current = { P, speed, interactive }
  // With no loop running (reduced motion, off-screen) new params still repaint.
  const repaint = useRef(null)
  useEffect(() => {
    repaint.current?.()
  }, [P])

  useEffect(() => {
    const root = rootRef.current
    const canvas = canvasRef.current
    if (!root || !canvas) return

    const gl = canvas.getContext("webgl", {
      antialias: false,
      alpha: false,
      depth: false,
      stencil: false,
      preserveDrawingBuffer: false,
      powerPreference: "low-power",
    })
    if (!gl) {
      setFailed(true)
      return
    }

    const compile = (type, source) => {
      const sh = gl.createShader(type)
      if (!sh) return null
      gl.shaderSource(sh, source)
      gl.compileShader(sh)
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error("lilac-dusk-canopy:", gl.getShaderInfoLog(sh))
        gl.deleteShader(sh)
        return null
      }
      return sh
    }
    const vs = compile(gl.VERTEX_SHADER, VERT)
    const fs = compile(gl.FRAGMENT_SHADER, FRAG)
    const program = vs && fs ? gl.createProgram() : null
    if (!program || !vs || !fs) {
      setFailed(true)
      return
    }
    gl.attachShader(program, vs)
    gl.attachShader(program, fs)
    gl.linkProgram(program)
    gl.deleteShader(vs)
    gl.deleteShader(fs)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("lilac-dusk-canopy:", gl.getProgramInfoLog(program))
      gl.deleteProgram(program)
      setFailed(true)
      return
    }
    gl.useProgram(program)

    // one triangle that covers the screen
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const aPos = gl.getAttribLocation(program, "a_pos")
    gl.enableVertexAttribArray(aPos)
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0)

    const loc = (n) => gl.getUniformLocation(program, n)
    const U = {
      res: loc("u_res"), time: loc("u_time"), seed: loc("u_seed"), wind: loc("u_wind"),
      gust: loc("u_gust"), pointer: loc("u_pointer"), sun: loc("u_sun"), sunShape: loc("u_sunShape"),
      gain: loc("u_gain"),
    }
    const colorLocs = COLOR_KEYS.map((k) => loc("u_" + k))
    const floatLocs = FLOAT_KEYS.map((k) => loc("u_" + k))

    // ---- sizing, from the element rather than the window --------------------
    // The light is soft by nature, so the drawing buffer stays near 1x even on
    // dense screens; the grain is the only fine detail and it wants to be soft.
    let cssW = 1
    let cssH = 1
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.25)
      cssW = Math.max(canvas.clientWidth, 1)
      cssH = Math.max(canvas.clientHeight, 1)
      const w = Math.max(1, Math.round(cssW * dpr))
      const h = Math.max(1, Math.round(cssH * dpr))
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
      }
    }
    resize()

    // ---- state ---------------------------------------------------------------
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    let clock = 7.3 // start mid-breeze, not at the phase where every sine is zero
    let windX = 0
    let windY = 0
    let windVX = 0
    let windVY = 0
    let boost = 0
    let stir = 0
    let pointerU = 0.5
    let pointerV = 0.5
    let pointerSeen = false
    let sunU = live.current.P.sunX
    let sunV = live.current.P.sunY
    let frameNo = 0

    const toUv = (e) => {
      const r = canvas.getBoundingClientRect()
      return [
        Math.min(Math.max((e.clientX - r.left) / Math.max(r.width, 1), 0), 1),
        Math.min(Math.max(1 - (e.clientY - r.top) / Math.max(r.height, 1), 0), 1),
      ]
    }
    const onMove = (e) => {
      if (!live.current.interactive) return
      const [u, v] = toUv(e)
      if (pointerSeen) {
        const [dx, dy] = toWall(u - pointerU + 0.5, v - pointerV + 0.5, cssW, cssH)
        const k = live.current.P.push
        // a push, not a drag: the tree is shoved in the direction of travel
        windVX += dx * 2.4 * k
        windVY += dy * 2.4 * k
        stir = Math.min(1, stir + Math.hypot(dx, dy) * 9)
      }
      pointerU = u
      pointerV = v
      pointerSeen = true
      wake()
    }
    const onDown = (e) => {
      if (!live.current.interactive) return
      const [u, v] = toUv(e)
      pointerU = u
      pointerV = v
      pointerSeen = true
      // a gust: the whole canopy flutters and swings away from the click
      boost = 1
      stir = 1
      const [wx, wy] = toWall(u, v, cssW, cssH)
      const d = Math.hypot(wx, wy) || 1
      const k = live.current.P.push
      windVX += (-wx / d) * 0.9 * k
      windVY += (-wy / d) * 0.9 * k
      wake()
    }
    const onLeave = () => {
      pointerSeen = false
    }
    // Window, not the section: as a fixed background the section sits under
    // the desk content, so pointer events on the content would never reach
    // it — window sees them all.
    window.addEventListener("pointermove", onMove)
    window.addEventListener("pointerdown", onDown)
    document.addEventListener("mouseleave", onLeave)

    // ---- draw ----------------------------------------------------------------
    const draw = () => {
      const { P: p } = live.current
      gl.viewport(0, 0, canvas.width, canvas.height)
      gl.uniform2f(U.res, canvas.width, canvas.height)
      gl.uniform1f(U.time, clock)
      gl.uniform1f(U.seed, (frameNo % 97) + 0.5)
      gl.uniform2f(U.wind, windX, windY)
      const gust = Math.min(1, gustAt(clock, p.gustiness) + boost * 0.8)
      gl.uniform1f(U.gust, gust)
      const [px, py] = toWall(pointerU, pointerV, cssW, cssH)
      gl.uniform3f(U.pointer, px, py, stir)
      const [sx, sy] = toWall(sunU, sunV, cssW, cssH)
      gl.uniform2f(U.sun, sx, sy)
      gl.uniform3f(U.sunShape, Math.max(p.sunWidth, 0.05), Math.max(p.sunHeight, 0.05), p.sunAngle)
      // the sun's shimmer: something higher up in the tree passing in front of it
      const shimmer = noise1(clock * 1.9, 9.1) * 0.6 + noise1(clock * 5.3, 3.3) * 0.4
      gl.uniform1f(U.gain, 1 - Math.min(Math.max(p.flicker, 0), 1) * 0.28 * shimmer * (0.5 + gust * 0.5))
      COLOR_KEYS.forEach((k, i) => {
        const [r, g, b] = hexToRgb(p[k])
        gl.uniform3f(colorLocs[i], r, g, b)
      })
      FLOAT_KEYS.forEach((k, i) => gl.uniform1f(floatLocs[i], p[k]))
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }

    let raf = 0
    let last = 0
    let visible = true
    let grainClock = 0

    const frame = (now) => {
      raf = 0
      const dt = last ? Math.min((now - last) / 1000, 0.1) : 1 / 60
      last = now
      const { P: p, speed: sp } = live.current
      const s = Math.max(sp, 0)
      clock += dt * s

      // the tree swings back to rest on a spring, with a little overshoot
      ;[windX, windVX] = springStep(windX, windVX, 0, dt, 7, 2.6)
      ;[windY, windVY] = springStep(windY, windVY, 0, dt, 7, 2.6)
      windX = Math.min(Math.max(windX, -0.6), 0.6)
      windY = Math.min(Math.max(windY, -0.6), 0.6)
      boost = approach(boost, 0, dt, 0.9)
      stir = approach(stir, 0, dt, 1.4)

      const follow = live.current.interactive && pointerSeen ? p.follow : 0
      sunU = approach(sunU, p.sunX + (pointerU - 0.5) * follow, dt, 2.2)
      sunV = approach(sunV, p.sunY + (pointerV - 0.5) * follow, dt, 2.2)

      grainClock += dt
      if (grainClock >= 1 / 24) {
        grainClock %= 1 / 24
        frameNo++
      }

      draw()
      if (visible) raf = requestAnimationFrame(frame)
    }

    // Reduced motion: one still frame, redrawn only when the box changes size.
    function wake() {
      if (reduced || raf || !visible) return
      last = 0
      raf = requestAnimationFrame(frame)
    }

    const observer = new ResizeObserver(() => {
      resize()
      if (reduced || !raf) draw()
    })
    observer.observe(canvas)

    const io = new IntersectionObserver(([en]) => {
      visible = en.isIntersecting
      if (visible) wake()
    })
    io.observe(root)

    const onLost = (e) => {
      e.preventDefault()
      cancelAnimationFrame(raf)
      raf = 0
    }
    const onRestored = () => setGeneration((g) => g + 1)
    canvas.addEventListener("webglcontextlost", onLost)
    canvas.addEventListener("webglcontextrestored", onRestored)

    repaint.current = () => {
      if (!raf) draw()
    }

    // paint before the first rAF, so nothing ever sees an empty canvas
    draw()
    wake()

    return () => {
      cancelAnimationFrame(raf)
      raf = 0
      visible = false
      repaint.current = null
      observer.disconnect()
      io.disconnect()
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("pointerdown", onDown)
      document.removeEventListener("mouseleave", onLeave)
      canvas.removeEventListener("webglcontextlost", onLost)
      canvas.removeEventListener("webglcontextrestored", onRestored)
      gl.deleteBuffer(buffer)
      gl.deleteProgram(program)
    }
  }, [generation])

  const fallback = hexToRgb(P.light)
  return (
    <section
      ref={rootRef}
      className={"canopy-root " + className}
      style={{ height, backgroundColor: P.wallTop, ...style }}
      aria-label="Sunlight through leaves on a wall"
    >
      {failed ? (
        // No WebGL: a still picture of the same light beats an empty box.
        <div
          aria-hidden="true"
          className="canopy-fallback"
          style={{
            background:
              "radial-gradient(110% 80% at " + P.sunX * 100 + "% " + (1 - P.sunY) * 100 + "%, rgba(" +
              fallback.map((c) => Math.round(c * 255)).join(",") + ",0.95) 0%, " +
              P.bounce + " 38%, " + P.wallBottom + " 72%, " + P.wallTop + " 100%)",
          }}
        />
      ) : (
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          style={{ width: "100%", height: "100%", maxWidth: "none" }}
        />
      )}
      {children ? <div className="canopy-children">{children}</div> : null}
    </section>
  )
}
