#!/usr/bin/env python3
"""Generate DevTeam's artwork (concept A: the striped D) into overlay/ and brand/.

Everything is drawn here from one geometry, in ScienceSoft brand colours, and
written at the exact paths, sizes and SVG structure upstream's files use, so
prepare.sh's overlay step swaps them in without code changes:

  app icons      website/electron/icon{,-nightly}.{png,ico,icns}, build/icons*/
  tray           website/electron/trayTemplate{,@2x}.png (black, macOS template)
  web            website/public/icon-{192,512}.png, src/kiro_crew/static/kirocrew-logo*.png
  installer      packaging/installer-assets/windows-installer-{header,sidebar}.{bmp,svg},
                 dmg-background.{svg,tiff}
  dashboard art  website/src/assets/avatarPoses/pose-1..11.svg   (parsed by lib/avatarPoses.ts)
                 website/src/assets/ghost-poses/pose-1..8.svg
                 website/src/assets/onboarding/kiro-ghost-*.svg
                 website/src/assets/kiro-file-chomper.png
                 website/src/assets/product-mark.svg              (patch 0050)
  loading screen rebrand/loading-character.json                   (rewrite_strings.py)
  masters        brand/devteam-{icon,mark,lockup}.svg

Generated files are committed; CI never runs this. To regenerate:

  python -m pip install resvg-py pillow
  python scripts/brand_assets.py

Fonts: brand/fonts/OpenSans-*.ttf (SIL OFL 1.1, brand/fonts/OFL.txt).
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "overlay"
BRAND = ROOT / "brand"
FONTS = [str(p) for p in sorted((BRAND / "fonts").glob("*.ttf"))]

# ScienceSoft theme colours (brand book §1.1) -- no others.
BLUE, NAVY, ORANGE = "#005EB8", "#2F5597", "#FF9A08"
TEAL, GREEN, BRIGHT, SKY = "#0AB9CF", "#0AC594", "#1A8FFF", "#479BEB"
INK, PANEL, WHITE = "#404040", "#E8F4FF", "#FFFFFF"
FONT = "Open Sans"
TAGLINE = "ScienceSoft AI"


# --------------------------------------------------------------------- render
def render(svg: str, width: int, height: int | None = None) -> Image.Image:
    png = resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height or width,
                                font_files=FONTS, skip_system_fonts=True)
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def out(rel: str) -> Path:
    path = OVERLAY / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_svg(rel: str, svg: str, root: Path = OVERLAY) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8", newline="\n")


def save_png(rel: str, img: Image.Image) -> None:
    img.save(out(rel), optimize=True)


# ------------------------------------------------------------------- app icon
# 512-unit canvas. The D: straight left edge, half-disc right edge.
D_PATH = "M136 120H250A136 136 0 0 1 250 392H136Z"


def icon_svg(bg: str = BLUE, size: str = "large") -> str:
    """The app icon. Stripes read only from ~48 px up; below that a solid D."""
    parts = [f'<rect width="512" height="512" rx="112" fill="{bg}"/>']
    if size == "large":
        stripes = "".join(f'<rect x="100" y="{120 + i * 35}" width="320" height="22"/>' for i in range(7))
        parts.append(f'<defs><clipPath id="d"><path d="{D_PATH}"/></clipPath></defs>'
                     f'<g clip-path="url(#d)" fill="{WHITE}">{stripes}'
                     f'<rect x="100" y="365" width="320" height="27"/></g>')
    else:
        parts.append(f'<path d="{D_PATH}" fill="{WHITE}"/>')
    if size != "tiny":
        parts.append(f'<rect x="356" y="356" width="{44 if size == "large" else 56}" '
                     f'height="{44 if size == "large" else 56}" fill="{ORANGE}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{"".join(parts)}</svg>'


def icon(px: int, bg: str = BLUE) -> Image.Image:
    size = "large" if px >= 48 else ("small" if px >= 24 else "tiny")
    return render(icon_svg(bg, size), px)


def tray_svg() -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="112 112 288 288">'
            f'<path d="{D_PATH}" fill="#000"/></svg>')


def mark_svg() -> str:
    """Nav-rail glyph (24-unit, stroke-drawn like the Lucide icons beside it).
    BrandGlyph paints it as a mask over currentColor, so colour is irrelevant."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M5 4h6.5a8 8 0 0 1 0 16H5Z"/><path d="M8.5 9.5h4"/><path d="M8.5 14.5h4"/></svg>')


