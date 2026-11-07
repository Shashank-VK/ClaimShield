#!/usr/bin/env python3
"""ClaimShield Desk voiceover — standalone, copy-paste version.

Run this on YOUR machine (not the VM): python3 fenrir-voiceover.py
It needs ONLY Python 3 — no installs, no ffmpeg.

What it does: generates all 7 voiceover sections in Fenrir's voice
(warm, conversational, natural Indian English accent) via Gemini TTS
and saves them as .wav files in a folder called claimshield-voice.
Send those 7 .wav files back and I will build them into the video.

Your Gemini API key: the script asks for it when it runs (it is hidden
as you type). Get one free at https://aistudio.google.com -> "Get API key".
If it answers 429 (quota), make a FRESH key there and run it again.
"""
import base64
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave

MODEL = "gemini-2.5-flash-preview-tts"
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


def tts(key, text, out_wav):
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
                                     headers={"x-goog-api-key": key,
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} attempt {attempt}", flush=True)
            if e.code == 429:
                print("  quota hit — waiting 45s before retry", flush=True)
                time.sleep(45)
                continue
            if e.code in (400, 401, 403):
                print("  key problem — check the API key and run again", flush=True)
            return False
        except Exception as e:
            print(f"  error {e} attempt {attempt}", flush=True)
            time.sleep(20)
            continue
        try:
            b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError):
            print("  unexpected response:", json.dumps(data)[:300], flush=True)
            return False
        pcm = base64.b64decode(b64)
        with wave.open(out_wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
        return True
    return False


def main():
    only = sys.argv[1:] or None
    key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Paste your Gemini API key: ").strip()
    if not key:
        print("No key given — stopping.")
        return
    outdir = os.path.join(os.getcwd(), "claimshield-voice")
    os.makedirs(outdir, exist_ok=True)
    print(f"Saving files to: {outdir}\n", flush=True)
    made, failed = [], []
    for slug, text in SECTIONS:
        if only and slug not in only:
            continue
        out = os.path.join(outdir, f"v2-{slug}.wav")
        print(f"== {slug} ==", flush=True)
        if tts(key, text, out):
            size = os.path.getsize(out)
            with wave.open(out, "rb") as w:
                dur = w.getnframes() / w.getframerate()
            print(f"  OK {out} ({dur:.1f}s, {size} bytes)", flush=True)
            made.append(slug)
        else:
            print(f"  FAILED {slug}", flush=True)
            failed.append(slug)
        time.sleep(35)
    print(f"\nDone. Made {len(made)}/7: {', '.join(made) or 'none'}", flush=True)
    if failed:
        print(f"Failed: {', '.join(failed)} — re-run with just those names, e.g.: "
              f"python3 {sys.argv[0]} {' '.join(failed)}", flush=True)
    print(f"Send the 7 .wav files in {outdir} back and I will build the video.", flush=True)


if __name__ == "__main__":
    main()
