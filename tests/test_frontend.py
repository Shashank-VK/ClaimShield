"""Tests for the basic Next.js cockpit (cs-008).

Builds the frontend (``npm run build``), serves it, and checks the three
panes render and that no unverified IRDAI percentages or DPDP sub-rule text
appears anywhere in the UI.
"""

import json
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = PROJECT_ROOT / "frontend"
FORBIDDEN = ["IRDAI", "DPDP", "Bima Bharosa"]


def _run(cmd, cwd, timeout=300):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="module")
def built_frontend():
    if not (FRONTEND / "node_modules").exists():
        install = _run(["npm", "install", "--no-audit", "--no-fund"], FRONTEND, timeout=600)
        assert install.returncode == 0, install.stdout[-2000:] + install.stderr[-2000:]
    build = _run(["npm", "run", "build"], FRONTEND, timeout=600)
    assert build.returncode == 0, build.stdout[-3000:] + build.stderr[-3000:]
    return FRONTEND


def test_next_build_succeeds(built_frontend):
    assert (built_frontend / ".next" / "BUILD_ID").exists()


def test_cockpit_serves_three_panes(built_frontend):
    proc = subprocess.Popen(
        ["npm", "run", "start", "--", "-p", "3000"],
        cwd=str(built_frontend),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 30
        html = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen("http://127.0.0.1:3000/", timeout=3) as resp:
                    html = resp.read().decode()
                    break
            except Exception:
                time.sleep(1)
        assert html is not None, "Next.js server did not answer in time"
        for pane in ("Live Updates", "Memory Check", "Rules"):
            assert pane in html, f"pane {pane!r} missing from served cockpit"
        # The plain-language 3-step explainer must be on the first screen.
        for step in ("It remembers what worked", "It checks the new claim", "It fixes it, or stops it"):
            assert step in html, f"explainer step {step!r} missing from served cockpit"
        assert "Draft for human review" in html
        assert "SYNTHETIC" in html
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_no_unverified_stats_text_in_ui():
    sources = list(FRONTEND.rglob("*.jsx")) + list(FRONTEND.rglob("*.js")) + list(FRONTEND.rglob("*.css"))
    for path in sources:
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN:
            assert forbidden not in text, f"{forbidden} found in UI source {path}"
