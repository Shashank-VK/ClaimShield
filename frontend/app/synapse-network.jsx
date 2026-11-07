// Synapse network backdrop — port of the InteractiveSynapseNetwork component
// to plain JS + hand CSS (this frontend has no TypeScript / Tailwind / shadcn).
// Mounted as a fixed layer BEHIND the desk: the canvas is transparent
// (clearRect each frame, no opaque trail wash) so the page grid shows through,
// and its colours come from the active theme's --network-* CSS vars, so it
// reads on dark and light alike. Pointer events come from the window, so the
// network still reacts to the cursor even though the canvas never takes clicks.
"use client";

import { useRef, useEffect } from "react";

export default function SynapseNetwork({ theme }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Theme colours: --network-node / --network-line / --network-pulse hold
    // "r, g, b" triplets in globals.css, one set per theme.
    const css = getComputedStyle(document.documentElement);
    const nodeRgb = (css.getPropertyValue("--network-node") || "41, 151, 255").trim();
    const lineRgb = (css.getPropertyValue("--network-line") || "41, 151, 255").trim();
    const pulseRgb = (css.getPropertyValue("--network-pulse") || "255, 255, 255").trim();

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const nodeCount = window.innerWidth < 700 ? 30 : 50;
    const connectionRadius = 180;

    let width = window.innerWidth;
    let height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const sizeCanvas = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    sizeCanvas();

    const mouse = { x: -9999, y: -9999 };

    class Pulse {
      constructor(start, end) {
        this.start = start;
        this.end = end;
        this.progress = 0;
        this.speed = 0.03;
      }
      update() {
        this.progress += this.speed;
      }
      draw() {
        const x = this.start.x + (this.end.x - this.start.x) * this.progress;
        const y = this.start.y + (this.end.y - this.start.y) * this.progress;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${pulseRgb}, 0.9)`;
        ctx.fill();
      }
    }

    class Node {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.radius = Math.random() * 2 + 2;
        this.connections = [];
        this.pulses = [];
        this.activation = 0;
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > width) this.vx *= -1;
        if (this.y < 0 || this.y > height) this.vy *= -1;

        const dx = this.x - mouse.x;
        const dy = this.y - mouse.y;
        const dist = Math.hypot(dx, dy);
        const target = Math.max(0, 1 - dist / (connectionRadius * 0.8));
        this.activation += (target - this.activation) * 0.1;

        if (this.activation > 0.5 && Math.random() > 0.98) {
          const to = this.connections[Math.floor(Math.random() * this.connections.length)];
          if (to) this.pulses.push(new Pulse(this, to));
        }
        this.pulses = this.pulses.filter((p) => p.progress < 1);
        this.pulses.forEach((p) => p.update());
      }
      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        const alpha = Math.max(0.3, this.activation);
        ctx.fillStyle = `rgba(${nodeRgb}, ${alpha})`;
        ctx.fill();
        this.pulses.forEach((p) => p.draw());
      }
    }

    const nodes = Array.from({ length: nodeCount }, () => new Node());
    nodes.forEach((n1) => {
      nodes.forEach((n2) => {
        if (n1 !== n2 && Math.hypot(n1.x - n2.x, n1.y - n2.y) < connectionRadius) {
          n1.connections.push(n2);
        }
      });
    });

    const drawFrame = () => {
      // Transparent clear (not the pasted component's opaque teal wash) so
      // the page background and grid stay visible behind the network.
      ctx.clearRect(0, 0, width, height);
      nodes.forEach((n1) => {
        n1.connections.forEach((n2) => {
          const a = Math.max(0.05, n1.activation, n2.activation) * 0.25;
          ctx.beginPath();
          ctx.moveTo(n1.x, n1.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.strokeStyle = `rgba(${lineRgb}, ${a})`;
          ctx.stroke();
        });
      });
      nodes.forEach((n) => n.draw());
    };

    const onPointerMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    const onPointerLeave = () => {
      mouse.x = -9999;
      mouse.y = -9999;
    };
    const onResize = () => sizeCanvas();

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerleave", onPointerLeave);
    window.addEventListener("resize", onResize);

    let raf;
    if (reduced) {
      // One static frame, no animation loop.
      drawFrame();
    } else {
      const animate = () => {
        nodes.forEach((n) => n.update());
        drawFrame();
        raf = requestAnimationFrame(animate);
      };
      animate();
    }

    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("resize", onResize);
    };
  }, [theme]);

  return (
    <div className="synapse-bg" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
