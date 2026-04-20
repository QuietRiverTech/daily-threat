"""
Daily Threat - Video Generation Engine
Produces YouTube-ready MP4 with CRT noir aesthetic from script + audio.
"""

import re
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

from config import BG_COLOR, GREEN, AMBER, RED, WHITE, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS as FPS


# --- Font Loading ---

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a monospace font, with fallbacks."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # Last resort: default font scaled
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _load_bold_font(size: int) -> ImageFont.FreeTypeFont:
    """Load bold monospace font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return _load_font(size)


# --- Scanline Overlay ---

def _create_scanline_overlay(width: int, height: int, alpha: int = 30) -> Image.Image:
    """Create a CRT scanline overlay image."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, height, 3):
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha), width=1)
    return overlay


# --- Title Card ---

def _render_title_card(date_str: str) -> Image.Image:
    """Render the title card frame."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title glow effect - draw blurred green text behind
    title_font = _load_bold_font(96)
    subtitle_font = _load_font(42)
    small_font = _load_font(36)

    title = "THE DAILY THREAT"

    # Glow layer
    glow = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    glow_draw = ImageDraw.Draw(glow)
    bbox = glow_draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (VIDEO_WIDTH - tw) // 2
    ty = VIDEO_HEIGHT // 2 - 120
    glow_draw.text((tx, ty), title, font=title_font, fill=GREEN)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))

    # Composite glow
    img = Image.blend(img, glow, 0.5)
    draw = ImageDraw.Draw(img)

    # Sharp title on top
    draw.text((tx, ty), title, font=title_font, fill=GREEN)

    # Date subtitle
    bbox2 = draw.textbbox((0, 0), date_str, font=subtitle_font)
    dw = bbox2[2] - bbox2[0]
    draw.text(((VIDEO_WIDTH - dw) // 2, ty + 130), date_str, font=subtitle_font, fill=WHITE)

    # "with Jack Cipher"
    byline = "with Jack Cipher"
    bbox3 = draw.textbbox((0, 0), byline, font=small_font)
    bw = bbox3[2] - bbox3[0]
    draw.text(((VIDEO_WIDTH - bw) // 2, ty + 190), byline, font=small_font, fill=AMBER)

    # Scanlines
    scanlines = _create_scanline_overlay(VIDEO_WIDTH, VIDEO_HEIGHT, alpha=25)
    img.paste(Image.alpha_composite(img.convert("RGBA"), scanlines).convert("RGB"))

    return img


# --- Outro Card ---

def _render_outro_card() -> Image.Image:
    """Render the outro frame."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _load_bold_font(64)
    sub_font = _load_font(36)
    brand_font = _load_font(30)

    # Main text
    main_text = "STAY PATCHED. STAY VIGILANT."
    bbox = draw.textbbox((0, 0), main_text, font=title_font)
    tw = bbox[2] - bbox[0]
    ty = VIDEO_HEIGHT // 2 - 80
    draw.text(((VIDEO_WIDTH - tw) // 2, ty), main_text, font=title_font, fill=GREEN)

    # Subscribe
    sub_text = "Subscribe for daily threat intel"
    bbox2 = draw.textbbox((0, 0), sub_text, font=sub_font)
    sw = bbox2[2] - bbox2[0]
    draw.text(((VIDEO_WIDTH - sw) // 2, ty + 100), sub_text, font=sub_font, fill=WHITE)

    # Branding
    brand = "QuietRiverTech"
    bbox3 = draw.textbbox((0, 0), brand, font=brand_font)
    bw = bbox3[2] - bbox3[0]
    draw.text(((VIDEO_WIDTH - bw) // 2, ty + 170), brand, font=brand_font, fill=AMBER)

    # Scanlines
    scanlines = _create_scanline_overlay(VIDEO_WIDTH, VIDEO_HEIGHT, alpha=25)
    img.paste(Image.alpha_composite(img.convert("RGBA"), scanlines).convert("RGB"))

    return img


# --- Main Content Frames ---

def _parse_paragraphs(script_text: str) -> list[str]:
    """Split script into paragraphs (non-empty lines)."""
    paragraphs = []
    current = []
    for line in script_text.split("\n"):
        stripped = line.strip()
        if stripped == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return [p for p in paragraphs if p]


def _find_cve_for_paragraph(paragraph: str, cves: list[dict]) -> Optional[dict]:
    """Find the CVE data dict matching a paragraph mention."""
    matches = re.findall(r"CVE-\d{4}-\d+", paragraph)
    if not matches:
        return None
    cve_id = matches[0]
    for cve in cves:
        if cve.get("cve_id", "") == cve_id or cve.get("id", "") == cve_id:
            return cve
    return None


def _severity_color(score: float) -> tuple:
    """Return color based on CVSS score."""
    if score >= 9.0:
        return RED
    elif score >= 7.0:
        return AMBER
    elif score >= 4.0:
        return (255, 255, 0)
    return GREEN


def _render_main_frame(
    paragraph: str,
    cve_data: Optional[dict],
    date_str: str,
    waveform_amplitude: float = 0.0,
    scanline_offset: int = 0,
) -> Image.Image:
    """Render a single main content frame."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Top bar ---
    top_bar_y = 40
    logo_font = _load_bold_font(28)
    date_font = _load_font(24)
    draw.text((40, top_bar_y), "THE DAILY THREAT", font=logo_font, fill=GREEN)
    bbox = draw.textbbox((0, 0), date_str, font=date_font)
    dw = bbox[2] - bbox[0]
    draw.text((VIDEO_WIDTH - dw - 40, top_bar_y + 4), date_str, font=date_font, fill=WHITE)
    draw.line([(40, top_bar_y + 45), (VIDEO_WIDTH - 40, top_bar_y + 45)], fill=GREEN, width=1)

    # --- Left side: paragraph text (60% width) ---
    text_area_x = 60
    text_area_y = 130
    text_area_w = int(VIDEO_WIDTH * 0.57) - 80
    text_font = _load_font(28)

    # Wrap text to fit
    wrapped = textwrap.fill(paragraph, width=52)
    lines = wrapped.split("\n")
    line_height = 38
    for i, line in enumerate(lines):
        y = text_area_y + i * line_height
        if y > VIDEO_HEIGHT - 160:
            break
        draw.text((text_area_x, y), line, font=text_font, fill=GREEN)

    # --- Right side: CVE info card (40% width) ---
    card_x = int(VIDEO_WIDTH * 0.60)
    card_y = 130
    card_w = VIDEO_WIDTH - card_x - 40
    card_h = 500

    if cve_data:
        # Card background
        draw.rounded_rectangle(
            [(card_x, card_y), (card_x + card_w, card_y + card_h)],
            radius=12,
            fill=(20, 20, 30),
            outline=GREEN,
            width=2,
        )

        cve_font = _load_bold_font(32)
        info_font = _load_font(24)
        small_font = _load_font(20)

        cy = card_y + 25
        cve_id = cve_data.get("cve_id", cve_data.get("id", "CVE-XXXX-XXXXX"))
        draw.text((card_x + 20, cy), cve_id, font=cve_font, fill=GREEN)
        cy += 50

        # Product
        product = cve_data.get("product", cve_data.get("vendor", "Unknown Product"))
        if product:
            draw.text((card_x + 20, cy), f"Product: {product[:28]}", font=info_font, fill=WHITE)
            cy += 40

        # CVSS Score
        cvss = cve_data.get("cvss", cve_data.get("cvss_score", 0.0))
        if cvss:
            score = float(cvss)
            color = _severity_color(score)
            draw.text((card_x + 20, cy), f"CVSS: {score:.1f}", font=info_font, fill=color)
            cy += 35

            # Severity bar
            bar_x = card_x + 20
            bar_w = card_w - 40
            draw.rounded_rectangle(
                [(bar_x, cy), (bar_x + bar_w, cy + 16)],
                radius=4,
                fill=(40, 40, 50),
            )
            fill_w = int(bar_w * (score / 10.0))
            if fill_w > 0:
                draw.rounded_rectangle(
                    [(bar_x, cy), (bar_x + fill_w, cy + 16)],
                    radius=4,
                    fill=color,
                )
            cy += 35

            # Severity label
            if score >= 9.0:
                sev_label = "CRITICAL"
            elif score >= 7.0:
                sev_label = "HIGH"
            elif score >= 4.0:
                sev_label = "MEDIUM"
            else:
                sev_label = "LOW"
            draw.text((card_x + 20, cy), sev_label, font=_load_bold_font(22), fill=color)
            cy += 40

        # EPSS
        epss = cve_data.get("epss", cve_data.get("epss_score", None))
        if epss is not None:
            epss_val = float(epss)
            draw.text(
                (card_x + 20, cy),
                f"EPSS: {epss_val:.1%}",
                font=info_font,
                fill=AMBER,
            )
            cy += 40

        # KEV badge
        kev = cve_data.get("kev", cve_data.get("in_kev", False))
        if kev:
            badge_y = cy + 10
            draw.rounded_rectangle(
                [(card_x + 20, badge_y), (card_x + 200, badge_y + 36)],
                radius=6,
                fill=RED,
            )
            draw.text(
                (card_x + 35, badge_y + 6),
                "⚠ KNOWN EXPLOITED",
                font=small_font,
                fill=WHITE,
            )

    # --- Bottom: Waveform visualization ---
    wave_y = VIDEO_HEIGHT - 80
    wave_h = 40
    bar_count = 80
    bar_width = (VIDEO_WIDTH - 120) // bar_count

    for i in range(bar_count):
        # Create pseudo-random bar heights based on amplitude
        seed_val = (i * 7 + scanline_offset) % 100
        noise = (np.sin(seed_val * 0.3) * 0.5 + 0.5)
        h = int(wave_h * waveform_amplitude * noise)
        if h < 2:
            h = 2
        x = 60 + i * bar_width
        bar_color = GREEN if h > 5 else (0, 100, 30)
        draw.rectangle(
            [(x, wave_y - h), (x + bar_width - 2, wave_y)],
            fill=bar_color,
        )

    # --- Animated scanlines ---
    scanlines = _create_scanline_overlay(VIDEO_WIDTH, VIDEO_HEIGHT, alpha=18)
    img = Image.alpha_composite(img.convert("RGBA"), scanlines).convert("RGB")

    return img


# --- Audio Waveform Processing ---

def _get_audio_amplitudes(audio_path: Path, fps: int, duration: float) -> np.ndarray:
    """Extract per-frame amplitude from audio file."""
    try:
        audio_clip = AudioFileClip(str(audio_path))
        n_frames = int(duration * fps)
        amplitudes = np.zeros(n_frames)
        samples_per_frame = int(audio_clip.fps / fps)

        for i in range(n_frames):
            t = i / fps
            try:
                chunk = audio_clip.get_frame(t)
                amplitudes[i] = np.abs(chunk).mean()
            except Exception:
                amplitudes[i] = 0.0

        # Normalize
        max_amp = amplitudes.max()
        if max_amp > 0:
            amplitudes = amplitudes / max_amp
        audio_clip.close()
        return amplitudes
    except Exception:
        return np.ones(int(duration * fps)) * 0.3


# --- Main Video Generation ---

def generate_video(
    script_text: str,
    audio_path: Path,
    output_path: Path,
    date_str: str,
    cves: list[dict],
) -> Path:
    """
    Generate a YouTube-ready MP4 video with CRT noir aesthetic.

    Args:
        script_text: The narration script text
        audio_path: Path to the narration audio file
        output_path: Where to save the final MP4
        date_str: Date string for display (e.g. 'April 20, 2026')
        cves: List of CVE data dicts with keys like cve_id, product, cvss, epss, kev

    Returns:
        Path to the generated video file
    """
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load audio to get duration
    audio_clip = AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration

    # Parse paragraphs and calculate timing
    paragraphs = _parse_paragraphs(script_text)
    if not paragraphs:
        paragraphs = ["[No script content]"]

    # Calculate timing per paragraph based on word count
    word_counts = [len(p.split()) for p in paragraphs]
    total_words = sum(word_counts)
    if total_words == 0:
        total_words = 1

    paragraph_durations = [(wc / total_words) * audio_duration for wc in word_counts]
    paragraph_starts = []
    t = 0.0
    for dur in paragraph_durations:
        paragraph_starts.append(t)
        t += dur

    # Find CVE data for each paragraph
    paragraph_cves = [_find_cve_for_paragraph(p, cves) for p in paragraphs]

    # Get audio amplitudes for waveform visualization
    amplitudes = _get_audio_amplitudes(audio_path, FPS, audio_duration)

    # --- Title Card (4 seconds) ---
    title_img = _render_title_card(date_str)
    title_array = np.array(title_img)
    title_clip = (
        ImageClip(title_array)
        .set_duration(4)
        .fadein(1.0)
        .fadeout(0.8)
    )

    # --- Main Content Clip ---
    # We use make_frame to render each frame dynamically
    def make_main_frame(t):
        """Generate frame for time t in the main content section."""
        # Determine which paragraph is active
        para_idx = 0
        for i, start in enumerate(paragraph_starts):
            if t >= start:
                para_idx = i

        paragraph = paragraphs[para_idx]
        cve_data = paragraph_cves[para_idx]

        # Get waveform amplitude for this frame
        frame_idx = int(t * FPS)
        if frame_idx < len(amplitudes):
            amp = amplitudes[frame_idx]
        else:
            amp = 0.0

        # Scanline animation offset
        scanline_offset = int(t * 10) % 100

        frame = _render_main_frame(
            paragraph=paragraph,
            cve_data=cve_data,
            date_str=date_str,
            waveform_amplitude=amp,
            scanline_offset=scanline_offset,
        )
        return np.array(frame)

    main_clip = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        color=BG_COLOR,
        duration=audio_duration,
    )
    main_clip = main_clip.fl(lambda gf, t: make_main_frame(t), apply_to=['mask'])
    # Actually, use VideoClip for custom frame generation
    from moviepy.video.VideoClip import VideoClip

    main_clip = VideoClip(make_main_frame, duration=audio_duration)
    main_clip = main_clip.set_fps(FPS)
    main_clip = main_clip.set_audio(audio_clip)

    # --- Outro (5 seconds) ---
    outro_img = _render_outro_card()
    outro_array = np.array(outro_img)
    outro_clip = (
        ImageClip(outro_array)
        .set_duration(5)
        .fadein(0.8)
        .fadeout(1.0)
    )

    # --- Concatenate all sections ---
    final = concatenate_videoclips([title_clip, main_clip, outro_clip], method="compose")

    # --- Write output ---
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="4000k",
        audio_bitrate="192k",
        threads=4,
        logger="bar",
    )

    # Cleanup
    audio_clip.close()
    final.close()

    return output_path


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) >= 3:
        script_file = Path(sys.argv[1])
        audio_file = Path(sys.argv[2])
        output = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("output.mp4")

        script = script_file.read_text()
        result = generate_video(
            script_text=script,
            audio_path=audio_file,
            output_path=output,
            date_str="April 20, 2026",
            cves=[],
        )
        print(f"Video generated: {result}")
    else:
        print("Usage: python video.py <script.txt> <audio.mp3> [output.mp4]")
