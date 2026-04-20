"""CVE fetching module for Daily Threat pipeline."""

import logging
from datetime import datetime, timedelta

import requests

from config import MAX_CVES

log = logging.getLogger("daily-threat.fetcher")

YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

SHODAN_KEV_URL = "https://cvedb.shodan.io/cves?is_kev=true&sort_by_epss=true&limit=10"
SHODAN_NEW_URL = f"https://cvedb.shodan.io/cves?sort_by_epss=true&limit=15&start_date={YESTERDAY}T00:00:00"


def _parse_cves(data: dict) -> list[dict]:
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


def _simulated_data() -> list[dict]:
    """Fallback simulated CVE data."""
    return [
        {"cve_id": "CVE-2024-99001", "cvss": 9.8, "epss": 0.97, "product": "Apache HTTP Server", "vendor": "Apache", "description": "Remote code execution via crafted request headers", "kev": True},
        {"cve_id": "CVE-2024-99002", "cvss": 8.1, "epss": 0.85, "product": "Windows SMB", "vendor": "Microsoft", "description": "Privilege escalation through SMB protocol flaw", "kev": True},
        {"cve_id": "CVE-2024-99003", "cvss": 7.5, "epss": 0.62, "product": "OpenSSL", "vendor": "OpenSSL", "description": "Buffer overflow in certificate parsing", "kev": False},
        {"cve_id": "CVE-2024-99004", "cvss": 6.5, "epss": 0.45, "product": "Chrome V8", "vendor": "Google", "description": "Type confusion in JavaScript engine", "kev": False},
        {"cve_id": "CVE-2024-99005", "cvss": 9.1, "epss": 0.91, "product": "Confluence", "vendor": "Atlassian", "description": "Authentication bypass allowing remote admin access", "kev": True},
    ]


def fetch_cves() -> list[dict]:
    """Fetch CVE data from Shodan CVEDB. Falls back to simulated data.

    Returns a list of CVE dicts with keys:
        cve_id, cvss, epss, product, vendor, description, kev
    """
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

    # Sort by EPSS descending, take top MAX_CVES
    all_cves.sort(key=lambda x: x["epss"], reverse=True)
    return all_cves[:MAX_CVES]
