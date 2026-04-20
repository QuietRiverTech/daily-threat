"""
YouTube upload module for The Daily Threat.
Uses YouTube Data API v3 for video uploads with OAuth2 authentication.
"""

import os
import json
import time
import httplib2
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Paths
BASE_DIR = Path(__file__).parent
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Retry config for resumable uploads
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def authenticate():
    """
    Authenticate with YouTube Data API v3 via OAuth2.

    - If token.json exists with a valid/refreshable token, uses it automatically.
    - Otherwise, runs the interactive OAuth2 consent flow.

    Returns:
        googleapiclient.discovery.Resource: Authenticated YouTube service object.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or re-authenticate if needed
    if creds and creds.expired and creds.refresh_token:
        print("[youtube] Refreshing expired token...")
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError(
                f"client_secret.json not found at {CLIENT_SECRET_FILE}. "
                "Download it from Google Cloud Console."
            )
        print("[youtube] No valid token found. Starting OAuth2 flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE), SCOPES
        )
        creds = flow.run_local_server(port=0)

    # Save token for future runs
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    service = build("youtube", "v3", credentials=creds)
    print("[youtube] Authenticated successfully.")
    return service


def upload_video(
    video_path,
    thumbnail_path,
    title,
    description,
    tags,
    category="28",
    privacy="public",
):
    """
    Upload a video to YouTube with metadata and thumbnail.

    Args:
        video_path: Path to the video file.
        thumbnail_path: Path to the thumbnail image.
        title: Video title.
        description: Video description.
        tags: List of tags.
        category: YouTube category ID (default '28' = Science & Technology).
        privacy: Privacy status ('public', 'unlisted', 'private').

    Returns:
        str: The uploaded video's YouTube ID.
    """
    youtube = authenticate()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print(f"[youtube] Uploading: {title}")
    video_id = _resumable_upload(request)

    # Set thumbnail
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"[youtube] Setting thumbnail from {thumbnail_path}")
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
            ).execute()
            print("[youtube] Thumbnail set successfully.")
        except HttpError as e:
            print(f"[youtube] Warning: Could not set thumbnail: {e}")

    print(f"[youtube] Upload complete! Video ID: {video_id}")
    print(f"[youtube] URL: https://youtu.be/{video_id}")
    return video_id


def _resumable_upload(request):
    """
    Execute a resumable upload with retry logic.

    Returns:
        str: Video ID from the completed upload.
    """
    response = None
    retries = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[youtube] Upload progress: {pct}%")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retries += 1
                if retries > MAX_RETRIES:
                    raise Exception(f"Upload failed after {MAX_RETRIES} retries.")
                wait = 2 ** retries
                print(f"[youtube] Retriable error {e.resp.status}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = 2 ** retries
            print(f"[youtube] Error: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    return response["id"]


def generate_metadata(date_str, cves, script_text):
    """
    Generate YouTube metadata (title, description, tags) for an episode.

    Args:
        date_str: Date string in 'YYYY-MM-DD' format.
        cves: List of CVE dicts, each with at least 'id' and optionally
              'product', 'vendor', 'summary'.
        script_text: The full narration script text.

    Returns:
        dict with keys: 'title', 'description', 'tags'
    """
    # Parse date
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = dt.strftime("%B %d, %Y").replace(" 0", " ")

    # --- Title ---
    top_cve_ids = [c["id"] for c in cves[:3]]
    cve_str = " | ".join(top_cve_ids) if top_cve_ids else "New Vulnerabilities"
    title = f"The Daily Threat | {formatted_date} | {cve_str}"
    # YouTube title max 100 chars
    if len(title) > 100:
        title = f"The Daily Threat | {formatted_date} | {top_cve_ids[0]}"
    if len(title) > 100:
        title = f"The Daily Threat | {formatted_date}"

    # --- Timestamps / Chapters ---
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    timestamps = _generate_chapters(paragraphs)

    # --- Description ---
    desc_parts = [
        f"🔒 The Daily Threat — {formatted_date}",
        "",
        script_text[:500] + ("..." if len(script_text) > 500 else ""),
        "",
        "📋 Timestamps:",
    ]
    for ts, label in timestamps:
        desc_parts.append(f"{ts} {label}")

    desc_parts.append("")
    desc_parts.append("🔗 CVE References:")
    for cve in cves:
        cve_id = cve["id"]
        summary = cve.get("summary", "")
        link = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        line = f"• {cve_id}: {link}"
        if summary:
            line += f" — {summary[:80]}"
        desc_parts.append(line)

    desc_parts.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📡 The Daily Threat by Jack Cipher",
        "Your noir-style daily cybersecurity briefing.",
        "New episodes every day.",
        "",
        "🔔 Subscribe for daily threat intelligence updates.",
        "#cybersecurity #CVE #threatintelligence #infosec #dailybriefing",
    ])

    description = "\n".join(desc_parts)
    # YouTube description max ~5000 chars
    if len(description) > 5000:
        description = description[:4990] + "\n..."

    # --- Tags ---
    base_tags = [
        "cybersecurity", "CVE", "threat intelligence", "daily briefing",
        "infosec", "hacking", "vulnerability", "CISA KEV",
        "Jack Cipher", "noir", "podcast",
    ]
    product_tags = []
    for cve in cves:
        for key in ("product", "vendor"):
            val = cve.get(key)
            if val and val.lower() not in [t.lower() for t in base_tags + product_tags]:
                product_tags.append(val)

    tags = base_tags + product_tags
    # YouTube allows up to 500 chars total for tags
    while sum(len(t) for t in tags) > 480 and product_tags:
        product_tags.pop()
        tags = base_tags + product_tags

    return {
        "title": title,
        "description": description,
        "tags": tags,
    }


def _generate_chapters(paragraphs):
    """
    Generate chapter timestamps from paragraphs.
    Estimates ~15 seconds per paragraph (rough narration pace).

    Returns:
        List of (timestamp_str, label) tuples.
    """
    chapters = [("0:00", "Introduction")]
    current_seconds = 0

    for i, para in enumerate(paragraphs):
        if i == 0:
            continue  # intro already covered

        # Estimate duration: ~150 words/min narration, avg ~2.5 sec per line
        word_count = len(para.split())
        duration = max(10, int(word_count / 150 * 60))
        current_seconds += duration

        minutes = current_seconds // 60
        seconds = current_seconds % 60
        ts = f"{minutes}:{seconds:02d}"

        # Try to extract a chapter label from the paragraph
        label = _extract_chapter_label(para, i)
        chapters.append((ts, label))

    return chapters


def _extract_chapter_label(paragraph, index):
    """Extract a short chapter label from a paragraph."""
    # Look for CVE IDs in the paragraph
    import re
    cve_match = re.search(r"CVE-\d{4}-\d{4,}", paragraph)
    if cve_match:
        return cve_match.group(0)

    # First sentence, truncated
    first_line = paragraph.split(".")[0].strip()
    if len(first_line) > 50:
        first_line = first_line[:47] + "..."
    return first_line if first_line else f"Segment {index}"