def lockup_svg(fg: str = BLUE, sub: str = INK) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 160">'
            f'<g transform="translate(8 16) scale(0.25)">{icon_svg()[icon_svg().index(">") + 1:-6]}</g>'
            + text(160, 86, "DevTeam", 64, 800, fg) + text(162, 126, TAGLINE, 26, 600, sub)
            + '</svg>')


# ------------------------------------------------------------------ character
# The agent character that replaces the ghost: a D-shaped body, two oval eyes,
# a short antenna. Units are the avatar tile's (300). Eye centre = origin of
# every pose transform, so lib/avatarPoses.ts's measured EYE_CENTERS stay valid.
BODY_W, BODY_H, CORNER = 196.0, 204.0, 34.0
EYE_RX, EYE_RY, EYE_GAP = 11.0, 16.0, 48.0
EYE_DX, EYE_DY = 14.0, 44.0           # eye centre relative to body centre (x right, y up)
ANT_STEM_W, ANT_STEM_H, ANT_R = 14.0, 24.0, 13.0


def body_geometry(ex: float, ey: float, scale: float = 1.0):
    w, h, r = BODY_W * scale, BODY_H * scale, CORNER * scale
    R = h / 2
    cx, cy = ex - EYE_DX * scale, ey + EYE_DY * scale
    x0, y0 = cx - w / 2, cy - h / 2
    xr = x0 + w - R                      # where the half-disc starts
    return w, h, r, R, x0, y0, xr


def body_d(ex: float, ey: float, scale: float = 1.0, arm: bool = False) -> str:
    w, h, r, R, x0, y0, xr = body_geometry(ex, ey, scale)
    d = (f"M{x0 + r:.2f} {y0:.2f}H{xr:.2f}A{R:.2f} {R:.2f} 0 0 1 {xr:.2f} {y0 + h:.2f}"
         f"H{x0 + r:.2f}Q{x0:.2f} {y0 + h:.2f} {x0:.2f} {y0 + h - r:.2f}"
         f"V{y0 + r:.2f}Q{x0:.2f} {y0:.2f} {x0 + r:.2f} {y0:.2f}Z")
    ax = x0 + w * 0.36
    sw, sh, ar = ANT_STEM_W * scale, ANT_STEM_H * scale, ANT_R * scale
    d += (f"M{ax - sw / 2:.2f} {y0 + 2 * scale:.2f}V{y0 - sh:.2f}H{ax + sw / 2:.2f}V{y0 + 2 * scale:.2f}Z"
          f"M{ax - ar:.2f} {y0 - sh - ar * 0.6:.2f}a{ar:.2f} {ar:.2f} 0 1 0 {2 * ar:.2f} 0"
          f"a{ar:.2f} {ar:.2f} 0 1 0 {-2 * ar:.2f} 0Z")
    if arm:  # a raised arm on the straight side, for the onboarding wave
        aw = 30 * scale
        hx, hy = x0 + 6 * scale, y0 + h * 0.52
        d += (f"M{hx:.2f} {hy:.2f}L{hx - 62 * scale:.2f} {hy - 58 * scale:.2f}"
              f"a{aw / 2:.2f} {aw / 2:.2f} 0 0 1 {21 * scale:.2f} {-21 * scale:.2f}"
              f"L{hx + 20 * scale:.2f} {hy - 22 * scale:.2f}Z")
    return d


