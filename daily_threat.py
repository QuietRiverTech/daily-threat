#!/usr/bin/env python3
"""
Daily Threat — A noir-style cybersecurity podcast generator.
Fetches real CVE data, writes a hard-boiled detective script, and generates audio.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
EPISODES_DIR = BASE_DIR / "episodes"
EPISODES_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("daily-threat")

# ---------------------------------------------------------------------------
# Environment / API Keys
# ---------------------------------------------------------------------------


def _load_env():
    """Load environment variables from ~/.hermes/.env"""
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            # Manual parse if python-dotenv not installed
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value:
                        os.environ.setdefault(key, value)


_load_env()


def _get_openrouter_key():
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OR_API_KEY") or ""


def _get_elevenlabs_key():
    return os.environ.get("ELEVENLABS_API_KEY") or ""


# ---------------------------------------------------------------------------
# Step 1: Fetch Threat Data
# ---------------------------------------------------------------------------

SHODAN_KEV_URL = "https://cvedb.shodan.io/cves?is_kev=true&sort_by_epss=true&limit=10"
SHODAN_NEW_URL = f"https://cvedb.shodan.io/cves?sort_by_epss=true&limit=15&start_date={YESTERDAY}T00:00:00"


def _parse_cves(data):
    """Parse CVE entries from Shodan CVEDB response."""
    cves = []
    for item in data.get("cves", []):
        cves.append({
            "cve_id": item.get("cve_id", "UNKNOWN"),
            "cvss": item.get("cvss", item.get("cvss_v2", 0)) or 0,
            "epss": item.get("epss", 0) or 0,
            "product": item.get("product", "unknown"),
            "vendor": item.get("vendor", "unknown"),
            "description": (item.get("summary") or item.get("description") or "No description")[:200],
            "kev": item.get("kev", False),
        })
    return cves


def fetch_threat_data():
    """Fetch CVE data from Shodan CVEDB. Falls back to simulated data."""
    all_cves = []
    try:
        log.info("Fetching KEV entries from Shodan CVEDB...")
        r = requests.get(SHODAN_KEV_URL, timeout=15)
        r.raise_for_status()
        all_cves.extend(_parse_cves(r.json()))
    except Exception as e:
        log.warning(f"KEV fetch failed: {e}")

    try:
        log.info("Fetching newest CVEs from Shodan CVEDB...")
        r = requests.get(SHODAN_NEW_URL, timeout=15)
        r.raise_for_status()
        new_cves = _parse_cves(r.json())
        # Deduplicate
        existing_ids = {c["cve_id"] for c in all_cves}
        for c in new_cves:
            if c["cve_id"] not in existing_ids:
                all_cves.append(c)
                existing_ids.add(c["cve_id"])
    except Exception as e:
        log.warning(f"New CVE fetch failed: {e}")

    if not all_cves:
        log.warning("Using simulated fallback data.")
        all_cves = _simulated_data()

    # Sort by EPSS descending, take top 8
    all_cves.sort(key=lambda x: x["epss"], reverse=True)
    return all_cves[:8]


def _simulated_data():
    """Fallback simulated CVE data."""
    return [
        {"cve_id": "CVE-2024-99001", "cvss": 9.8, "epss": 0.97, "product": "Apache HTTP Server", "vendor": "Apache", "description": "Remote code execution via crafted request headers", "kev": True},
        {"cve_id": "CVE-2024-99002", "cvss": 8.1, "epss": 0.85, "product": "Windows SMB", "vendor": "Microsoft", "description": "Privilege escalation through SMB protocol flaw", "kev": True},
        {"cve_id": "CVE-2024-99003", "cvss": 7.5, "epss": 0.62, "product": "OpenSSL", "vendor": "OpenSSL", "description": "Buffer overflow in certificate parsing", "kev": False},
        {"cve_id": "CVE-2024-99004", "cvss": 6.5, "epss": 0.45, "product": "Chrome V8", "vendor": "Google", "description": "Type confusion in JavaScript engine", "kev": False},
        {"cve_id": "CVE-2024-99005", "cvss": 9.1, "epss": 0.91, "product": "Confluence", "vendor": "Atlassian", "description": "Authentication bypass allowing remote admin access", "kev": True},
    ]


# ---------------------------------------------------------------------------
# Step 2: Generate Noir Script via OpenRouter
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a hard-boiled noir detective narrator from a 1940s radio drama. You investigate cybersecurity threats like crime scenes. Your name is Jack Cipher.

Style rules:
- Measured, deliberate pacing. Let sentences breathe. Pauses between thoughts.
- Noir metaphors and rain-soaked city imagery, but don't sacrifice clarity for style.
- Each CVE is a 'case' or 'crime scene' you're investigating
- Critical CVEs are 'murders', high are 'armed robberies', medium are 'break-ins'
- KEV entries are 'repeat offenders caught in the act'
- EPSS scores are your 'informant's tip on how likely this perp strikes again'
- Always open with setting the scene (time, weather, city)
- Always close with a sign-off catchphrase

IMPORTANT — For each CVE, provide CONTEXT that a security professional would appreciate:
- What the vulnerability actually DOES in plain terms (not just the CVE title)
- What kind of attacker would use this and why it matters
- What the real-world impact looks like (data breach, ransomware entry point, lateral movement, etc.)
- Who should be worried (what industries, what stack)
- Brief mention of mitigation if notable (patch available, workaround, etc.)

- Target length: 2.5 minutes when read aloud (~350 words)
- Cover 3 CVEs with solid context, not 5+ superficially
- Make it entertaining AND genuinely educational — listeners should walk away understanding the threats
- Mention real CVE IDs, products, CVSS scores, and EPSS probabilities"""


