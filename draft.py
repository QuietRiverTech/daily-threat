#!/usr/bin/env python3
"""
draft.py — Phase 1: Generate tomorrow's Daily Threat script draft.
Run at ~9 PM the night before. Saves draft for review.
"""
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import EPISODES_DIR
from fetcher import fetch_cves
from writer import generate_script

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DRAFTS_DIR = EPISODES_DIR / "drafts"
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_draft():
    """Fetch CVEs and generate tomorrow's script draft."""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_display = (datetime.now() + timedelta(days=1)).strftime("%B %d, %Y")

    log.info(f"Generating draft for {tomorrow_display}...")

    # Fetch current threat landscape
    cves = fetch_cves()
    log.info(f"Fetched {len(cves)} CVEs")

    # Generate script
    script = generate_script(cves)
    word_count = len(script.split())
    log.info(f"Script generated: {word_count} words")

    # Save draft
    draft_path = DRAFTS_DIR / f"draft-{tomorrow}.txt"
    draft_path.write_text(script)

    # Save CVE data alongside for morning comparison
    cve_path = DRAFTS_DIR / f"draft-{tomorrow}-cves.json"
    cve_path.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "target_date": tomorrow,
        "cves": cves,
        "word_count": word_count,
    }, indent=2, default=str))

    log.info(f"Draft saved: {draft_path}")

    # Format for Telegram delivery
    output = []
    output.append(f"🎙️ **DAILY THREAT DRAFT — {tomorrow_display}**")
    output.append(f"📏 {word_count} words | ~{word_count * 60 // 150 // 60}m {(word_count * 60 // 150) % 60}s")
    output.append(f"🔍 {len(cves)} CVEs covered")
    output.append("")
    output.append("**CVEs in this episode:**")
    for c in cves[:4]:
        sev = "🔴 CRITICAL" if c["cvss"] >= 9.0 else "🟠 HIGH" if c["cvss"] >= 7.0 else "🟡 MEDIUM"
        kev = " ⚠️ KEV" if c.get("kev") else ""
        output.append(f"  • {c['cve_id']} ({c['cvss']}) — {c['product']}{kev} {sev}")
    output.append("")
    output.append("---")
    output.append("")
    output.append(script)
    output.append("")
    output.append("---")
    output.append("")
    output.append("✏️ **Reply with edits or say 'publish daily threat' in the morning to go live.**")

    print("\n".join(output))
    return draft_path


if __name__ == "__main__":
    generate_draft()