def antenna_ball(ex: float, ey: float, scale: float = 1.0) -> tuple[float, float, float]:
    w, h, r, R, x0, y0, xr = body_geometry(ex, ey, scale)
    ax = x0 + w * 0.36
    return ax, y0 - ANT_STEM_H * scale - ANT_R * scale * 0.6, ANT_R * scale


def eye_ds(ex: float, ey: float, scale: float = 1.0) -> list[str]:
    rx, ry, g = EYE_RX * scale, EYE_RY * scale, EYE_GAP * scale / 2
    return [f"M{x - rx:.2f} {ey:.2f}a{rx:.2f} {ry:.2f} 0 1 0 {2 * rx:.2f} 0a{rx:.2f} {ry:.2f} 0 1 0 {-2 * rx:.2f} 0Z"
            for x in (ex - g, ex + g)]


def pose_transform(ex: float, ey: float, rot: float, mirror: bool) -> str:
    t = f"rotate({rot} {ex} {ey})" if rot else ""
    if mirror:
        t += f" translate({2 * ex} 0) scale(-1 1)"
    return t.strip()


def outline_points(ex, ey, scale, rot, mirror, arm=False):
    """Points on the character's outline after the pose transform, for bounds."""
    w, h, r, R, x0, y0, xr = body_geometry(ex, ey, scale)
    pts = [(x0, y0), (x0, y0 + h)]
    pts += [(xr + R * math.sin(a / 20 * math.pi), y0 + R - R * math.cos(a / 20 * math.pi)) for a in range(21)]
    ax, ay, ar = antenna_ball(ex, ey, scale)
    pts += [(ax + ar * math.cos(a / 8 * math.pi), ay + ar * math.sin(a / 8 * math.pi)) for a in range(16)]
    if arm:
        hx, hy = x0 + 6 * scale, y0 + h * 0.52
        pts += [(hx - 77 * scale, hy - 79 * scale), (hx - 62 * scale, hy - 58 * scale)]
    out_pts = []
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for x, y in pts:
        if mirror:
            x = 2 * ex - x
        dx, dy = x - ex, y - ey
        out_pts.append((ex + dx * c - dy * s, ey + dx * s + dy * c))
    return out_pts


# Upstream's measured eye centres (lib/avatarPoses.ts EYE_CENTERS) -- keep in step.
EYE_CENTERS = [(181.9, 115.4), (158.8, 108), (231.8, 125.7), (114.8, 117.4), (172.5, 101.4), (108.1, 95.5),
               (206.4, 102.5), (157.8, 105.1), (181, 124.7), (102.7, 102.3), (198, 100.6)]
AVATAR_POSES = [(0, False), (-8, False), (12, True), (-10, True), (6, False), (-14, True),
                (10, False), (0, True), (-6, False), (14, True), (-12, False)]


def avatar_pose_svg(i: int) -> str:
    """Structure lib/avatarPoses.ts parses: one self-closing <rect fill>, one body
    <path fill="#fff">, two eye <path>s with no fill attribute."""
    ex, ey = EYE_CENTERS[i]
    rot, mirror = AVATAR_POSES[i]
    t = pose_transform(ex, ey, rot, mirror)
    ta = f' transform="{t}"' if t else ""
    eyes = "".join(f'\n  <path d="{d}"{ta}/>' for d in eye_ds(ex, ey))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">\n'
            f'  <rect width="300" height="300" fill="{BLUE}"/>\n'
            f'  <path d="{body_d(ex, ey)}" fill="#fff"{ta}/>{eyes}\n</svg>\n')


