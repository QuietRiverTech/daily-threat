#!/usr/bin/env python3
"""
The Daily Threat — Full YouTube Pipeline
Fetch CVEs → Write noir script → Generate audio → Render video → Create thumbnail → Upload to YouTube
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import EPISODES_DIR
from fetcher import fetch_cves
from writer import generate_script
from audio import generate_audio
from video import generate_video
from thumbnail import generate_thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def run_pipeline(upload=False, notify=False):
    """Run the full Daily Threat pipeline."""
    today = datetime.now().strftime("%Y-%m-%d")
    date_display = datetime.now().strftime("%B %d, %Y")
    
    log.info(f"{'='*60}")
    log.info(f"THE DAILY THREAT — {date_display}")
    log.info(f"{'='*60}")
    
    # Output paths
    base = EPISODES_DIR / f"daily-threat-{today}"
    script_path = base.with_suffix(".txt")
    audio_path = base.with_suffix(".mp3")
    video_path = base.with_suffix(".mp4")
    thumb_path = EPISODES_DIR / f"daily-threat-{today}-thumb.png"
    meta_path = base.with_suffix(".json")
    
    # --- PHASE 1: Fetch threat data ---
    log.info("PHASE 1: Fetching threat intelligence...")
    cves = fetch_cves()
    log.info(f"  → {len(cves)} CVEs collected")
    
    # --- PHASE 2: Generate noir script ---
    log.info("PHASE 2: Generating noir script...")
    script = generate_script(cves)
    script_path.write_text(script)
    word_count = len(script.split())
    log.info(f"  → {word_count} words written to {script_path.name}")
    
    # --- PHASE 3: Generate audio ---
    log.info("PHASE 3: Generating voice narration (Jelf)...")
    result = generate_audio(script, audio_path)
    if result is None:
        log.error("  → Audio generation failed. Stopping pipeline.")
        return None
    log.info(f"  → Audio saved: {audio_path.name}")
    
    # --- PHASE 4: Generate video ---
    log.info("PHASE 4: Rendering video...")
    try:
        generate_video(script, audio_path, video_path, date_display, cves)
        log.info(f"  → Video saved: {video_path.name}")
    except Exception as e:
        log.error(f"  → Video generation failed: {e}")
        video_path = None
    
    # --- PHASE 5: Generate thumbnail ---
    log.info("PHASE 5: Creating thumbnail...")
    try:
        generate_thumbnail(date_display, cves, thumb_path)
        log.info(f"  → Thumbnail saved: {thumb_path.name}")
    except Exception as e:
        log.error(f"  → Thumbnail generation failed: {e}")
        thumb_path = None
    
    # --- PHASE 6: Upload to YouTube ---
    video_id = None
    if upload and video_path and video_path.exists():
        log.info("PHASE 6: Uploading to YouTube...")
        try:
            from youtube import authenticate, upload_video, generate_metadata
            
            metadata = generate_metadata(date_display, cves, script)
            service = authenticate()
            video_id = upload_video(
                service=service,
                video_path=str(video_path),
                thumbnail_path=str(thumb_path) if thumb_path and thumb_path.exists() else None,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
            )
            log.info(f"  → Uploaded! https://youtube.com/watch?v={video_id}")
        except Exception as e:
            log.error(f"  → YouTube upload failed: {e}")
    elif upload:
        log.warning("  → Skipping upload (no video file)")
    else:
        log.info("PHASE 6: YouTube upload skipped (use --upload to enable)")
    
    # --- Save metadata ---
    meta = {
        "date": today,
        "date_display": date_display,
        "cves_covered": [c["cve_id"] for c in cves[:4]],
        "script_words": word_count,
        "script_path": str(script_path),
        "audio_path": str(audio_path) if audio_path.exists() else None,
        "video_path": str(video_path) if video_path and video_path.exists() else None,
        "thumbnail_path": str(thumb_path) if thumb_path and thumb_path.exists() else None,
        "youtube_id": video_id,
        "youtube_url": f"https://youtube.com/watch?v={video_id}" if video_id else None,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    
    # --- Summary ---
    log.info(f"\n{'='*60}")
    log.info("PIPELINE COMPLETE")
    log.info(f"{'='*60}")
    log.info(f"  📄 Script:    {script_path}")
    log.info(f"  🎙️  Audio:     {audio_path}")
    log.info(f"  🎬 Video:     {video_path}")
    log.info(f"  🖼️  Thumbnail: {thumb_path}")
    if video_id:
        log.info(f"  ▶️  YouTube:   https://youtube.com/watch?v={video_id}")
    log.info(f"  📏 Words: {word_count} | Est: ~{word_count * 60 // 150 // 60}m {(word_count * 60 // 150) % 60}s")
    
    return meta


if __name__ == "__main__":
    upload = "--upload" in sys.argv
    run_pipeline(upload=upload)
