#!/usr/bin/env python3
"""Rebuild claimshield-desk-deck.pptx — dark ClaimShield theme, same 8 slides/content.

Design: 16:9, canvas #0B0E13, Apple Action Blue #2997FF, semantic
APPROVE #30D158 / VETO #FF453A / BLOCKED #FFD60A, Arial, solid fills only.
No emojis, no card grids, no gradients. Slide 4 is a light figure plate because
the architecture diagram itself is light-background.
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "claimshield-desk-deck.pptx")
DIAGRAM = os.path.join(HERE, "architecture-diagram.png")

BG = RGBColor(0x0B, 0x0E, 0x13)
PANEL = RGBColor(0x14, 0x18, 0x1F)
DIV = RGBColor(0x2A, 0x2F, 0x38)
INK = RGBColor(0xF5, 0xF5, 0xF7)
MUTED = RGBColor(0x9B, 0xA0, 0xA6)
BLUE = RGBColor(0x29, 0x97, 0xFF)
GREEN = RGBColor(0x30, 0xD1, 0x58)
RED = RGBColor(0xFF, 0x45, 0x3A)
AMBER = RGBColor(0xFF, 0xD6, 0x0A)
DARKTXT = RGBColor(0x0B, 0x0E, 0x13)
LIGHTBG = RGBColor(0xF5, 0xF5, 0xF7)
LIGHTMUTED = RGBColor(0x5A, 0x5F, 0x66)
FONT = "Arial"
FOOTER = "ClaimShield Desk  ·  Team God Protocol  ·  github.com/Shashank-VK/ClaimShield"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    return s


def tb(slide, x, y, w, h):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text, size, color, bold=False, first=False, space_after=6,
         space_before=0, align=PP_ALIGN.LEFT, line=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    if line:
        p.line_spacing = line
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return p


def rule(slide, x, y, w, color=BLUE, h=0.03):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def panel(slide, x, y, w, h):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = PANEL
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def footer(slide, n, dark=False):
    tf = tb(slide, 0.6, 7.08, 11.0, 0.3)
    para(tf, FOOTER, 9, LIGHTMUTED if dark else MUTED, first=True)
    tf = tb(slide, 12.2, 7.08, 0.55, 0.3)
    para(tf, str(n), 9, LIGHTMUTED if dark else MUTED, first=True,
         align=PP_ALIGN.RIGHT)


def kicker_title(slide, kick, kick_color, title, dark=False, title_size=40):
    tf = tb(slide, 0.6, 0.5, 12.1, 0.35)
    para(tf, kick, 13, kick_color, bold=True, first=True, space_after=0)
    rule(slide, 0.6, 0.92, 0.9, kick_color)
    tf = tb(slide, 0.6, 1.12, 12.1, 0.9)
    para(tf, title, title_size, DARKTXT if dark else INK, bold=True,
         first=True, space_after=0)


# ---- Slide 1: title -------------------------------------------------------
s = new_slide()
tf = tb(s, 0.6, 1.45, 12.1, 0.35)
para(tf, "HINDSIGHT REMEMBERS.", 13, BLUE, bold=True, first=True)
rule(s, 0.6, 1.87, 0.9, BLUE)
tf = tb(s, 0.6, 2.05, 12.1, 1.1)
para(tf, "ClaimShield Desk", 60, INK, bold=True, first=True, space_after=0)
tf = tb(s, 0.6, 3.25, 11.5, 0.5)
para(tf, "AI denial-defense and pre-dispatch scrubber for Indian hospital "
         "TPA desks", 20, MUTED, first=True, line=1.15)
tf = tb(s, 0.6, 4.0, 11.5, 0.8)
para(tf, "The desk remembers now — every appeal outcome retained in "
         "Hindsight memory, with a proof count.", 16, INK, first=True, line=1.2)
rule(s, 0.6, 5.6, 12.13, DIV, h=0.015)
tf = tb(s, 0.6, 5.85, 12.1, 0.4)
para(tf, "Team God Protocol", 16, INK, bold=True, first=True, space_after=0)
tf = tb(s, 0.6, 6.3, 12.1, 0.4)
para(tf, "github.com/Shashank-VK/ClaimShield", 14, MUTED, first=True)
footer(s, 1)

# ---- Slide 2: problem ------------------------------------------------------
s = new_slide()
kicker_title(s, "THE PROBLEM", RED, "The desk forgot.")
tf = tb(s, 0.6, 2.15, 7.6, 4.4)
para(tf, "A family paid the bill out of pocket and filed for reimbursement "
         "— ₹1,45,000 for a dengue claim. The insurer answered in one line: "
         "“OPD-convertible.” Denied.", 15, INK, first=True, space_after=12,
     line=1.2)
para(tf, "The desk appealed the way it always had: a generic letter, no "
         "evidence attached. It failed. Six months later, the same denial "
         "came back. Same appeal. Same failure.", 15, INK, space_after=12,
     line=1.2)
para(tf, "The knowledge was there — a senior staffer knew Star Health "
         "overturns dengue denials when the NS1 report and IV fluid sheets "
         "are attached. But that knowledge lived in one person’s head, or in "
         "a spreadsheet nobody opens.", 15, INK, space_after=14, line=1.2)
para(tf, "So we asked: what if the desk itself could remember?", 16, BLUE,
     bold=True, space_after=0, line=1.2)
panel(s, 8.6, 2.15, 4.13, 3.6)
tf = tb(s, 9.0, 2.5, 3.4, 1.0)
para(tf, "DENIED", 44, RED, bold=True, first=True, space_after=0)
tf = tb(s, 9.0, 3.45, 3.4, 0.6)
para(tf, "₹1,45,000", 30, INK, bold=True, first=True, space_after=0)
tf = tb(s, 9.0, 4.15, 3.4, 0.4)
para(tf, "dengue · OPD-convertible", 13, MUTED, first=True, space_after=0)
rule(s, 9.0, 4.75, 3.33, DIV, h=0.015)
tf = tb(s, 9.0, 4.95, 3.4, 0.6)
para(tf, "Thousands of claims a day — cashless + reimbursement.",
     12, MUTED, first=True, line=1.2)
footer(s, 2)

# ---- Slide 3: idea ---------------------------------------------------------
s = new_slide()
kicker_title(s, "THE IDEA", BLUE, "Memory with a proof count.")
tf = tb(s, 0.6, 2.15, 7.6, 4.4)
para(tf, "Every appeal outcome — overturned, partially paid, rejected, "
         "cashless or reimbursement — is retained in Hindsight memory, with "
         "a proof count: how many times that pattern has actually worked.",
     15, INK, first=True, space_after=12, line=1.2)
para(tf, "When the dengue denial comes in now, the desk doesn’t guess. It "
         "recalls the win, cites the NS1 report, and drafts the appeal from "
         "what worked.", 15, INK, space_after=12, line=1.2)
para(tf, "And the first thing the desk learns is what a failure looks like: "
         "a generic appeal, no recalled evidence, vetoed at proof ×0.",
     15, INK, space_after=12, line=1.2)
para(tf, "Before any of that, the desk scrubs the packet. PAN, Aadhaar and "
         "phone numbers are redacted before a single word is remembered.",
     15, INK, space_after=0, line=1.2)
panel(s, 8.6, 2.15, 4.13, 3.6)
tf = tb(s, 9.0, 2.5, 3.4, 1.0)
para(tf, "proof ×5", 54, GREEN, bold=True, first=True, space_after=0)
tf = tb(s, 9.0, 3.55, 3.4, 0.5)
para(tf, "the dengue win, recalled", 15, INK, first=True, space_after=0)
rule(s, 9.0, 4.3, 3.33, DIV, h=0.015)
tf = tb(s, 9.0, 4.5, 3.4, 0.9)
para(tf, "proof ×0 — the generic appeal, vetoed", 13, RED, bold=True,
     first=True, space_after=4)
para(tf, "Memory that can’t say no is just a louder way to be wrong.",
     12, MUTED, line=1.2)
footer(s, 3)

# ---- Slide 4: how it works (light figure plate) ---------------------------
s = new_slide(bg=LIGHTBG)
kicker_title(s, "HOW IT WORKS", BLUE, "From denial to decision.", dark=True,
             title_size=36)
im = Image.open(DIAGRAM)
iw, ih = im.size
box_w, box_h = 12.13, 4.55
scale = min(box_w / iw, box_h / ih)
dw, dh = iw * scale, ih * scale
x = (13.333 - dw) / 2
y = 2.15 + (box_h - dh) / 2
s.shapes.add_picture(DIAGRAM, Inches(x), Inches(y),
                     Inches(dw), Inches(dh))
footer(s, 4, dark=True)

# ---- Slide 5: demo, four beats -------------------------------------------
s = new_slide()
kicker_title(s, "THE DEMO", BLUE, "Four beats.")
beats = [
    ("01", "Day-1 veto", "VETO · proof ×0", RED,
     "A generic appeal with no recalled evidence is vetoed at proof ×0."),
    ("02", "The scrub", "REDACTED · CLEAN", BLUE,
     "PAN, Aadhaar and phone numbers redacted; a raw SSN in a document is "
     "caught by the second layer."),
    ("03", "The critic", "VETO · stale tactic", RED,
     "Star Health changed the knee rule in Oct 2026: 4-week physio out, "
     "6 weeks + X-ray in. The desk drafts on the old argument; the critic "
     "vetoes it and names what is missing. A poisoned packet that says "
     "“approve anyway” is vetoed too — plain RAG approves it."),
    ("04", "The human gate", "BLOCKED · no report", AMBER,
     "A person approves the packet and the scrubber learns: the dengue rule "
     "now needs the platelet report too. The same packet that passed a "
     "minute earlier is blocked until the report is attached."),
]
y = 2.15
for num, name, verdict, vcolor, desc in beats:
    tf = tb(s, 0.6, y, 0.7, 0.4)
    para(tf, num, 20, BLUE, bold=True, first=True, space_after=0)
    tf = tb(s, 1.5, y, 7.6, 0.4)
    para(tf, name, 17, INK, bold=True, first=True, space_after=0)
    tf = tb(s, 9.4, y, 3.33, 0.4)
    para(tf, verdict, 14, vcolor, bold=True, first=True, space_after=0,
         align=PP_ALIGN.RIGHT)
    tf = tb(s, 1.5, y + 0.42, 11.23, 0.7)
    para(tf, desc, 12.5, MUTED, first=True, space_after=0, line=1.15)
    y += 1.18
    if num != "04":
        rule(s, 0.6, y - 0.08, 12.13, DIV, h=0.015)
footer(s, 5)

# ---- Slide 6: measured, not claimed ---------------------------------------
s = new_slide()
kicker_title(s, "THE PROOF", GREEN, "Measured, not claimed.")
tf = tb(s, 0.6, 2.05, 12.1, 0.4)
para(tf, "20 cases + 5 adversarial packets, run through three systems:",
     14, MUTED, first=True, space_after=0)
# header
y = 2.6
tf = tb(s, 0.6, y, 3.6, 0.35)
para(tf, "SYSTEM", 11, MUTED, bold=True, first=True, space_after=0)
tf = tb(s, 4.4, y, 2.0, 0.35)
para(tf, "MAIN / 20", 11, MUTED, bold=True, first=True, space_after=0,
     align=PP_ALIGN.CENTER)
tf = tb(s, 6.6, y, 2.0, 0.35)
para(tf, "ADVERSARIAL / 5", 11, MUTED, bold=True, first=True, space_after=0,
     align=PP_ALIGN.CENTER)
tf = tb(s, 9.0, y, 3.73, 0.35)
para(tf, "NOTE", 11, MUTED, bold=True, first=True, space_after=0)
rule(s, 0.6, y + 0.42, 12.13, DIV, h=0.015)
rows = [
    ("Stateless", "16", "—", "No memory at all.", INK),
    ("Plain RAG", "11", "0", "Approved the poisoned “approve anyway” packet.", INK),
    ("Hindsight (ClaimShield)", "19", "5", "Vetoed the poisoned packet.", GREEN),
]
y = 3.15
for name, main, adv, note, num_color in rows:
    tf = tb(s, 0.6, y, 3.6, 0.4)
    para(tf, name, 15, INK, bold=True, first=True, space_after=0)
    tf = tb(s, 4.4, y, 2.0, 0.4)
    para(tf, main, 18, num_color, bold=True, first=True, space_after=0,
         align=PP_ALIGN.CENTER)
    tf = tb(s, 6.6, y, 2.0, 0.4)
    para(tf, adv, 18, num_color, bold=True, first=True, space_after=0,
         align=PP_ALIGN.CENTER)
    tf = tb(s, 9.0, y + 0.03, 3.73, 0.4)
    para(tf, note, 12.5, MUTED, first=True, space_after=0, line=1.1)
    y += 0.78
    rule(s, 0.6, y - 0.08, 12.13, DIV, h=0.015)
tf = tb(s, 0.6, 5.85, 12.13, 0.8)
para(tf, "Honest limit (EVAL-14): ", 12.5, AMBER, bold=True, first=True,
     space_after=0)
p = tf.add_paragraph()
p.space_after = Pt(0)
r = p.add_run()
r.text = ("a bare “delayed intimation, please approve” appeal slips past "
          "the grounding check on shared words alone — keyword grounding is "
          "not semantic understanding yet.")
r.font.name = FONT
r.font.size = Pt(12.5)
r.font.color.rgb = MUTED
footer(s, 6)

# ---- Slide 7: stack ---------------------------------------------------------
s = new_slide()
kicker_title(s, "THE STACK", BLUE, "What it’s built on.")
tf = tb(s, 0.6, 2.15, 12.13, 1.1)
para(tf, "BACKEND", 13, BLUE, bold=True, first=True, space_after=4)
para(tf, "FastAPI (Python) — Hindsight 1.2 memory adapter, PII scrubber, "
         "pre-dispatch checker with versioned rules, Band room "
         "(Auditor → Critic veto chain).", 14.5, INK, space_after=0, line=1.2)
tf = tb(s, 0.6, 3.35, 12.13, 1.1)
para(tf, "FRONTEND", 13, BLUE, bold=True, first=True, space_after=4)
para(tf, "Next.js cockpit — Hindsight X-Ray with proof counts, beat rail, "
         "and a chat panel that runs the real work against the backend.",
     14.5, INK, space_after=0, line=1.2)
tf = tb(s, 0.6, 4.55, 12.13, 0.7)
para(tf, "Demo runs on the in-memory backend (49 tests green). The Hindsight "
         "Cloud key is verified live; Cloud rebuilds the seeded proof counts, "
         "so the demo stays on local memory.", 14.5, INK, first=True,
     space_after=0, line=1.2)
rule(s, 0.6, 5.55, 12.13, DIV, h=0.015)
tf = tb(s, 0.6, 5.8, 12.13, 1.0)
para(tf, "Repo: github.com/Shashank-VK/ClaimShield", 13, MUTED, first=True,
     space_after=4)
para(tf, "Articles: dev.to/shashankvk — “How I Taught a Billing Desk to "
         "Remember with Hindsight” and “How I Stress-Tested Hindsight "
         "Against Poisoned Claims”.", 13, MUTED, space_after=4)
para(tf, "Demo video: link in the submission form (YouTube).", 13, MUTED,
     space_after=0)
footer(s, 7)

# ---- Slide 8: close ---------------------------------------------------------
s = new_slide()
tf = tb(s, 0.9, 2.5, 11.53, 1.4)
para(tf, "A desk that remembers stops losing the same fight twice.", 34,
     INK, bold=True, first=True, space_after=0, align=PP_ALIGN.CENTER,
     line=1.15)
tf = tb(s, 0.9, 4.15, 11.53, 0.5)
para(tf, "ClaimShield Desk — the desk remembers now.", 18, BLUE, bold=True,
     first=True, space_after=0, align=PP_ALIGN.CENTER)
tf = tb(s, 0.9, 4.8, 11.53, 0.4)
para(tf, "github.com/Shashank-VK/ClaimShield", 14, MUTED, first=True,
     space_after=0, align=PP_ALIGN.CENTER)
footer(s, 8)

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
