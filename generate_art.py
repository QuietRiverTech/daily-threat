#!/usr/bin/env python3
"""Generate YouTube channel art for The Daily Cyber Threat."""

import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(42)

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

GREEN = (0, 255, 65)
DIM_GREEN = (0, 180, 40)
DARK_GREEN = (0, 80, 20)
BG = (10, 10, 15)
AMBER = (255, 176, 0)
GRAY = (160, 160, 170)
DIM_GRAY = (100, 100, 110)


def make_banner():
    W, H = 2560, 1440
    safe_w, safe_h = 1546, 423
    safe_x = (W - safe_w) // 2
    safe_y = (H - safe_h) // 2

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # CRT scanlines
    for y in range(0, H, 3):
        draw.line([(0, y), (W, y)], fill=(0, 0, 0), width=1)

    # Matrix rain - hex characters at low opacity
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    hex_font = ImageFont.truetype(FONT_MONO, 14)
    hex_chars = "0123456789ABCDEF"
    
    for col in range(0, W, 20):
        length = random.randint(5, 30)
        start_y = random.randint(-200, H)
        for i in range(length):
            y = start_y + i * 18
            if 0 <= y < H:
                c = random.choice(hex_chars)
                alpha = max(8, 40 - i * 2)
                odraw.text((col, y), c, fill=(0, 255, 65, alpha), font=hex_font)

    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)

    # --- Draw safe area content ---
    draw = ImageDraw.Draw(img_rgba)

    # Title
    title = "THE DAILY CYBER THREAT"
    title_font = ImageFont.truetype(FONT_BOLD, 62)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = safe_y + 80

    # Glow effect - draw text multiple times with blur
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for offset in range(6, 0, -1):
        alpha = 30
        gdraw.text((tx, ty), title, fill=(0, 255, 65, alpha), font=title_font)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    img_rgba = Image.alpha_composite(img_rgba, glow)
    draw = ImageDraw.Draw(img_rgba)
    draw.text((tx, ty), title, fill=GREEN, font=title_font)

    # Green line separator above subtitle
    line_y = ty + th + 20
    line_margin = 300
    draw.line([(W//2 - line_margin, line_y), (W//2 + line_margin, line_y)], fill=DIM_GREEN, width=2)

    # Subtitle
    subtitle = "AI-Narrated Noir Cybersecurity Briefings | Daily CVE Intelligence"
    sub_font = ImageFont.truetype(FONT_MONO, 24)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = bbox[2] - bbox[0]
    sx = (W - sw) // 2
    sy = line_y + 12
    draw.text((sx, sy), subtitle, fill=GRAY, font=sub_font)

    # Green line separator below subtitle
    line_y2 = sy + 34
    draw.line([(W//2 - line_margin, line_y2), (W//2 + line_margin, line_y2)], fill=DIM_GREEN, width=2)

    # Powered by Jack Cipher
    pbc_font = ImageFont.truetype(FONT_MONO, 20)
    pbc = "Powered by Jack Cipher"
    bbox = draw.textbbox((0, 0), pbc, font=pbc_font)
    pw = bbox[2] - bbox[0]
    px = (W - pw) // 2
    py = safe_y + safe_h - 55
    draw.text((px, py), pbc, fill=(180, 130, 0, 200), font=pbc_font)

    # --- Radar graphic (left accent) ---
    radar_cx = safe_x + 120
    radar_cy = safe_y + safe_h // 2
    for r in [60, 45, 30, 15]:
        draw.ellipse(
            [radar_cx - r, radar_cy - r, radar_cx + r, radar_cy + r],
            outline=(*DARK_GREEN, 150), width=1
        )
    # Cross hairs
    draw.line([(radar_cx - 65, radar_cy), (radar_cx + 65, radar_cy)], fill=(*DARK_GREEN, 100), width=1)
    draw.line([(radar_cx, radar_cy - 65), (radar_cx, radar_cy + 65)], fill=(*DARK_GREEN, 100), width=1)
    # Sweep line
    angle = math.radians(35)
    sweep_x = radar_cx + int(60 * math.cos(angle))
    sweep_y = radar_cy - int(60 * math.sin(angle))
    draw.line([(radar_cx, radar_cy), (sweep_x, sweep_y)], fill=GREEN, width=2)
    # Bright dot on sweep
    draw.ellipse([sweep_x - 3, sweep_y - 3, sweep_x + 3, sweep_y + 3], fill=GREEN)
    # Blip
    blip_angle = math.radians(70)
    bx = radar_cx + int(40 * math.cos(blip_angle))
    by = radar_cy - int(40 * math.sin(blip_angle))
    draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=GREEN)

    # --- Waveform graphic (right accent) ---
    wave_cx = W - safe_x - 120
    wave_cy = safe_y + safe_h // 2
    wave_points = []
    for i in range(60):
        x = wave_cx - 55 + i * 2
        amp = 25 * math.sin(i * 0.3) * math.exp(-abs(i - 30) * 0.04)
        y = wave_cy + int(amp)
        wave_points.append((x, y))
    for i in range(len(wave_points) - 1):
        draw.line([wave_points[i], wave_points[i + 1]], fill=GREEN, width=2)
    # Second wave (dimmer, offset)
    for i in range(len(wave_points) - 1):
        x1, y1 = wave_points[i]
        x2, y2 = wave_points[i + 1]
        draw.line([(x1, y1 + 15), (x2, y2 + 15)], fill=DIM_GREEN, width=1)
    # Center line
    draw.line([(wave_cx - 60, wave_cy), (wave_cx + 60, wave_cy)], fill=(*DARK_GREEN, 80), width=1)

    # --- Vignette ---
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    # Darken edges
    for i in range(200):
        alpha = int(120 * (1 - i / 200))
        # Top
        vdraw.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
        # Bottom
        vdraw.line([(0, H - 1 - i), (W, H - 1 - i)], fill=(0, 0, 0, alpha))
    for i in range(300):
        alpha = int(100 * (1 - i / 300))
        # Left
        vdraw.line([(i, 0), (i, H)], fill=(0, 0, 0, alpha))
        # Right
        vdraw.line([(W - 1 - i, 0), (W - 1 - i, H)], fill=(0, 0, 0, alpha))

    img_rgba = Image.alpha_composite(img_rgba, vignette)

    # Save
    img_rgba.convert("RGB").save("/home/logkbomb/projects/daily-threat/assets/banner.png", "PNG")
    print("Banner saved.")


def make_profile():
    S = 800
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Black circle background
    margin = 10
    draw.ellipse([margin, margin, S - margin, S - margin], fill=BG)

    # Subtle circle border
    draw.ellipse([margin, margin, S - margin, S - margin], outline=(*DARK_GREEN, 120), width=3)
    draw.ellipse([margin + 15, margin + 15, S - margin - 15, S - margin - 15], outline=(*DARK_GREEN, 60), width=1)

    # CRT scanlines on circle
    for y in range(0, S, 4):
        # Only draw within circle
        dx = margin
        draw.line([(dx, y), (S - dx, y)], fill=(0, 0, 0, 25), width=1)

    # JC monogram with glow
    jc_font = ImageFont.truetype(FONT_BOLD, 280)
    text = "JC"
    bbox = draw.textbbox((0, 0), text, font=jc_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (S - tw) // 2 - bbox[0]
    ty = (S - th) // 2 - bbox[1]

    # Glow layers
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.text((tx, ty), text, fill=(0, 255, 65, 60), font=jc_font)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.alpha_composite(img, glow)

    glow2 = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gdraw2 = ImageDraw.Draw(glow2)
    gdraw2.text((tx, ty), text, fill=(0, 255, 65, 40), font=jc_font)
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=25))
    img = Image.alpha_composite(img, glow2)

    # Main text
    draw = ImageDraw.Draw(img)
    draw.text((tx, ty), text, fill=GREEN, font=jc_font)

    # Clip to circle
    mask = Image.new("L", (S, S), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([margin, margin, S - margin, S - margin], fill=255)
    img.putalpha(mask)

    img.save("/home/logkbomb/projects/daily-threat/assets/profile.png", "PNG")
    print("Profile saved.")


if __name__ == "__main__":
    make_banner()
    make_profile()
    print("Done!")
