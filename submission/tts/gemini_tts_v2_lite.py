#!/usr/bin/env python3
"""Gemini TTS for the ClaimShield Desk v2 story script (7 sections).

Model: gemini-2.5-flash-lite-preview-tts, voice Fenrir, warm/relaxed/conversational
direction + natural Indian English accent (style prefix is direction, not spoken).
Key: ~/.config/provider-keys/gemini.key (never printed). Pro TTS is quota-blocked;
Flash only. ~35s between calls to dodge the free-tier 429s; retry each up to 3x.
Writes PCM -> mp3 via ffmpeg into submission/vo/v2-s<N>-<slug>.mp3.
"""
import base64
import json
import subprocess
import sys
import time
import urllib.request

KEY = open("/home/hatch/.config/provider-keys/gemini.key").read().strip()
MODEL = "gemini-2.5-flash-lite-preview-tts"
OUT = "/home/hatch/workspace/goals/hackwithbangalore-4-0-hackathon/builds/claimshield-desk/submission/vo"
STYLE = (
    "Say in a warm, relaxed, conversational tone, with a natural Indian English accent. "
    "Speak like a teammate telling a story, not like a narrator reading a script. "
    "Keep the pace natural, pause briefly between sentences. "
    "Say exactly this, and nothing else: "
)

SECTIONS = [
    ("s1-hook", "Hi, we're Team God Protocol. Every hospital has a desk where hope goes to wait. "
     "A family paid the bill out of pocket and filed for reimbursement — one lakh forty-five thousand rupees — "
     "and the insurer answers in a single line: OPD-convertible. Denied. "
     "The person at the desk appeals the way she always has: a generic letter, no evidence attached. It fails. "
     "Six months later, the same denial comes back. Same appeal. Same failure."),
    ("s2-problem", "The desk didn't fail because it didn't care. It failed because it forgot. "
     "The desk handles both kinds of claims — cashless approvals at the counter, and reimbursement claims from "
     "families who already paid and are waiting to be paid back — thousands a day. "
     "The knowledge was there — a senior staffer knew Star Health overturns dengue denials when the NS1 report "
     "and the IV fluid sheets are attached. But that knowledge lived in one person's head, or in a spreadsheet "
     "nobody opens. And when she was on leave, or the file was buried, every new denial started from zero. "
     "So we asked a simple question: what if the desk itself could remember?"),
    ("s3-turn", "That's ClaimShield Desk. Every appeal outcome — overturned, partially paid, rejected, "
     "cashless or reimbursement — is retained in Hindsight memory, with a proof count: how many times that "
     "pattern has actually worked. When the dengue denial comes in now, the desk doesn't guess. It recalls the "
     "win at proof five, cites the NS1 report, and drafts the appeal from what worked. The same denial that "
     "failed twice now walks in with evidence behind it. And the first thing the desk learns is what a failure "
     "looks like: a generic appeal, no recalled evidence, vetoed at proof zero."),
    ("s4-scrub", "Before any of that, the desk scrubs the packet. PAN, Aadhaar, phone numbers — redacted "
     "before a single word is remembered. A raw SSN in a document gets caught by the second layer too. "
     "Nothing about a patient is ever retained unscrubbed. Memory you can't trust with data is memory you "
     "can't trust at all."),
    ("s5-critic", "But memory alone isn't enough. Memory can go stale — and stale memory is worse than no "
     "memory. In October, Star Health changed the rule for knee-surgery appeals: the old four-week physio "
     "trial was out; six weeks plus an X-ray was in. The desk drafted on the old argument anyway. And the "
     "critic caught it — vetoed the appeal before it left the desk, and named exactly what was missing. "
     "It does the same to a poisoned packet that just says approve anyway: no evidence, no grounds, vetoed. "
     "A plain RAG system approves that packet. Memory that can't say no is just a louder way to be wrong."),
    ("s6-gate", "And nothing becomes a rule without a human. A person approves the packet, and the scrubber "
     "learns: from now on, the dengue rule needs the platelet report too. The same complete packet that passed "
     "a minute earlier is blocked until the report is attached. The denial never happens again. "
     "The desk doesn't just remember. It learns."),
    ("s7-wrap", "We measured it, we didn't claim it. On twenty cases plus five adversarial ones: Stateless "
     "scored sixteen out of twenty. Plain RAG scored eleven — and approved the poisoned packet. Hindsight "
     "scored nineteen out of twenty, five out of five adversarial. A desk that remembers — cashless or "
     "reimbursement — is a desk that stops losing the same fight twice. That's ClaimShield Desk — built by "
     "Team God Protocol, with Hindsight memory. The desk remembers now."),
]


def tts(text: str, out_mp3: str) -> bool:
    body = json.dumps({
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Fenrir"}}},
        },
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for attempt in range(1, 4):
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} attempt {attempt}", flush=True)
            if e.code == 429:
                time.sleep(45)
                continue
            return False
        except Exception as e:
            print(f"  error {e} attempt {attempt}", flush=True)
            time.sleep(20)
            continue
        try:
            b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError):
            print("  unexpected response shape", json.dumps(data)[:300], flush=True)
            return False
        pcm = base64.b64decode(b64)
        p = subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", "24000", "-ac", "1",
                            "-i", "-", "-q:a", "2", out_mp3, "-y"],
                           input=pcm, capture_output=True)
        if p.returncode != 0:
            print("  ffmpeg failed:", p.stderr.decode()[:200], flush=True)
            return False
        return True
    return False


def main():
    only = sys.argv[1:] or None
    for slug, text in SECTIONS:
        if only and slug not in only:
            continue
        out = f"{OUT}/v2-{slug}.mp3"
        print(f"== {slug} ==", flush=True)
        if tts(text, out):
            d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", out], capture_output=True, text=True)
            print(f"  OK {out} {d.stdout.strip()}s", flush=True)
        else:
            print(f"  FAILED {slug}", flush=True)
        time.sleep(35)


if __name__ == "__main__":
    main()
