"""Script generation module for Daily Threat pipeline."""

import logging
from datetime import datetime

import requests

from config import OPENROUTER_API_KEY, LLM_MODEL, SCRIPT_TARGET_WORDS, MAX_CVES

log = logging.getLogger("daily-threat.writer")

TODAY = datetime.now().strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""You are a hard-boiled noir detective narrator from a 1940s radio drama. You investigate cybersecurity threats like crime scenes. Your name is Jack Cipher.

Style rules:
- Measured, deliberate pacing. Let sentences breathe. Pauses between thoughts.
- Noir metaphors and rain-soaked city imagery, but NEVER sacrifice clarity for style.
- Each CVE is a 'case' or 'crime scene' you're investigating
- Critical CVEs are 'murders', high are 'armed robberies', medium are 'break-ins'
- KEV entries are 'repeat offenders caught in the act'
- EPSS scores are your 'informant's tip on how likely this perp strikes again'

STRUCTURE (follow this precisely):
1. COLD OPEN (2 paragraphs): Set the scene — time, weather, city, mood. Establish that tonight's cases are heavy. Hint at what's coming.

2. CVE INVESTIGATIONS (2-3 paragraphs per CVE, cover {MAX_CVES} CVEs max):
   For EACH CVE, you MUST cover:
   - What the vulnerability actually DOES in plain English (not just the CVE title)
   - Who built the affected software and how widespread/popular it is
   - The attack vector described in noir terms (how the 'crime' is committed)
   - Real-world impact scenarios: ransomware entry point, espionage vector, lateral movement enabler, data exfiltration
   - Who should be panicking (what industries, what teams, what stack)
   - What to do about it (patch, workaround, mitigation)
   - Mention the CVE ID, CVSS score, and EPSS probability

3. TRANSITIONS between CVEs: Use noir transition phrases like:
   - 'But that wasn't the only body on the slab tonight...'
   - 'I barely had time to light another cigarette when the next file landed on my desk...'
   - 'The night was far from over...'

4. WRAP-UP AND SIGN-OFF (1-2 paragraphs): Tie together the night's themes, deliver actionable takeaway, sign off as Jack Cipher with a memorable closing line.

FORMATTING:
- Use explicit paragraph breaks (blank lines between paragraphs) — this is CRITICAL for audio chunking
- Target length: ~{SCRIPT_TARGET_WORDS} words (5-6 minutes when read aloud at natural pace)
- Prioritize CLARITY and EDUCATION over pure style — listeners should understand each threat deeply
- Make it entertaining AND genuinely educational
- Always mention real CVE IDs, products, CVSS scores, and EPSS probabilities"""


def _format_cve_data(cves: list[dict]) -> str:
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
    lines.append(f"\nWrite the noir podcast script for today's episode. Target ~{SCRIPT_TARGET_WORDS} words. Cover these threats with deep context and education.")
    return "\n".join(lines)


def _fallback_script(cves: list[dict]) -> str:
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


def generate_script(cves: list[dict]) -> str:
    """Generate noir script using OpenRouter API.

    Args:
        cves: List of CVE dicts from fetcher.fetch_cves()

    Returns:
        Generated script text.
    """
    if not OPENROUTER_API_KEY:
        log.error("No OpenRouter API key found. Cannot generate script.")
        return _fallback_script(cves)

    user_prompt = _format_cve_data(cves)

    try:
        log.info("Generating noir script via OpenRouter...")
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 2048,
                "temperature": 0.85,
            },
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        script = data["choices"][0]["message"]["content"]
        log.info(f"Script generated successfully ({len(script.split())} words).")
        return script.strip()
    except Exception as e:
        log.error(f"OpenRouter call failed: {e}")
        return _fallback_script(cves)
