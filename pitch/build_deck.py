"""Build pitch/Moon_Twins_on_Earth.pptx (7 slides, 16:9, with a live-demo slide) with python-pptx.

Run from the repo root:  python pitch/build_deck.py   (globes first: python pitch/render_globes.py)
Design follows the web app (app/style.css): palette 'Earth seen from the Moon', condensed bold titles,
rounded panels with a thin border, gold numbered circles. Fonts: Bahnschrift (titles, stands in for Fira Sans
Extra Condensed) and Segoe UI (body, stands in for Fira Sans); both ship with Windows.
Numbers: see pitch/SCRIPT.md, "Sources".
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
APP_URL = "tlcaspars.github.io/EspaceOdyssey/app/"

# app/style.css :root
BG = RGBColor(0x06, 0x12, 0x1C)
PANEL = RGBColor(0x0C, 0x1E, 0x2C)
PANEL2 = RGBColor(0x12, 0x29, 0x3B)
BORDER = RGBColor(0x24, 0x46, 0x5E)
BRAND = RGBColor(0x13, 0x42, 0x57)
TEXT = RGBColor(0xEE, 0xF3, 0xF6)
MUTED = RGBColor(0xA7, 0xBA, 0xC7)
SIGNAL = RGBColor(0x3C, 0xC8, 0xB4)
ON_SIGNAL = RGBColor(0x04, 0x20, 0x1C)
EARTH = RGBColor(0x6C, 0xB4, 0xEE)
MOON = RGBColor(0xE8, 0xE3, 0xD3)
ACCENT = RGBColor(0xF0, 0xC8, 0x5D)
WARN = RGBColor(0xF0, 0xA3, 0x5D)
BLACK = RGBColor(0, 0, 0)
TITLE_FONT = "Bahnschrift Condensed"
BODY_FONT = "Segoe UI"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    return s


def _zero_margins(tf):
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)


def text(s, x, y, w, h, runs, size=20, color=TEXT, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         font=BODY_FONT, gap=0.45, name=None):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, opts) tuples.
    opts: size, color, bold, font, spacing (character spacing in pt)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    _zero_margins(tf)
    paras = [runs] if isinstance(runs, str) else runs
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if i and gap:
            p.space_before = Pt(size * gap)
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = t
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.color.rgb = o.get("color", color)
            if "spacing" in o:   # character spacing, e.g. for uppercase labels
                r.font._element.set("spc", str(int(o["spacing"] * 100)))   # font._element is <a:rPr>
    return tb


def box(s, x, y, w, h, fill=PANEL, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, weight=1.25):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(weight)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    sh.shadow.inherit = False
    return sh


def pic(s, path, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    return s.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def framed(s, path, x, y, w, h_img):
    """Screenshot inside an app-style panel (thin border, small inset) so its edges are not cut hard."""
    pad = 0.12
    box(s, x - pad, y - pad, w + 2 * pad, h_img + 2 * pad, fill=PANEL, radius=0.03)
    return pic(s, path, x, y, w=w)


def label(s, x, y, t, color=SIGNAL, w=6):
    """Small uppercase label, like the app's panel headings (EARTH TWINS, THE MOON)."""
    text(s, x, y, w, 0.35, [[(t.upper(), {"font": TITLE_FONT, "bold": True, "spacing": 2.5})]], size=15, color=color)


def title(s, eyebrow, t):
    label(s, 0.6, 0.42, eyebrow)
    text(s, 0.6, 0.72, 12.1, 0.9, [[(t, {"font": TITLE_FONT, "bold": True})]], size=44, name="Title")