def character_svg(rot=0.0, mirror=False, arm=False, stroke=0.0, pad=0.0, fill=WHITE,
                  eyes=True, ball=True, box=None, box_outline=0.0) -> str:
    """The character alone on a transparent canvas, cropped to its bounds.

    With ``box=(w, h, inset)`` it is fitted into that exact viewBox; the fit
    ignores any stroke, so a ``box_outline`` (stroke offset in box units) traces
    the very same body as the unstroked file fitted with the same box."""
    ex, ey = 0.0, 0.0
    t = pose_transform(ex, ey, rot, mirror)
    pts = outline_points(ex, ey, 1.0, rot, mirror, arm)
    m = (0 if box else stroke / 2) + pad
    minx, miny = min(p[0] for p in pts) - m, min(p[1] for p in pts) - m
    vw, vh = max(p[0] for p in pts) + m - minx, max(p[1] for p in pts) + m - miny
    if box and box_outline:
        k = min((box[0] - 2 * box[2]) / vw, (box[1] - 2 * box[2]) / vh)
        stroke = 2 * box_outline / k
    ta = f' transform="{t}"' if t else ""
    st = f' stroke="#000" stroke-width="{stroke}" stroke-linejoin="round"' if stroke else ""
    body = f'<path d="{body_d(ex, ey, arm=arm)}" fill="{fill}"{st}{ta}/>'
    ax, ay, ar = antenna_ball(ex, ey)
    ball_el = (f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="{ar:.2f}" fill="{ORANGE}"{st}{ta}/>' if ball else "")
    eye_el = "".join(f'<path d="{d}" fill="#000"{ta}/>' for d in eye_ds(ex, ey)) if eyes else ""
    inner = body + ball_el + eye_el
    if box:  # fit into an exact upstream viewBox (bw, bh), centred
        bw, bh, inset = box
        k = min((bw - 2 * inset) / vw, (bh - 2 * inset) / vh)
        tx, ty = (bw - vw * k) / 2 - minx * k, (bh - vh * k) / 2 - miny * k
        return (f'<svg width="{bw}" height="{bh}" viewBox="0 0 {bw} {bh}" fill="none" xmlns="http://www.w3.org/2000/svg">'
                f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k:.5f})">{inner}</g></svg>\n')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.2f} {miny:.2f} {vw:.2f} {vh:.2f}" '
            f'fill="none">{inner}</svg>\n')


GHOST_POSES = [(0, False), (-12, False), (10, True), (-6, True), (14, False), (-14, True), (6, False), (0, True)]


def chomper_svg() -> str:
    """Drop-a-file overlay art (512x356): the character with a document."""
    ex, ey = 200.0, 160.0
    s = 1.15
    body = f'<path d="{body_d(ex, ey, s)}" fill="{WHITE}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
    ax, ay, ar = antenna_ball(ex, ey, s)
    ball = f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{ar:.1f}" fill="{ORANGE}" stroke="{INK}" stroke-width="6"/>'
    eyes = "".join(f'<path d="{d}" fill="#000"/>' for d in eye_ds(ex, ey, s))
    mouth = f'<ellipse cx="{ex + 6:.1f}" cy="{ey + 74:.1f}" rx="44" ry="30" fill="#000"/>'
    doc = ('<g transform="translate(330 150) rotate(12)">'
           f'<path d="M0 0H70L98 28V130H0Z" fill="{WHITE}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
           f'<path d="M70 0V28H98Z" fill="{ORANGE}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
           f'<rect x="18" y="50" width="60" height="9" rx="4" fill="{BLUE}"/>'
           f'<rect x="18" y="72" width="48" height="9" rx="4" fill="{BLUE}"/>'
           f'<rect x="18" y="94" width="60" height="9" rx="4" fill="{BLUE}"/></g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 356">{body}{ball}{eyes}{mouth}{doc}</svg>'


# ------------------------------------------------------------------ installer
def family(weight: int) -> str:
    """Open Sans ships its heavy cuts as their own families ("Open Sans ExtraBold"),
    which is how the brand template names them too; plain "Open Sans" is the fallback."""
    named = {800: "Open Sans ExtraBold", 600: "Open Sans SemiBold"}.get(weight)
    return f"'{named}', '{FONT}'" if named else f"'{FONT}'"


def text(x, y, s, size, weight=800, fill=BLUE, anchor="start", spacing=0):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{family(weight)}" font-weight="{weight}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls}>{s}</text>')


