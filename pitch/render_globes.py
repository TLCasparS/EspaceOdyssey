"""Render round, transparent-background globes for the pitch deck from the app's NASA textures.

Earth: app/assets/blue-marble-2004-07-4096.jpg (NASA Blue Marble Next Generation, July 2004)
Moon:  app/assets/lroc-moon-color-4096.jpg (NASA SVS CGI Moon Kit, from LRO camera data)
Both are equirectangular maps (left edge = 180° W). Orthographic view, light limb shading, soft rim glow.
Run from the repo root: python pitch/render_globes.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pitch" / "img"
SIZE = 900          # output diameter in px (plus glow margin)
SS = 2              # supersampling


def project(lat0, lon0, lat, lon):
    """Forward orthographic projection -> (x, y) in [-1, 1], y up; None if on the far side."""
    p0, l0, p, l = map(np.radians, (lat0, lon0, lat, lon))
    if np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(l - l0) < 0:
        return None
    x = np.cos(p) * np.sin(l - l0)
    y = np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(l - l0)
    return x, y


def globe(texture, lat0, lon0, marker, marker_rgb, glow_rgb, name):
    tex = np.asarray(Image.open(texture).convert("RGB")).astype(np.float32)
    H, W = tex.shape[:2]
    n = SIZE * SS
    ys, xs = np.mgrid[0:n, 0:n]
    x = (xs + 0.5) / n * 2 - 1
    y = 1 - (ys + 0.5) / n * 2
    rho = np.hypot(x, y)
    inside = rho <= 1
    c = np.arcsin(np.clip(rho, 0, 1))
    p0, l0 = np.radians(lat0), np.radians(lon0)
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.cos(c) * np.sin(p0) + np.where(rho > 0, y * np.sin(c) * np.cos(p0) / rho, 0))
        lon = l0 + np.arctan2(x * np.sin(c), rho * np.cos(c) * np.cos(p0) - y * np.sin(c) * np.sin(p0))
    u = ((np.degrees(lon) + 180) % 360) / 360 * (W - 1)
    v = (90 - np.degrees(lat)) / 180 * (H - 1)
    rgb = tex[np.clip(v, 0, H - 1).astype(int), np.clip(u, 0, W - 1).astype(int)]
    shade = 0.45 + 0.55 * np.sqrt(np.clip(np.cos(c), 0, 1))       # gentle limb darkening
    rgb = np.clip(rgb * shade[..., None], 0, 255)
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = rgb.astype(np.uint8)
    img[..., 3] = np.where(inside, 255, 0)
    sphere = Image.fromarray(img, "RGBA")

    d = ImageDraw.Draw(sphere)
    pos = project(lat0, lon0, *marker)
    if pos:
        cx, cy = (pos[0] + 1) / 2 * n, (1 - pos[1]) / 2 * n
        r = n * 0.022
        d.ellipse((cx - r * 1.7, cy - r * 1.7, cx + r * 1.7, cy + r * 1.7), outline=(255, 255, 255, 255), width=SS * 4)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=marker_rgb + (255,))
    sphere = sphere.resize((SIZE, SIZE), Image.LANCZOS)

    margin = int(SIZE * 0.06)
    canvas = Image.new("RGBA", (SIZE + 2 * margin,) * 2, (0, 0, 0, 0))
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((margin - 6, margin - 6, margin + SIZE + 6, margin + SIZE + 6), fill=glow_rgb + (150,))
    glow = glow.filter(ImageFilter.GaussianBlur(margin * 0.45))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(sphere, (margin, margin))
    canvas.save(OUT / name)
    print("saved", name, canvas.size, "marker at", None if not pos else (round(pos[0], 3), round(pos[1], 3)))


# Earth centred so Asia (Tian Shan, rank 1) is in view; gold marker = Tian Shan (42.572 N, 82.391 E, outputs/scores.csv)
globe(ROOT / "app/assets/blue-marble-2004-07-4096.jpg", 25, 65, (42.572, 82.391), (240, 200, 93), (108, 180, 238),
      "globe_earth.png")
# Moon seen from below the south pole region; teal marker = Shackleton floor low point (89.625 S, 118.8 E, app/app.js)
globe(ROOT / "app/assets/lroc-moon-color-4096.jpg", -55, 100, (-89.625, 118.8), (60, 200, 180), (232, 227, 211),
      "globe_moon.png")
