"""Audio generation module for Daily Threat pipeline.

Handles text chunking and ElevenLabs TTS with pydub concatenation.
"""

import io
import logging
from pathlib import Path

import requests

from config import ELEVENLABS_API_KEY, VOICE_ID, TTS_MODEL, VOICE_SETTINGS

log = logging.getLogger("daily-threat.audio")

ELEVENLABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"


def _chunk_text(text: str, target_words: int = 350) -> list[str]:
    """Split text into chunks at paragraph breaks, targeting ~300-400 words each.

    If script is <= 400 words, return as single chunk.
    """
    words = text.split()
    if len(words) <= 400:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_word_count = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())

        # If adding this paragraph exceeds target and we have content, start new chunk
        if current_word_count + para_words > target_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_word_count = para_words
        else:
            current_chunk.append(para)
            current_word_count += para_words

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _generate_chunk_audio(text: str) -> bytes | None:
    """Generate audio bytes for a single text chunk via ElevenLabs."""
    try:
        r = requests.post(
            ELEVENLABS_TTS_URL,
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": TTS_MODEL,
                "voice_settings": VOICE_SETTINGS,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.content
    except Exception as e:
        log.error(f"ElevenLabs TTS chunk failed: {e}")
        return None


def generate_audio(script_text: str, output_path: Path) -> Path | None:
    """Generate MP3 audio from script text using ElevenLabs API with chunking.

    If script is > 400 words, splits at paragraph breaks into ~300-400 word chunks,
    generates audio for each separately, then concatenates with 0.5s silence gaps.

    Args:
        script_text: The full script text to convert to audio.
        output_path: Path where the final MP3 should be saved.

    Returns:
        The output path on success, None on failure.
    """
    if not ELEVENLABS_API_KEY:
        log.warning("No ElevenLabs API key. Skipping audio generation.")
        return None

    chunks = _chunk_text(script_text)
    log.info(f"Split script into {len(chunks)} audio chunk(s).")

    if len(chunks) == 1:
        # Single chunk — simple path, no pydub needed
        audio_data = _generate_chunk_audio(chunks[0])
        if not audio_data:
            return None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)
        log.info(f"Audio saved: {output_path}")
        return output_path

    # Multiple chunks — generate each and concatenate with pydub
    try:
        from pydub import AudioSegment
    except ImportError:
        log.error("pydub not installed. Falling back to single-chunk generation.")
        # Fallback: just generate the whole thing in one shot
        audio_data = _generate_chunk_audio(script_text)
        if not audio_data:
            return None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)
        log.info(f"Audio saved (single chunk fallback): {output_path}")
        return output_path

    # Generate audio for each chunk
    audio_segments = []
    silence = AudioSegment.silent(duration=500)  # 0.5s silence

    for i, chunk in enumerate(chunks):
        log.info(f"Generating audio chunk {i + 1}/{len(chunks)} ({len(chunk.split())} words)...")
        audio_data = _generate_chunk_audio(chunk)
        if audio_data is None:
            log.error(f"Failed on chunk {i + 1}. Aborting audio generation.")
            return None
        segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        audio_segments.append(segment)

    # Concatenate with silence gaps
    combined = audio_segments[0]
    for segment in audio_segments[1:]:
        combined = combined + silence + segment

    # Export
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(str(output_path), format="mp3")
    log.info(f"Audio saved (concatenated {len(chunks)} chunks): {output_path}")
    return output_path