def nested_icon(x, y, px, bg=BLUE) -> str:
    inner = icon_svg(bg)
    return f'<g transform="translate({x} {y}) scale({px / 512})">{inner[inner.index(">") + 1:-6]}</g>'


def header_svg() -> str:  # NSIS header, 150x57, right-aligned image area
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="57" viewBox="0 0 150 57">'
            f'<rect width="150" height="57" fill="{WHITE}"/>'
            + text(8, 27, "DevTeam", 17) + text(9, 42, TAGLINE, 9, 600, INK)
            + nested_icon(108, 10, 36) +f'<rect y="55" width="150" height="2" fill="{ORANGE}"/></svg>')


def sidebar_svg() -> str:  # NSIS welcome/finish sidebar, 164x314
    tile = (f'<rect x="38" y="70" width="88" height="88" rx="19" fill="{WHITE}"/>'
            f'<g transform="translate(38 70) scale({88 / 512})"><defs><clipPath id="s"><path d="{D_PATH}"/></clipPath></defs>'
            f'<g clip-path="url(#s)" fill="{BLUE}">'
            + "".join(f'<rect x="100" y="{120 + i * 35}" width="320" height="22"/>' for i in range(7))
            + f'<rect x="100" y="365" width="320" height="27"/></g>'
            f'<rect x="356" y="356" width="44" height="44" fill="{ORANGE}"/></g>')
    squares = "".join(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{c}"/>'
                      for x, y, s, c in [(14, 268, 14, ORANGE), (32, 286, 9, WHITE), (136, 24, 9, WHITE), (118, 14, 6, ORANGE)])
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="164" height="314" viewBox="0 0 164 314">'
            f'<rect width="164" height="314" fill="{BLUE}"/>{tile}'
            + text(82, 196, "DevTeam", 22, 800, WHITE, "middle")
            + text(82, 216, TAGLINE, 11, 600, WHITE, "middle") + squares + '</svg>')


def dmg_svg() -> str:  # macOS DMG window, 660x420; icons sit at (170,246) and (490,246)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="660" height="420" viewBox="0 0 660 420">'
            f'<rect width="660" height="420" fill="{PANEL}"/>'
            + text(330, 86, "DevTeam", 34, 800, BLUE, "middle")
            + text(330, 112, "Drag DevTeam onto the Applications folder", 14.5, 400, INK, "middle")
            + f'<polyline points="318,226 340,246 318,266" fill="none" stroke="{ORANGE}" stroke-width="8" '
              'stroke-linecap="round" stroke-linejoin="round"/>'
            + "".join(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{c}"/>'
                      for x, y, s, c in [(28, 370, 18, ORANGE), (54, 388, 10, BLUE), (612, 30, 12, BLUE), (596, 18, 8, ORANGE)])
            + '</svg>')


def to_bmp(img: Image.Image, rel: str) -> None:
    flat = Image.new("RGB", img.size, (255, 255, 255))
    flat.paste(img, mask=img.split()[3])
    flat.save(out(rel), format="BMP")


# ------------------------------------------------------------------- loading
def loading_character() -> dict:
    """Body + eyes for website/electron/loading.html's GHOST_SVG (white body,
    black eyes in a .g-eyes group the page blinks)."""
    ex, ey = 0.0, 0.0
    pts = outline_points(ex, ey, 1.0, 0, False)
    pad = 6
    minx, miny = min(p[0] for p in pts) - pad, min(p[1] for p in pts) - pad
    vw, vh = max(p[0] for p in pts) + pad - minx, max(p[1] for p in pts) + pad - miny
    return {"viewBox": f"{minx:.1f} {miny:.1f} {vw:.1f} {vh:.1f}", "body": body_d(ex, ey), "eyes": eye_ds(ex, ey)}


