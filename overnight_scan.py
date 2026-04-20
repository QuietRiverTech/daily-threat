#!/usr/bin/env python3
"""
overnight_scan.py — Phase 2: Scan for overnight high-viz events.
Run at ~5:30 AM. Compares against last night's draft and flags new threats.
"""
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import EPISODES_DIR
from fetcher import fetch_cves

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DRAFTS_DIR = EPISODES_DIR / "drafts"


def overnight_scan():
    """Compare overnight CVEs against last night's draft."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%B %d, %Y")

    draft_path = DRAFTS_DIR / f"draft-{today}.txt"
    cve_path = DRAFTS_DIR / f"draft-{today}-cves.json"

    # Load last night's draft data
    draft_exists = draft_path.exists()
    old_cve_ids = set()
    if cve_path.exists():
        data = json.loads(cve_path.read_text())
        old_cve_ids = {c["cve_id"] for c in data.get("cves", [])}
        generated_at = data.get("generated_at", "unknown")
    else:
        generated_at = "no draft found"

    # Fetch fresh CVEs
    log.info("Scanning for overnight events...")
    fresh_cves = fetch_cves()

    # Find NEW CVEs not in last night's draft
    new_cves = [c for c in fresh_cves if c["cve_id"] not in old_cve_ids]
    new_critical = [c for c in new_cves if c["cvss"] >= 9.0]
    new_kev = [c for c in new_cves if c.get("kev")]
    new_high = [c for c in new_cves if c["cvss"] >= 7.0]

    # Build report
    output = []
    output.append(f"☀️ **OVERNIGHT THREAT SCAN — {today_display}**")
    output.append(f"📋 Draft from last night: {'✅ Ready' if draft_exists else '❌ Not found'}")
    output.append(f"🕐 Draft generated: {generated_at}")
    output.append("")

    if new_critical or new_kev:
        output.append("🚨 **BREAKING — New overnight threats detected:**")
        for c in new_critical + [c for c in new_kev if c not in new_critical]:
            sev = "🔴 CRITICAL" if c["cvss"] >= 9.0 else "🟠 HIGH"
            kev = " ⚠️ KEV" if c.get("kev") else ""
            output.append(f"  🆕 {c['cve_id']} ({c['cvss']}) — {c['product']}{kev} {sev}")
            if c.get("description"):
                output.append(f"     {c['description'][:120]}")
        output.append("")
        output.append("⚠️ **Consider updating the script to include these.**")
    elif new_high:
        output.append("📡 **New HIGH severity CVEs overnight (not in draft):**")
        for c in new_high[:5]:
            output.append(f"  🆕 {c['cve_id']} ({c['cvss']}) — {c['product']}")
        output.append("")
        output.append("ℹ️ Nothing critical enough to require a script rewrite.")
    else:
        output.append("✅ **No significant new threats overnight.** Draft looks good as-is.")

    output.append("")
    output.append("---")
    output.append("")

    if draft_exists:
        word_count = len(draft_path.read_text().split())
        output.append(f"📄 Draft: {word_count} words, ready to publish")
        output.append("")
        output.append("**Actions:**")
        output.append("• Say **'publish daily threat'** to generate video and upload")
        output.append("• Send edits to the script and I'll update before publishing")
        output.append("• Say **'rewrite daily threat'** to regenerate the script from scratch with fresh CVEs")
    else:
        output.append("⚠️ No draft found. Say **'generate daily threat'** to create one now.")

    print("\n".join(output))
    return {
        "new_cves": len(new_cves),
        "new_critical": len(new_critical),
        "new_kev": len(new_kev),
        "draft_exists": draft_exists,
    }


if __name__ == "__main__":
    overnight_scan()
