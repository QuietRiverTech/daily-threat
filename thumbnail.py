"""
Daily Threat - Thumbnail Generator
Produces eye-catching YouTube thumbnails with CRT noir aesthetic.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import BG_COLOR, GREEN, AMBER, RED, WHITE


THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a monospace font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
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


def _create_scanline_overlay(width: int, height: int, alpha: int = 20) -> Image.Image:
    """Create CRT scanline overlay."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, height, 4):
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha), width=1)
    return overlay


def generate_thumbnail(date_str: str, cves: list[dict], output_path: Path) -> Path:
    """
    Generate a 1280x720 YouTube thumbnail.

    Args:
        date_str: Date string (e.g. 'April 20, 2026')
        cves: List of CVE dicts with cve_id, cvss, product keys
        output_path: Where to save the thumbnail PNG

    Returns:
        Path to generated thumbnail
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Dramatic gradient/vignette effect
    for y in range(THUMB_HEIGHT):
        for x in range(0, THUMB_WIDTH, 4):
            # Subtle green grid pattern
            if (x % 80 == 0 or y % 80 == 0) and np.random.random() > 0.7:
                draw.point((x, y), fill=(0, 30, 10))

    # Title with glow
    title_font = _load_bold_font(82)
    title = "THE DAILY THREAT"

    # Glow layer
    glow = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), BG_COLOR)
    glow_draw = ImageDraw.Draw(glow)
    bbox = glow_draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (THUMB_WIDTH - tw) // 2
    ty = 60
    glow_draw.text((tx, ty), title, font=title_font, fill=GREEN)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=12))
    img = Image.blend(img, glow, 0.6)
    draw = ImageDraw.Draw(img)

    # Sharp title
    draw.text((tx, ty), title, font=title_font, fill=GREEN)

    # Date
    date_font = _load_font(32)
    bbox2 = draw.textbbox((0, 0), date_str, font=date_font)
    dw = bbox2[2] - bbox2[0]
    draw.text(((THUMB_WIDTH - dw) // 2, ty + 100), date_str, font=date_font, fill=WHITE)

    # Separator line
    draw.line([(100, ty + 155), (THUMB_WIDTH - 100, ty + 155)], fill=GREEN, width=2)

    # CVE entries (top 3)
    cve_font = _load_bold_font(44)
    badge_font = _load_bold_font(24)
    product_font = _load_font(24)

    display_cves = cves[:3] if cves else []
    cy = 260

    for cve in display_cves:
        cve_id = cve.get("cve_id", cve.get("id", "CVE-XXXX-XXXXX"))
        cvss = float(cve.get("cvss", cve.get("cvss_score", 0.0)))
        product = cve.get("product", cve.get("vendor", ""))

        # CVE ID
        draw.text((100, cy), cve_id, font=cve_font, fill=GREEN)

        # Severity badge
        if cvss >= 9.0:
            badge_text = "CRITICAL"
            badge_color = RED
        elif cvss >= 7.0:
            badge_text = "HIGH"
            badge_color = AMBER
        elif cvss >= 4.0:
            badge_text = "MEDIUM"
            badge_color = (255, 255, 0)
        else:
            badge_text = "LOW"
            badge_color = GREEN

        badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_w = badge_bbox[2] - badge_bbox[0] + 24
        badge_x = THUMB_WIDTH - 100 - badge_w
        draw.rounded_rectangle(
            [(badge_x, cy + 8), (badge_x + badge_w, cy + 44)],
            radius=6,
            fill=badge_color,
        )
        draw.text((badge_x + 12, cy + 12), badge_text, font=badge_font, fill=(0, 0, 0))

        # CVSS score next to badge
        score_text = f"{cvss:.1f}"
        score_font = _load_bold_font(36)
        draw.text((badge_x - 80, cy + 8), score_text, font=score_font, fill=badge_color)

        # Product name
        if product:
            draw.text((120, cy + 55), product[:40], font=product_font, fill=(180, 180, 180))

        cy += 110

    # If no CVEs, show placeholder text
    if not display_cves:
        no_cve_font = _load_font(36)
        draw.text((100, 300), "Today's Critical Vulnerabilities", font=no_cve_font, fill=AMBER)

    # Bottom branding
    brand_font = _load_font(22)
    draw.text((100, THUMB_HEIGHT - 60), "QuietRiverTech", font=brand_font, fill=AMBER)
    draw.text(
        (THUMB_WIDTH - 300, THUMB_HEIGHT - 60),
        "DAILY THREAT INTEL",
        font=brand_font,
        fill=GREEN,
    )

    # Scanline overlay
    scanlines = _create_scanline_overlay(THUMB_WIDTH, THUMB_HEIGHT, alpha=22)
    img = Image.alpha_composite(img.convert("RGBA"), scanlines).convert("RGB")

    # Vignette effect (darken edges)
    vignette = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    vig_draw = ImageDraw.Draw(vignette)
    for i in range(60):
        alpha = int(3.5 * (60 - i))
        vig_draw.rectangle(
            [(i, i), (THUMB_WIDTH - i, THUMB_HEIGHT - i)],
            outline=(0, 0, 0, alpha),
        )
    img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    img.save(str(output_path), quality=95)
    return output_path


if __name__ == "__main__":
    # Quick test
    test_cves = [
        {"cve_id": "CVE-2026-1234", "cvss": 9.8, "product": "Apache HTTP Server"},
        {"cve_id": "CVE-2026-5678", "cvss": 7.5, "product": "OpenSSL"},
        {"cve_id": "CVE-2026-9012", "cvss": 8.1, "product": "Linux Kernel"},
    ]
    result = generate_thumbnail(
        date_str="April 20, 2026",
        cves=test_cves,
        output_path=Path("test_thumbnail.png"),
    )
    print(f"Thumbnail generated: {result}")
