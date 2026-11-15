"""Build pitch/Moon_Twins_on_Earth.pptx (7 slides, 16:9) with python-pptx.

Run from the repo root:  python pitch/build_deck.py
Numbers come from docs/MORNING_REPORT.md, docs/JURY_FAQ.md, docs/MARE_V11.md, docs/MACROSTRAT_REPORT.md,
docs/VALIDATION_config-v1.md, docs/FACT_CHECK.md and outputs/scores.csv (see pitch/SCRIPT.md, "Sources").
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"

BG = RGBColor(0x0B, 0x1B, 0x2B)
PANEL = RGBColor(0x13, 0x2B, 0x40)
TEXT = RGBColor(0xF2, 0xF4, 0xF7)
MUTED = RGBColor(0xA9, 0xBC, 0xCF)
TEAL = RGBColor(0x3C, 0xC6, 0xA8)
GOLD = RGBColor(0xF2, 0xC1, 0x4E)
CORAL = RGBColor(0xFF, 0x8A, 0x5B)
BLACK = RGBColor(0, 0, 0)
FONT = "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    return s


def text(s, x, y, w, h, runs, size=20, color=TEXT, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         name=None):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, {size,color,bold}) tuples."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    paras = [runs] if isinstance(runs, str) else runs
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if i and size < 40:   # big titles: plain line break, no extra gap
            p.space_before = Pt(size * 0.45)
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.color.rgb = o.get("color", color)
    return tb


def box(s, x, y, w, h, fill=PANEL, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1.5)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = 0.08
    sh.shadow.inherit = False
    return sh


def pic(s, path, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    return s.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def title(s, t, sub=None):
    text(s, 0.6, 0.45, 12.1, 0.8, t, size=40, bold=True, name="Title")
    if sub:
        text(s, 0.6, 1.25, 12.1, 0.5, sub, size=20, color=MUTED)


def num(s, n, x, y, d=0.5, fill=GOLD):
    c = box(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(18), True, BG


def caption(s, t, y=7.0):
    text(s, 0.6, y, 12.1, 0.3, t, size=11, color=MUTED)


SCRIPT = {}  # filled from SCRIPT.md-style text below, used as speaker notes


def notes(s, who, words):
    s.notes_slide.notes_text_frame.text = f"{who}\n\n{words}"


# ---------- 1. Title ----------
s = new_slide(BLACK)
pic(s, IMG / "earthrise_16x9.jpg", 0, 0, w=13.333)
text(s, 0.7, 0.6, 5.6, 2.0, ["Moon Twins", "on Earth"], size=56, bold=True)
text(s, 0.7, 2.6, 5.4, 1.0, "Where on Earth can we rehearse a Moon base?", size=24, color=MUTED)
text(s, 0.7, 3.8, 5.9, 1.2, [[("[TEAM NAMES]", {"bold": True, "color": GOLD})],
                           "Team EspaceOdyssey", "NASA Space Apps Challenge 2026"], size=20)
text(s, 9.0, 0.35, 4.0, 0.3, "Earthrise · NASA / Apollo 8 (AS08-14-2383)", size=11, color=MUTED,
     align=PP_ALIGN.RIGHT)
notes(s, "Speaker A (Caspar) · ~15 s",
      "Hi, we are Team EspaceOdyssey. This is Earthrise, photographed by Apollo 8 from lunar orbit. "
      "Today we turn that view around: we look for the Moon's twins on Earth.")

# ---------- 2. The question ----------
s = new_slide()
title(s, "Where on Earth can we rehearse a Moon base?")
box(s, 0.6, 1.9, 5.8, 3.9)
text(s, 0.95, 2.2, 5.1, 3.4, [
    [("Today", {"bold": True, "color": CORAL, "size": 28})],
    "Analog sites are hand-picked by eye",
    "Poorly characterized: nobody measured how Moon-like they are",
    [("Haughton · Meteor Crater · Iceland", {"color": MUTED, "size": 18})],
], size=22)
box(s, 6.9, 1.9, 5.8, 3.9, line=TEAL)
text(s, 7.25, 2.2, 5.1, 3.4, [
    [("Our approach", {"bold": True, "color": TEAL, "size": 28})],
    "A systematic search of Earth",
    "Open NASA and ESA data only",
    "Measured criterion by criterion against real lunar sites",
], size=22)
pic(s, IMG / "lunar_horizon_strip.jpg", 0, 6.15, w=13.333)
notes(s, "Speaker A (Caspar) · ~25 s",
      "Before astronauts build a base on the Moon, they rehearse on Earth. But today's analog sites "
      "were picked by eye, and nobody measured how Moon-like they really are. So we asked: where on Earth "
      "can we rehearse a Moon base? And we searched systematically, with open data only.")

# ---------- 3. Method ----------
s = new_slide()
title(s, "One ruler for two worlds")
# Moon side
pic(s, IMG / "moon_globe.png", 0.6, 1.6, h=2.9)
text(s, 0.6, 4.65, 4.2, 1.9, [
    [("MOON · NASA data", {"bold": True, "color": GOLD})],
    "LOLA + PGDA: Shackleton and 2 craters in Artemis III regions",
    "SLDEM2015: 20 mare cells",
], size=18)
# middle
box(s, 4.95, 2.35, 3.45, 1.45, fill=TEAL)
text(s, 4.95, 2.35, 3.45, 1.45, [[("Same code", {"bold": True, "size": 26, "color": BG})],
                                 [("same 60 m grid", {"size": 20, "color": BG})]],
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, 4.95, 4.1, 3.45, 1.4, [[("Score per criterion", {"bold": True})],
                               [("1 = same as the Moon", {"color": MUTED})]], size=18, align=PP_ALIGN.CENTER)
for x0, x1 in ((4.0, 4.85), (8.5, 9.35)):
    a = s.shapes.add_shape(MSO_SHAPE.LEFT_RIGHT_ARROW,
                           Inches(x0), Inches(2.85), Inches(x1 - x0), Inches(0.45))
    a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
# Earth side
pic(s, IMG / "earth_globe.png", 9.45, 1.6, h=2.9)
text(s, 8.9, 4.65, 3.9, 1.9, [
    [("EARTH · open data", {"bold": True, "color": TEAL})],
    "Copernicus DEM (30 m elevation)",
    "ESA WorldCover (land cover)",
], size=18)
caption(s, "Moon: NASA LOLA LDEM_80S_20MPP_ADJ, PGDA illumination map, SLDEM2015 (PGDA). "
           "Earth: Copernicus DEM GLO-30, ESA WorldCover 2021. Globes: screenshots of our app.")
notes(s, "Speaker A (Caspar) · ~30 s",
      "On the Moon we measured Shackleton crater at the south pole and two craters in Artemis III landing "
      "regions, from NASA's LOLA elevation and PGDA light data. For mare plains we used SLDEM2015. On Earth "
      "we used the Copernicus elevation model and ESA WorldCover. Same code on both worlds, on the same "
      "60-metre grid. Every criterion gets a score: one means identical to the Moon.")

# ---------- 4. The search ----------
s = new_slide()
title(s, "We searched ~265,000 places in one night")
pic(s, IMG / "funnel.png", 0.6, 1.55, h=5.3)
X = 8.75
for i, (big, small, col) in enumerate((("~265,000", "cells of 15 km searched", TEXT),
                                       ("1,825", "crater-like places scored", TEXT),
                                       ("1,261", "Polar places ranked", TEAL))):
    text(s, X, 1.6 + i * 1.25, 4.0, 1.2, [[(big, {"size": 44, "bold": True, "color": col})],
                                          [(small, {"size": 18, "color": MUTED})]], size=18)
box(s, X - 0.2, 5.4, 4.3, 1.45, line=CORAL)
text(s, X, 5.5, 3.95, 1.3, [[("111 open-pit mines", {"bold": True, "color": CORAL, "size": 24})],
                            "found and filtered out, e.g. Chuquicamata and Escondida (Chile)"], size=17)
caption(s, "Funnel: screenshot of our app. Mine filter: Maus et al. 2022 mining polygons. "
           "Cell size ≈ an Artemis III candidate region (NASA, 2022).", y=7.0)
notes(s, "Speaker A (Caspar) · ~25 s",
      "In one night we searched about 265,000 cells of 15 kilometres, the size of an Artemis III landing "
      "region. 1,825 crater-like places were scored. Our bowl finder was so good it also found 111 open-pit "
      "mines, like Chuquicamata and Escondida. We filter them out. That leaves 1,261 ranked places. "
      "Sofi, the results.")

# ---------- 5. Results ----------
s = new_slide()
title(s, "Our #1: a crater bowl in the Tian Shan")
pic(s, IMG / "map_top_polar.png", 0.6, 1.5, w=7.4)
box(s, 8.35, 1.5, 4.4, 2.9, line=GOLD)
num(s, 1, 8.6, 1.75, d=0.6)
text(s, 9.35, 1.72, 3.3, 0.7, [[("Tian Shan, China", {"bold": True, "size": 24})]])
text(s, 8.6, 2.5, 4.0, 1.9, [
    [("60 %", {"bold": True, "size": 44, "color": GOLD}), ("  similar", {"size": 20, "color": MUTED})],
    "Closest lunar twin: Shackleton",
    [("Walls 27.3° vs 27.2° on the Moon", {"size": 17, "color": MUTED})],
], size=19)
box(s, 8.35, 4.65, 4.4, 1.55)
num(s, 10, 8.6, 4.9, d=0.6, fill=TEXT)
text(s, 9.35, 4.85, 3.3, 1.3, [[("Meteor Crater, USA", {"bold": True, "size": 22})],
                               [("Known reference (tuning site)", {"size": 17, "color": MUTED})],
                               [("46 % similar", {"size": 17, "color": MUTED})]])
caption(s, "Top Polar list and globe: screenshot of our app (heatmap = similarity to Shackleton).", y=5.5)
notes(s, "Speaker B (Sofi) · ~25 s",
      "Here is the map. Number one is a bowl in the Tian Shan mountains in China: 60 percent similar, and its "
      "closest lunar twin is Shackleton itself. Its walls are as steep as Shackleton's. Meteor Crater, a known "
      "training site we used for tuning, ranks tenth.")

# ---------- 6. What we learned ----------
s = new_slide()
title(s, "What we learned")
pic(s, IMG / "scatter.png", 0.6, 1.5, h=5.0)
X = 7.55
items = [
    ("Shape twins are not light twins", "No place scores high on both", TEAL),
    ("Earth has no grazing Sun", "Shackleton floor: always in shadow · typical Earth floor: 16.5 %", GOLD),
    ("Mare: flat ground is common", "Basalt and small-crater texture are rare", CORAL),
]
for i, (head, sub, col) in enumerate(items):
    y = 1.55 + i * 1.8
    num(s, i + 1, X, y + 0.05, d=0.55, fill=col)
    text(s, X + 0.8, y, 4.4, 1.6, [[(head, {"bold": True, "size": 24})], [(sub, {"size": 18, "color": MUTED})]])
caption(s, "Scatter: 1,261 ranked Polar places, screenshot of our app. Mare: 392 of 500 places have no small "
           "craters (Moon: all 20 cells have some); 0 of 500 are basalt at the site (Macrostrat).", y=6.95)
notes(s, "Speaker B (Sofi) · ~30 s",
      "Three lessons. One: places shaped like Shackleton are not lit like Shackleton. No place scores high on "
      "both. Two: Earth has no grazing Sun. Shackleton's floor is always in shadow; a typical Earth crater "
      "floor only 16.5 percent of the time. Three: for mare plains, flat ground is easy to find, but basalt "
      "and the Moon's small craters are rare.")

# ---------- 7. Limits + try it ----------
s = new_slide()
title(s, "Honest limits, open results")
rows = [
    ("Haughton, Canada", "eroded: no closed bowl in the elevation data"),
    ("Askja, Iceland", "caldera lake looks flat: 48 m deep, below our 50 m minimum"),
    ("Lanzarote, Spain", "sea and village buffers: 0 of 16 cells pass the land filter"),
]
text(s, 0.6, 1.55, 7.6, 0.5, [[("Known analogs we missed, and why", {"color": MUTED})]], size=20)
for i, (site, why) in enumerate(rows):
    y = 2.2 + i * 1.35
    box(s, 0.6, y, 7.7, 1.15)
    text(s, 0.9, y + 0.15, 7.2, 0.9, [[(site, {"bold": True, "size": 22, "color": CORAL})],
                                     [(why, {"size": 18})]])
box(s, 8.85, 1.55, 3.9, 5.25, fill=TEXT)
pic(s, IMG / "qr_app.png", 9.25, 1.8, w=3.1)
text(s, 8.95, 5.05, 3.7, 1.6, [[("Try it live", {"bold": True, "size": 24, "color": BG})],
                               [("tlcaspars.github.io/EspaceOdyssey/app/", {"size": 15, "color": BG})]],
     align=PP_ALIGN.CENTER)
notes(s, "Speaker B (Sofi) · ~20 s",
      "We also show what we miss. Haughton is too eroded. At Askja, the lake makes the caldera look too "
      "shallow. Lanzarote is mostly sea and villages. Every score is open in our app. Scan the code and find "
      "your own Moon twin. Thank you!")

out = HERE / "Moon_Twins_on_Earth.pptx"
prs.save(out)
print("saved", out)
