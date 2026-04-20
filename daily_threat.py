#!/usr/bin/env python3
"""
Daily Threat — A noir-style cybersecurity podcast generator.
Fetches real CVE data, writes a hard-boiled detective script, and generates audio.

This is a backwards-compatible wrapper around the modular pipeline:
  config.py  — Central configuration
  fetcher.py — CVE data fetching
  writer.py  — Script generation via LLM
  audio.py   — TTS audio generation with chunking
"""

import json
import logging
from datetime import datetime

from config import EPISODES_DIR
from fetcher import fetch_cves
from writer import generate_script
from audio import generate_audio

# Re-export for backwards compatibility
fetch_threat_data = fetch_cves

TODAY = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("daily-threat")


def generate_episode():
    """Main entry point: fetch data, generate script, produce audio, save outputs."""
    log.info(f"=== Daily Threat — {TODAY} ===")

    # Fetch CVEs
    cves = fetch_cves()
    log.info(f"Collected {len(cves)} CVEs for today's episode.")

    # Generate script
    script = generate_script(cves)

    # File paths
    audio_path = EPISODES_DIR / f"daily-threat-{TODAY}.mp3"
    text_path = EPISODES_DIR / f"daily-threat-{TODAY}.txt"
    meta_path = EPISODES_DIR / f"daily-threat-{TODAY}.json"

    # Save text script
    text_path.write_text(script, encoding="utf-8")
    log.info(f"Script saved: {text_path}")

    # Generate audio
    audio_result = generate_audio(script, audio_path)

    # Word count and duration estimate (~150 wpm reading speed)
    word_count = len(script.split())
    duration_estimate = round(word_count / 150 * 60)  # seconds

    # Save metadata
    metadata = {
        "date": TODAY,
        "cves_covered": [c["cve_id"] for c in cves],
        "script_word_count": word_count,
        "audio_path": str(audio_result) if audio_result else str(text_path),
        "duration_estimate": f"{duration_estimate}s (~{duration_estimate // 60}m {duration_estimate % 60}s)",
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log.info(f"Metadata saved: {meta_path}")

    # Print output
    print("\n" + "=" * 60)
    print("DAILY THREAT — NOIR CYBERSECURITY BRIEFING")
    print("=" * 60)
    print(script)
    print("=" * 60)
    print(f"\n📄 Script: {text_path}")
    if audio_result:
        print(f"🎙️  Audio: {audio_result}")
    else:
        print("🎙️  Audio: not generated (no API key or error)")
    print(f"📊 Metadata: {meta_path}")
    print(f"📏 Words: {word_count} | Est. duration: {metadata['duration_estimate']}")

    return {
        "script": script,
        "audio_path": str(audio_result) if audio_result else None,
        "text_path": str(text_path),
        "metadata": metadata,
    }


if __name__ == "__main__":
    generate_episode()
