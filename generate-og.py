#!/usr/bin/env python3
"""
Per Medjat OG Image Generator  --  minimal delta from IHS generator
===================================================================
Run from the Per-Medjat root directory:

    pip install Pillow
    python generate-og.py           # skip existing PNGs, always update HTML tags
    python generate-og.py --force   # regenerate all PNGs
"""

import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("pillow not installed  -- run: pip install Pillow")

W, H = 1200, 630

TYRIAN_PURPLE = (102, 2, 60)        # #66023C
PAPER         = (246, 241, 219)     # #F6F1DB
TERRACOTTA    = (139, 58, 26)       # #8B3A1A
LAPIS         = (26, 52, 104)       # #1A3468
GOLD_LABEL    = (225, 199, 138)     # #E1C78A
CREAM_BOX     = PAPER

BASE_URL         = "https://medjat.irokosociety.org"
LOGO_PATH        = Path("assets/IHS-Logo.jpg")
FORCE            = "--force" in sys.argv


def _blend(fg, alpha, bg):
    return tuple(int(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


LOGO_BOX                = dict(x=75, y=180, w=269, h=269)
TEXT_X_LOGO             = LOGO_BOX["x"] + LOGO_BOX["w"] + 75
RIGHT_PAD               = 72
LABEL_Y                 = 170
TITLE_OFFSET_FROM_LABEL = 38

SZ_LABEL  = 18
SZ_TITLE  = 62
SZ_SUB    = 26
SZ_DOMAIN = 22

SCHEMES = {
    "main": dict(
        bg        = TYRIAN_PURPLE,
        col_label = GOLD_LABEL,
        col_title = PAPER,
        col_sub   = (216, 184, 200),  # #D8B8C8, dusty pale mauve
        col_dom   = (197, 141, 169),  # #C58DA9, quiet footer mauve
    ),
    "library": dict(
        bg        = TERRACOTTA,
        col_label = GOLD_LABEL,
        col_title = PAPER,
        col_sub   = _blend(PAPER, 0.75, TERRACOTTA),
        col_dom   = (213, 167, 142),  # #D5A78E, strengthened footer
    ),
    "archives": dict(
        bg        = LAPIS,
        col_label = GOLD_LABEL,
        col_title = PAPER,
        col_sub   = _blend(PAPER, 0.75, LAPIS),
        col_dom   = (179, 189, 206),  # #B3BDCE, strengthened footer
    ),
}

# Deliberate line breaks keep every subtitle to a controlled two-line block.
# wrap_text() preserves these breaks while still wrapping unusually long lines.
PAGES = [
    dict(file="index.html", slug="og-pm-main", section="main",
         label="PER MEDJAT · IROKO HISTORICAL SOCIETY",
         title="Per Medjat", subtitle="House of Written\nKnowledge",
         og_title="Per Medjat - Iroko Historical Society",
         og_description="Per Medjat is the governed public interface for collections of the Iroko Historical Society. Structured knowledge with explicit stewardship boundaries.",
         og_url=f"{BASE_URL}/"),
    dict(file="library/index.html", slug="og-pm-library", section="library",
         label="PER MEDJAT · MEDJAT LIBRARY",
         title="Medjat Library",
         subtitle="Cataloged scholarly and reference materials\nfor Afro-Atlantic research",
         og_title="Medjat Library - Per Medjat - Iroko Historical Society",
         og_description="Cataloged scholarly and reference materials supporting research into Afro-Atlantic sacred knowledge systems. Published works, field editions, and the IHS Research Library catalog.",
         og_url=f"{BASE_URL}/library/"),
    dict(file="archives/index.html", slug="og-pm-archives", section="archives",
         label="PER MEDJAT · MEDJAT ARCHIVES",
         title="Medjat Archives",
         subtitle="Primary source and governed collections\nunder the Iroko Framework",
         og_title="Medjat Archives - Per Medjat - Iroko Historical Society",
         og_description="Archival and field collections governed under the six-tier Iroko Framework. Unique materials, sacred texts, and donor holdings stewarded with community authorization.",
         og_url=f"{BASE_URL}/archives/"),
    dict(file="ewe/index.html", slug="og-pm-ewe", section="archives",
         label="MEDJAT ARCHIVES · EWE COLLECTION",
         title="Ewe Database",
         subtitle="Botanical knowledge structured\nunder the Iroko Framework",
         og_title="Ewe Database - Medjat Archives - Iroko Historical Society",
         og_description="The Ewe Database provides a public interface for plant records structured using the Iroko Framework. Public botanical knowledge with explicit stewardship boundaries.",
         og_url=f"{BASE_URL}/ewe/"),
    dict(file="entrusting/index.html", slug="og-pm-entrusting", section="archives",
         label="MEDJAT ARCHIVES · COLLECTIONS",
         title="Entrusting the Work",
         subtitle="Knowledge donations, collection transfers\nand stewardship agreements",
         og_title="Entrusting the Work - Per Medjat - Iroko Historical Society",
         og_description="IHS actively seeks knowledge donations, collection transfers, and stewardship agreements from practitioners, lineage holders, scholars, and community institutions.",
         og_url=f"{BASE_URL}/entrusting/"),
    dict(file="espiritismo/index.html", slug="og-pm-espiritismo", section="archives",
         label="MEDJAT ARCHIVES · ESPIRITISMO",
         title="Espiritismo Collection",
         subtitle="Caribbean Spiritism archival and\nethnographic materials",
         og_title="Espiritismo Collection - Medjat Archives - Iroko Historical Society",
         og_description="A forthcoming corpus of structured archival and ethnographic materials on Caribbean Spiritism within the Medjat Archives.",
         og_url=f"{BASE_URL}/espiritismo/"),
    dict(file="hyatt/index.html", slug="og-pm-hyatt", section="archives",
         label="MEDJAT ARCHIVES · HYATT COLLECTION",
         title="Hyatt Collection",
         subtitle="Hoodoo and rootwork materials\nunder the Iroko Framework",
         og_title="Hyatt Collection - Medjat Archives - Iroko Historical Society",
         og_description="A planned corpus of structured entries from hoodoo and rootwork materials within the Medjat Archives.",
         og_url=f"{BASE_URL}/hyatt/"),
]

_GOOGLE_SPECS = {
    "garamond_ital": ("EB Garamond",   "400", "1"),
    "garamond_bold": ("EB Garamond",   "700", "0"),
    "sourcesans":    ("Source Sans 3", "400", "0"),
}
_WIN_FALLBACKS = {
    "garamond_ital": ["C:/Windows/Fonts/georgiai.ttf", "C:/Windows/Fonts/timesi.ttf", "C:/Windows/Fonts/times.ttf"],
    "garamond_bold": ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/times.ttf"],
    "sourcesans":    ["C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/segoeui.ttf"],
}
_font_cache: dict = {}
FONTS = Path("fonts-pm")
FONTS.mkdir(exist_ok=True)


def _find_poor_richard() -> Optional[str]:
    for name in ("PoorRichard.ttf", "poorrich.ttf", "PoorRich.ttf",
                 "poorrichard.ttf", "POORICH.TTF", "Poor Richard.ttf"):
        for folder in (Path("C:/Windows/Fonts"), Path("C:/Windows/fonts")):
            p = folder / name
            if p.exists():
                return str(p)
    for name in ("PoorRichard.ttf", "poorrichard.ttf", "poorrich.ttf"):
        c = FONTS / name
        if c.exists() and c.stat().st_size > 1000:
            return str(c)
    return None


def _download_font(key: str) -> Optional[Path]:
    dest = FONTS / f"{key}.ttf"
    if dest.exists() and dest.stat().st_size > 4000:
        return dest
    if dest.exists():
        dest.unlink()
    family, weight, ital = _GOOGLE_SPECS[key]
    css_url = (
        "https://fonts.googleapis.com/css2"
        f"?family={family.replace(' ', '+')}:ital,wght@{ital},{weight}"
    )
    headers = {"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"}
    print(f"  Downloading font: {family} weight={weight} ital={ital} ...")
    try:
        req = urllib.request.Request(css_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            css = r.read().decode()
        m = re.search(r"url\((https?://[^)]+\.ttf)\)", css)
        if m:
            ttf_url = m.group(1).strip()
            urllib.request.urlretrieve(ttf_url, dest)
            if dest.stat().st_size > 4000:
                print(f"  Saved  -> fonts-pm/{key}.ttf ({dest.stat().st_size} bytes)")
                return dest
            dest.unlink()
            print(f"  WARNING: downloaded {family} too small, skipping")
        else:
            print(f"  WARNING: no .ttf URL in CSS for {family}")
            print(f"  CSS preview: {css[:300]}")
    except Exception as e:
        print(f"  WARNING: could not download {family}: {e}")
    for fallback in _WIN_FALLBACKS.get(key, []):
        fb = Path(fallback)
        if fb.exists():
            print(f"  Using system fallback: {fallback}")
            return fb
    return None


def get_font(key: str, size: int) -> ImageFont.FreeTypeFont:
    cache_key = (key, size)
    if cache_key in _font_cache:
        return _font_cache[cache_key]
    path = None
    if key == "poorrichard":
        path = _find_poor_richard()
        if not path:
            print("  Poor Richard not found -- falling back to EB Garamond Bold")
            p = _download_font("garamond_bold")
            path = str(p) if p else None
    else:
        p = _download_font(key)
        path = str(p) if p else None
    f = None
    if path:
        try:
            f = ImageFont.truetype(path, size)
        except Exception as e:
            print(f"  WARNING: truetype() failed for {key} at {path}: {e}")
    if f is None:
        for emergency in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/times.ttf"]:
            try:
                f = ImageFont.truetype(emergency, size)
                print(f"  EMERGENCY fallback: {emergency} at {size}pt")
                break
            except Exception:
                pass
    if f is None:
        print(f"  CRITICAL: no font loaded for {key} at {size}pt -- output broken")
        f = ImageFont.load_default()
    _font_cache[cache_key] = f
    return f


def _text_w(draw, text, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def _text_h(draw, text, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]

def wrap_text(draw, text, font, max_w) -> list:
    """Wrap text while preserving any deliberate line breaks in the source."""
    lines = []

    for paragraph in text.splitlines():
        words = paragraph.split()
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            if _text_w(draw, candidate, font) <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

    return lines

def draw_wrapped(draw, text, font, x, y, max_w, color, leading_mult=1.25) -> int:
    for line in wrap_text(draw, text, font, max_w):
        draw.text((x, y), line, font=font, fill=color)
        y += int(_text_h(draw, line, font) * leading_mult)
    return y

def auto_size_title(draw, title, max_w):
    size = SZ_TITLE
    while size >= 32:
        f = get_font("poorrichard", size)
        if len(wrap_text(draw, title, f, max_w)) <= 3:
            return f, size
        size -= 4
    return get_font("poorrichard", 32), 32


def render_logo_panel(img: Image.Image) -> int:
    draw = ImageDraw.Draw(img)
    bx, by, bw, bh = LOGO_BOX["x"], LOGO_BOX["y"], LOGO_BOX["w"], LOGO_BOX["h"]
    draw.rectangle([bx, by, bx + bw, by + bh], fill=CREAM_BOX)
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGB").resize((bw, bh), Image.LANCZOS)
        img.paste(logo, (bx, by))
    return TEXT_X_LOGO


def make_og_image(page: dict) -> Image.Image:
    sc    = SCHEMES[page["section"]]
    img   = Image.new("RGB", (W, H), color=sc["bg"])
    draw  = ImageDraw.Draw(img)
    text_x = render_logo_panel(img)
    max_w  = W - text_x - RIGHT_PAD
    f_label = get_font("sourcesans", SZ_LABEL)
    draw.text((text_x, LABEL_Y), page["label"], font=f_label, fill=sc["col_label"])
    f_title, _ = auto_size_title(draw, page["title"], max_w)
    title_y    = LABEL_Y + TITLE_OFFSET_FROM_LABEL + _text_h(draw, "A", f_label)
    title_end  = draw_wrapped(draw, page["title"], f_title, text_x, title_y, max_w, sc["col_title"], 1.15)
    f_sub = get_font("garamond_ital", SZ_SUB)
    draw_wrapped(draw, page["subtitle"], f_sub, text_x, title_end + 20, max_w, sc["col_sub"], 1.45)
    f_dom  = get_font("sourcesans", SZ_DOMAIN)
    domain = "medjat.irokosociety.org"
    dh     = _text_h(draw, domain, f_dom)
    draw.text((text_x, H - 42 - dh), domain, font=f_dom, fill=sc["col_dom"])
    return img


OG_BLOCK = "\n".join([
    '  <meta property="og:type"         content="website">',
    '  <meta property="og:site_name"    content="Per Medjat - Iroko Historical Society">',
    '  <meta property="og:title"        content="{og_title}">',
    '  <meta property="og:description"  content="{og_description}">',
    '  <meta property="og:url"          content="{og_url}">',
    '  <meta property="og:image"        content="{og_image}">',
    '  <meta property="og:image:width"  content="1200">',
    '  <meta property="og:image:height" content="630">',
    '  <meta property="og:image:type"   content="image/png">',
    '  <meta name="twitter:card"        content="summary_large_image">',
    '  <meta name="twitter:title"       content="{og_title}">',
    '  <meta name="twitter:description" content="{og_description}">',
    '  <meta name="twitter:image"       content="{og_image}">',
])


def inject_og_tags(html_path: Path, page: dict, png_filename: str) -> None:
    src      = html_path.read_text(encoding="utf-8")
    og_image = f"{BASE_URL}/assets/{png_filename}"
    block    = OG_BLOCK.format(
        og_title       = page["og_title"],
        og_description = page["og_description"],
        og_url         = page["og_url"],
        og_image       = og_image,
    )
    cleaned = re.sub(
        r'\s*<meta\s+(?:property="og:|name="twitter:)[^>]*>\n?',
        "", src, flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r'\s*<meta\s+property="og:image:(?:width|height|type)"[^>]*>\n?',
        "", cleaned, flags=re.IGNORECASE,
    )
    new_src = re.sub(
        r"(</title>)", r"\1\n" + block, cleaned, count=1, flags=re.IGNORECASE,
    )
    html_path.write_text(new_src, encoding="utf-8")


def main():
    pr = _find_poor_richard()
    print("Per Medjat OG Image Generator")
    print("=" * 50)
    print(f"Poor Richard: {pr or 'NOT FOUND -- will use EB Garamond Bold fallback'}")
    print(f"Mode: {'--force' if FORCE else 'incremental'}\n")
    print("Checking fonts ...")
    for key in _GOOGLE_SPECS:
        p = _download_font(key)
        label = str(p) if p else "NOT FOUND"
        print(f"  {key:15s} -> {label}")
    dummy_img  = Image.new("RGB", (100, 100))
    dummy_draw = ImageDraw.Draw(dummy_img)
    f_test = get_font("poorrichard", SZ_TITLE)
    bb     = dummy_draw.textbbox((0, 0), "A", font=f_test)
    print(f"  title font 'A' height at SZ_TITLE={SZ_TITLE}: {bb[3]-bb[1]}px")
    del dummy_img, dummy_draw

    assets     = Path("assets")
    assets.mkdir(exist_ok=True)
    seen_slugs = set()
    generated  = []
    updated    = []

    for page in PAGES:
        html_path    = Path(page["file"])
        png_filename = f"{page['slug']}.png"
        png_path     = assets / png_filename
        print(f"\n[{page['file']}]")
        if not html_path.exists():
            print(f"  SKIP  (file not found)")
            continue
        if (not png_path.exists() or FORCE) and page["slug"] not in seen_slugs:
            print(f"  Generating {png_filename} ...")
            img = make_og_image(page)
            img.save(str(png_path), "PNG", optimize=True)
            print(f"  Saved -> assets/{png_filename}")
            generated.append(png_filename)
        else:
            print(f"  PNG: {png_filename} exists (use --force to regenerate)")
        seen_slugs.add(page["slug"])
        inject_og_tags(html_path, page, png_filename)
        print(f"  Tags: updated {page['file']}")
        updated.append(page["file"])

    print(f"\n{'=' * 50}")
    print(f"Generated {len(generated)} PNG(s), updated {len(updated)} HTML file(s)")
    print("Done. Commit assets/ and the updated HTML files.")


if __name__ == "__main__":
    main()
