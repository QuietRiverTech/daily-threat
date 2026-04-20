#!/usr/bin/env python3
"""
publish.py — Phase 3: Publish today's Daily Threat.
Takes the draft script, generates audio + video + thumbnail, uploads to YouTube.
Optionally accepts a custom script path or uses today's draft.
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import EPISODES_DIR
from audio import generate_audio
from video import generate_video
from thumbnail import generate_thumbnail
from youtube import upload_video, generate_metadata

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DRAFTS_DIR = EPISODES_DIR / "drafts"


def publish(script_override=None):
    """Generate audio, video, thumbnail from draft and upload to YouTube."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%B %d, %Y")

    # Load script
    if script_override:
        script = script_override
        log.info("Using provided script override")
    else:
        draft_path = DRAFTS_DIR / f"draft-{today}.txt"
        if not draft_path.exists():
            log.error(f"No draft found at {draft_path}")
            print(f"❌ No draft found for {today}. Run draft.py first or provide a script.")
            return None
        script = draft_path.read_text()
        log.info(f"Loaded draft from {draft_path}")

    # Load CVE data
    cve_path = DRAFTS_DIR / f"draft-{today}-cves.json"
    if cve_path.exists():
        cves = json.loads(cve_path.read_text()).get("cves", [])
    else:
        cves = []
        log.warning("No CVE data file found, proceeding without CVE metadata")

    word_count = len(script.split())
    log.info(f"Script: {word_count} words")

    # Output paths
    base = EPISODES_DIR / f"daily-threat-{today}"
    script_path = base.with_suffix(".txt")
    audio_path = base.with_suffix(".mp3")
    video_path = base.with_suffix(".mp4")
    thumb_path = EPISODES_DIR / f"daily-threat-{today}-thumb.png"
    meta_path = base.with_suffix(".json")

    # Save final script
    script_path.write_text(script)

    # Phase 3a: Audio
    log.info("🎙️ Generating voice narration...")
    result = generate_audio(script, audio_path)
    if result is None:
        print("❌ Audio generation failed.")
        return None
    log.info(f"Audio saved: {audio_path.name}")

    # Phase 3b: Video
    log.info("🎬 Rendering video...")
    try:
        generate_video(script, audio_path, video_path, today_display, cves)
        log.info(f"Video saved: {video_path.name}")
    except Exception as e:
        log.error(f"Video generation failed: {e}")
        print(f"❌ Video rendering failed: {e}")
        return None

    # Phase 3c: Thumbnail
    log.info("🖼️ Creating thumbnail...")
    try:
        generate_thumbnail(today_display, cves, thumb_path)
    except Exception as e:
        log.warning(f"Thumbnail failed: {e}")
        thumb_path = None

    # Phase 3d: Upload
    log.info("📤 Uploading to YouTube...")
    try:
        meta = generate_metadata(today_display, cves, script)
        vid_id = upload_video(
            video_path=str(video_path),
            thumbnail_path=str(thumb_path) if thumb_path and thumb_path.exists() else None,
            title=meta["title"],
            description=meta["description"],
            tags=meta["tags"],
        )
        youtube_url = f"https://youtu.be/{vid_id}"
        log.info(f"Uploaded! {youtube_url}")
    except Exception as e:
        log.error(f"YouTube upload failed: {e}")
        vid_id = None
        youtube_url = None

    # Save metadata
    meta_data = {
        "date": today,
        "cves_covered": [c.get("cve_id", c.get("id")) for c in cves[:4]],
        "script_words": word_count,
        "youtube_id": vid_id,
        "youtube_url": youtube_url,
    }
    meta_path.write_text(json.dumps(meta_data, indent=2))

    # Output summary
    output = []
    output.append(f"🎬 **DAILY THREAT PUBLISHED — {today_display}**")
    output.append("")
    if youtube_url:
        output.append(f"▶️ **{youtube_url}**")
    else:
        output.append("⚠️ YouTube upload failed — video saved locally")
    output.append("")
    output.append(f"📏 {word_count} words | 🔍 {len(cves)} CVEs")
    output.append(f"📄 Script: {script_path}")
    output.append(f"🎙️ Audio: {audio_path}")
    output.append(f"🎬 Video: {video_path}")
    if vid_id:
        output.append(f"📺 Title: {meta.get('title', 'N/A')}")

    print("\n".join(output))
    return vid_id


if __name__ == "__main__":
    publish()