def _format_cve_data(cves):
    """Format CVE data for the LLM prompt."""
    lines = [f"Today's date: {TODAY}\n\nCVE Intelligence Report:\n"]
    for i, c in enumerate(cves, 1):
        sev = "CRITICAL" if c["cvss"] >= 9.0 else "HIGH" if c["cvss"] >= 7.0 else "MEDIUM"
        lines.append(
            f"{i}. {c['cve_id']} | Severity: {sev} (CVSS {c['cvss']}) | "
            f"EPSS: {c['epss']:.2f} | Product: {c['product']} ({c['vendor']}) | "
            f"KEV: {'YES' if c['kev'] else 'No'}\n"
            f"   Description: {c['description']}\n"
        )
    lines.append("\nWrite the noir podcast script for today's episode covering these threats.")
    return "\n".join(lines)


def generate_script(cves):
    """Generate noir script using OpenRouter API."""
    api_key = _get_openrouter_key()
    if not api_key:
        log.error("No OpenRouter API key found. Cannot generate script.")
        return _fallback_script(cves)

    user_prompt = _format_cve_data(cves)

    try:
        log.info("Generating noir script via OpenRouter...")
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1024,
                "temperature": 0.85,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        script = data["choices"][0]["message"]["content"]
        log.info("Script generated successfully.")
        return script.strip()
    except Exception as e:
        log.error(f"OpenRouter call failed: {e}")
        return _fallback_script(cves)


def _fallback_script(cves):
    """Simple fallback script when LLM is unavailable."""
    top = cves[0] if cves else {"cve_id": "CVE-XXXX-XXXXX", "cvss": 0, "epss": 0, "product": "Unknown"}
    return (
        f"The rain hammered the neon-lit streets as I pulled up today's case files.\n\n"
        f"Top of the stack: {top['cve_id']}. CVSS {top['cvss']}. "
        f"My informants say there's a {top['epss']:.0%} chance this one hits again. "
        f"The product? {top['product']}. A real nasty piece of work.\n\n"
        f"I've got {len(cves)} cases on my desk tonight. The city never sleeps, "
        f"and neither do the threat actors.\n\n"
        f"Stay patched, stay paranoid. This is Jack Cipher, signing off."
    )


# ---------------------------------------------------------------------------
# Step 3: Generate Audio via ElevenLabs
# ---------------------------------------------------------------------------

ELEVENLABS_VOICE_ID = "oNewkOzghH74whuAIBh0"
ELEVENLABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"


def generate_audio(script_text, output_path):
    """Generate MP3 audio from script text using ElevenLabs API."""
    api_key = _get_elevenlabs_key()
    if not api_key:
        log.warning("No ElevenLabs API key. Skipping audio generation.")
        return None

    try:
        log.info("Generating audio via ElevenLabs...")
        r = requests.post(
            ELEVENLABS_TTS_URL,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": script_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.85,
                    "similarity_boost": 0.80,
                    "style": 0.15,
                    "speed": 0.90,
                },
            },
            timeout=120,
        )
        r.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(r.content)
        log.info(f"Audio saved: {output_path}")
        return str(output_path)
    except Exception as e:
        log.error(f"ElevenLabs TTS failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 4: Output & Metadata
# ---------------------------------------------------------------------------


def generate_episode():
    """Main entry point: fetch data, generate script, produce audio, save outputs."""
    log.info(f"=== Daily Threat — {TODAY} ===")

    # Fetch CVEs
    cves = fetch_threat_data()
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
        "audio_path": audio_result or str(text_path),
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
        "audio_path": audio_result,
        "text_path": str(text_path),
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate_episode()