def num(s, n, x, y, d=0.5, fill=ACCENT, color=BG, size=18):
    c = box(s, x, y, d, d, fill=fill, line=None, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    _zero_margins(tf)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = TITLE_FONT, Pt(size), True, color


def pill(s, x, y, w, t, fill=BRAND, line=SIGNAL, color=TEXT, size=16, h=0.5):
    b = box(s, x, y, w, h, fill=fill, line=line, radius=0.5)
    tf = b.text_frame
    _zero_margins(tf)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = t
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = BODY_FONT, Pt(size), True, color


def caption(s, t, y=7.02):
    text(s, 0.6, y, 12.1, 0.3, t, size=10.5, color=MUTED)


def notes(s, who, words):
    s.notes_slide.notes_text_frame.text = f"{who}\n\n{words}"


# ---------- 1. Title (like the app's Earthrise opening screen) ----------
s = new_slide(BLACK)
pic(s, IMG / "earthrise_16x9.jpg", 0, 0, w=13.333)
label(s, 0.7, 0.6, "Team EspaceOdyssey", color=MUTED)
text(s, 0.7, 0.95, 5.8, 2.3, [[("Moon Twins", {"font": TITLE_FONT, "bold": True})],
                              [("on Earth", {"font": TITLE_FONT, "bold": True})]], size=66, gap=0)
text(s, 0.7, 3.3, 6.2, 0.5, "Where on Earth can we rehearse a lunar base?", size=22, color=MUTED)
text(s, 0.7, 4.1, 6.2, 1.3, [[("Caspar Schlageter · Sofi Sosa · Mateo Pozo", {"bold": True, "color": ACCENT})],
                             "NASA Space Apps Challenge 2026"], size=18)
text(s, 7.6, 0.35, 5.4, 0.3, "Earthrise, seen from Apollo 8 in lunar orbit, 24 Dec 1968 · photo: NASA", size=10.5,
     color=MUTED, align=PP_ALIGN.RIGHT)
notes(s, "Speaker A (Caspar) · ~12 s",
      "Hi, we are Caspar, Sofi and Mateo, team EspaceOdyssey. This is Earthrise, seen from Apollo 8. "
      "We turn the view around and look for the Moon's twins on Earth.")

# ---------- 2. The question ----------
s = new_slide()
title(s, "The question", "Where on Earth can we rehearse a Moon base?")
box(s, 0.6, 2.0, 5.85, 3.35)
text(s, 0.95, 2.3, 5.2, 3.3, [
    [("TODAY", {"font": TITLE_FONT, "bold": True, "color": WARN, "size": 26, "spacing": 2})],
    "Analog sites are hand-picked by eye",
    "Poorly characterized: nobody measured how Moon-like they are",
    [("Haughton · Meteor Crater · Iceland", {"color": MUTED, "size": 17})],
], size=21)
box(s, 6.85, 2.0, 5.85, 3.35, fill=PANEL2, line=SIGNAL, weight=2)
text(s, 7.2, 2.3, 5.2, 3.3, [
    [("OUR APPROACH", {"font": TITLE_FONT, "bold": True, "color": SIGNAL, "size": 26, "spacing": 2})],
    "A systematic search of Earth",
    "Open NASA and ESA data only",
    "Measured criterion by criterion against real lunar sites",
], size=21)
pic(s, IMG / "lunar_horizon_strip.jpg", 0, 6.15, w=13.333)
notes(s, "Speaker A (Caspar) · ~16 s",
      "Astronauts rehearse Moon missions on Earth. But today's analog sites were picked by eye, and nobody "
      "measured how Moon-like they are. So we searched systematically, with open data only.")

# ---------- 3. Method ----------
s = new_slide()
title(s, "Method", "One ruler for two worlds")
G = 3.15   # globe image size (incl. glow margin)
pic(s, IMG / "globe_moon.png", 0.75, 1.65, w=G, h=G)
pic(s, IMG / "globe_earth.png", 9.43, 1.65, w=G, h=G)
label(s, 0.6, 4.95, "Moon · NASA data", color=MOON)
text(s, 0.6, 5.3, 4.3, 1.6, ["LOLA + PGDA: Shackleton and 2 craters in Artemis III regions",
                             "SLDEM2015: 20 mare cells"], size=16, gap=0.35)
label(s, 9.0, 4.95, "Earth · open data", color=EARTH, w=3.8)
text(s, 9.0, 5.3, 3.8, 1.6, ["Copernicus DEM (30 m elevation)", "ESA WorldCover (land cover)"], size=16, gap=0.35)
for x0 in (4.15, 8.3):
    a = s.shapes.add_shape(MSO_SHAPE.LEFT_RIGHT_ARROW, Inches(x0), Inches(3.0), Inches(0.85), Inches(0.42))
    a.fill.solid(); a.fill.fore_color.rgb = BORDER; a.line.fill.background()
box(s, 5.15, 2.45, 3.0, 1.5, fill=SIGNAL, line=None, radius=0.12)
text(s, 5.15, 2.45, 3.0, 1.5, [[("Same code", {"font": TITLE_FONT, "bold": True, "size": 30, "color": ON_SIGNAL})],
                               [("same 60 m grid", {"size": 17, "color": ON_SIGNAL})]],
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, gap=0.1)
text(s, 4.95, 4.25, 3.4, 1.2, [[("Score per criterion", {"bold": True})],
                               [("1 = same as the Moon", {"color": MUTED})]], size=17, align=PP_ALIGN.CENTER, gap=0.2)
caption(s, "Moon: NASA LOLA LDEM_80S_20MPP_ADJ, PGDA illumination map, SLDEM2015. Earth: Copernicus DEM GLO-30, "
           "ESA WorldCover 2021. Globes: NASA Blue Marble and CGI Moon Kit (LRO). Dots: Tian Shan, Shackleton.")
notes(s, "Speaker A (Caspar) · ~25 s",
      "On the Moon: Shackleton crater at the south pole and two craters in Artemis III regions, from NASA's LOLA "
      "and PGDA data, plus mare plains from SLDEM2015. On Earth: the Copernicus elevation model and ESA "
      "WorldCover. Same code, same 60-metre grid. Every criterion scores from zero to one: one means identical "
      "to the Moon.")

# ---------- 4. The search ----------
s = new_slide()
title(s, "The search", "~265,000 places searched in one night")
framed(s, IMG / "funnel.png", 0.72, 1.85, w=6.9, h_img=6.9 * 600 / 841)
X = 8.35
for i, (big, small, col) in enumerate((("~265,000", "cells of 15 km searched", TEXT),
                                       ("1,825", "crater-like places scored", MOON),
                                       ("1,261", "Polar places ranked", SIGNAL))):
    text(s, X, 1.75 + i * 1.2, 4.4, 1.15, [[(big, {"font": TITLE_FONT, "size": 48, "bold": True, "color": col})],
                                           [(small, {"size": 16, "color": MUTED})]], gap=0)
box(s, X, 5.45, 4.35, 1.4, fill=PANEL2, line=WARN, weight=1.75)
text(s, X + 0.25, 5.57, 3.9, 1.2, [[("111 open-pit mines", {"font": TITLE_FONT, "bold": True, "color": WARN,
                                                            "size": 26})],
                                   "found and filtered out, e.g. Chuquicamata and Escondida (Chile)"], size=15, gap=0.15)
caption(s, "Funnel: screenshot of our app. Mine filter: Maus et al. 2022 mining polygons. "
           "Cell size ≈ an Artemis III candidate region (NASA, 2022).")
notes(s, "Speaker A (Caspar) · ~22 s",
      "In one night we searched about 265,000 cells, each the size of an Artemis III landing region. 1,825 "
      "crater-like places were scored. The finder was so good it found 111 open-pit mines, like Chuquicamata. "
      "We filtered them out: 1,261 places remain. Sofi will show you.")

# ---------- 5. Live demo ----------
s = new_slide()
title(s, "Live demo", "Let's explore the Moon twins")
W5 = 8.0
framed(s, IMG / "app_map.png", 0.72, 1.9, w=W5, h_img=W5 * 1080 / 1920)
X = 9.25
steps = [
    ("1", "Tian Shan, China", "#1 · 60 % similar · closest lunar twin: Shackleton", ACCENT),
    ("2", "Where it breaks", "the card lists what the place lacks", ACCENT),
    ("10", "Meteor Crater, USA", "known reference · 46 % similar", MOON),
]
for i, (n_, head, sub, col) in enumerate(steps):
    y = 1.95 + i * 1.5
    num(s, n_, X, y, d=0.55, fill=col, size=17 if len(n_) > 1 else 19)
    text(s, X + 0.75, y - 0.02, 3.0, 1.4, [[(head, {"font": TITLE_FONT, "bold": True, "size": 24})],
                                          [(sub, {"size": 14.5, "color": MUTED})]], gap=0.1)
caption(s, f"Live: {APP_URL} · backup: screenshot of the same view", y=6.75)
notes(s, "Speaker B (Sofi) · LIVE DEMO · ~50 s (browser open on the app, already scrolled past the Earthrise screen)",
      "This is our app, live. Every dot on the globe is a ranked crater. "
      "[Click #1 in the list] Number one: a bowl in the Tian Shan mountains in China. 60 percent similar, and its "
      "closest lunar twin is Shackleton itself. Its walls are as steep as Shackleton's. "
      "[Scroll the card to 'What it lacks'] The card also says honestly where the analogy breaks. "
      "[Click Meteor Crater, #10] Meteor Crater, a known training site we used for tuning, ranks tenth. "
      "[Back to the slides]")

# ---------- 6. What we learned ----------
s = new_slide()
title(s, "What we learned", "Earth can copy the shape, not the light")
framed(s, IMG / "scatter.png", 0.72, 1.85, w=6.2, h_img=6.2 * 800 / 1047)
X = 7.55
items = [
    ("Shape twins are not light twins", "No place scores high on both", SIGNAL),
    ("Earth has no grazing Sun", "Shackleton floor: always in shadow · typical Earth floor: 16.5 %", ACCENT),
    ("Mare: flat ground is common", "Basalt and small-crater texture are rare", WARN),
]
for i, (head, sub, col) in enumerate(items):
    y = 1.9 + i * 1.6
    num(s, i + 1, X, y + 0.04, d=0.55, fill=col)
    text(s, X + 0.8, y, 4.4, 1.5, [[(head, {"font": TITLE_FONT, "bold": True, "size": 25})],
                                   [(sub, {"size": 16, "color": MUTED})]], gap=0.15)
caption(s, "Scatter: 1,261 ranked Polar places, screenshot of our app. Mare: 392 of 500 places have no small "
           "craters (Moon: all 20 cells have some); 0 of 500 are basalt at the site (Macrostrat).")
notes(s, "Speaker B (Sofi) · ~25 s",
      "Three lessons. Shape twins are not light twins: no place scores high on both. Earth has no grazing Sun: "
      "Shackleton's floor is always in shadow, a typical Earth crater floor only 16.5 percent of the time. And for "
      "mare plains, flat ground is common, but basalt and small craters are rare.")

# ---------- 7. Limits + explore it yourself ----------
s = new_slide()
title(s, "Honest limits", "Explore it yourself")
label(s, 0.6, 1.85, "Known analogs we missed, and why", color=MUTED, w=7)
rows = [
    ("Haughton, Canada", "eroded: no closed bowl in the elevation data"),
    ("Askja, Iceland", "caldera lake looks flat: 48 m deep, below our 50 m minimum"),
    ("Lanzarote, Spain", "sea and village buffers: 0 of 16 cells pass the land filter"),
]
for i, (site, why) in enumerate(rows):
    y = 2.35 + i * 1.4
    box(s, 0.6, y, 6.9, 1.18)
    text(s, 0.9, y + 0.15, 6.4, 0.95, [[(site, {"font": TITLE_FONT, "bold": True, "size": 24, "color": WARN})],
                                      [(why, {"size": 16})]], gap=0.1)
box(s, 7.95, 1.85, 4.8, 5.05, fill=PANEL2, line=SIGNAL, weight=2, radius=0.05)
box(s, 8.6, 2.1, 3.5, 3.5, fill=TEXT, line=None, radius=0.04)
pic(s, IMG / "qr_app.png", 8.75, 2.25, w=3.2, h=3.2)
text(s, 7.95, 5.75, 4.8, 1.1, [[("Scan to open the app on your phone", {"font": TITLE_FONT, "bold": True,
                                                                       "size": 22})],
                               [(APP_URL, {"size": 14, "color": SIGNAL})]], align=PP_ALIGN.CENTER, gap=0.15)
notes(s, "Speaker B (Sofi) · ~14 s",
      "We also show what we miss: Haughton is eroded, Askja's lake hides its depth, Lanzarote is mostly sea and "
      "villages. Scan the code and explore it on your own phone. Thank you!")

out = HERE / "Moon_Twins_on_Earth.pptx"
prs.save(out)
print("saved", out)