# ---------------------------------------------------------------------- main
def main() -> None:
    sizes = [16, 32, 48, 64, 128, 256, 512]
    for bg, suffix, icons_dir in [(BLUE, "", "icons"), (NAVY, "-nightly", "icons-nightly")]:
        big = icon(1024, bg)
        save_png(f"website/electron/icon{suffix}.png", big)
        ico_imgs = [icon(s, bg) for s in (16, 24, 32, 48, 64, 128, 256)]
        ico_imgs[-1].save(out(f"website/electron/icon{suffix}.ico"), format="ICO",
                          sizes=[(i.width, i.height) for i in ico_imgs], append_images=ico_imgs[:-1])
        big.save(out(f"website/electron/icon{suffix}.icns"), format="ICNS")
        for s in sizes:
            save_png(f"website/electron/build/{icons_dir}/{s}x{s}.png", icon(s, bg))
        save_png(f"src/kiro_crew/static/kirocrew-logo{suffix}.png", icon(512, bg))
    save_png("website/public/icon-192.png", icon(192))
    save_png("website/public/icon-512.png", icon(512))
    save_png("website/electron/trayTemplate.png", render(tray_svg(), 18))
    save_png("website/electron/trayTemplate@2x.png", render(tray_svg(), 36))

    for i in range(11):
        write_svg(f"website/src/assets/avatarPoses/pose-{i + 1}.svg", avatar_pose_svg(i))
    for i, (rot, mirror) in enumerate(GHOST_POSES):
        write_svg(f"website/src/assets/ghost-poses/pose-{i + 1}.svg",
                  character_svg(rot, mirror, stroke=16, pad=2))
    onboarding = "website/src/assets/onboarding/"
    write_svg(onboarding + "kiro-ghost-var1.svg", character_svg(-8, False, box=(51, 48, 2)))
    write_svg(onboarding + "kiro-ghost-var2.svg", character_svg(8, True, box=(61, 48, 2)))
    write_svg(onboarding + "kiro-ghost-with-arm.svg", character_svg(0, False, arm=True, box=(67, 54, 3)))
    write_svg(onboarding + "kiro-ghost-with-arm-outline.svg",
              character_svg(0, False, arm=True, fill="#000", eyes=False, ball=False, box=(67, 54, 3), box_outline=3))
    write_svg("website/src/assets/product-mark.svg", mark_svg())
    chomper = chomper_svg()
    save_png("website/src/assets/kiro-file-chomper.png", render(chomper, 512, 356))

    assets = "packaging/installer-assets/"
    for name, svg, w, h in [("windows-installer-header", header_svg(), 150, 57),
                            ("windows-installer-sidebar", sidebar_svg(), 164, 314)]:
        write_svg(assets + name + ".svg", svg)
        to_bmp(render(svg, w, h), assets + name + ".bmp")
    write_svg(assets + "dmg-background.svg", dmg_svg())
    # Two pages, as electron-builder expects for a DMG background: 1x at 72 dpi and
    # a 2x (Retina) page at 144 dpi (website/electron/test/packaging.test.js).
    retina = render(dmg_svg(), 1320, 840)
    retina.encoderinfo = {"dpi": (144, 144)}
    render(dmg_svg(), 660, 420).save(out(assets + "dmg-background.tiff"), format="TIFF",
                                     save_all=True, append_images=[retina], dpi=(72, 72))

    (ROOT / "rebrand" / "loading-character.json").write_text(
        json.dumps(loading_character(), indent=2) + "\n", encoding="utf-8", newline="\n")

    write_svg("devteam-icon.svg", icon_svg(), BRAND)
    write_svg("devteam-mark.svg", mark_svg(), BRAND)
    write_svg("devteam-lockup.svg", lockup_svg(), BRAND)
    write_svg("devteam-character.svg", character_svg(0, False, stroke=10, pad=4), BRAND)
    print("brand assets written to overlay/, brand/ and rebrand/loading-character.json")


if __name__ == "__main__":
    main()
