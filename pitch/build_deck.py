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
PRODUCT = "Moon Twins on Earth"          # product name: change here only (title, file name, document title)
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
_w = PRODUCT.split()
text(s, 0.7, 0.95, 5.8, 2.3, [[(" ".join(_w[:2]), {"font": TITLE_FONT, "bold": True})],
                              [(" ".join(_w[2:]), {"font": TITLE_FONT, "bold": True})]], size=66, gap=0)
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
           "ESA WorldCover 2021. Globes: NASA Blue Marble and CGI Moon Kit (LRO). Dots: demo place (Tibesti), Shackleton.")
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
for i, (big, small, col) in enumerate((("1,825", "crater-like places (closed depressions) scored", MOON),
                                       ("1,261", "Polar places ranked", SIGNAL))):
    text(s, X, 1.7 + i * 1.5, 4.4, 1.4, [[(big, {"font": TITLE_FONT, "size": 44, "bold": True, "color": col})],
                                         [(small, {"size": 16, "color": MUTED})]], gap=0)
box(s, X, 4.45, 4.35, 1.1, fill=PANEL2, line=WARN, weight=1.75)
text(s, X + 0.25, 4.52, 3.9, 1.0, [[("111 open-pit mines", {"font": TITLE_FONT, "bold": True, "color": WARN,
                                                           "size": 24})],
                                  "found and filtered out, e.g. Chuquicamata and Escondida"], size=14.5, gap=0.1)
box(s, X, 5.7, 4.35, 1.15, fill=PANEL2, line=SIGNAL, weight=1.75)
text(s, X + 0.25, 5.8, 3.9, 1.0, [[("Known impact craters", {"font": TITLE_FONT, "bold": True, "color": SIGNAL,
                                                             "size": 24})],
                                  "flagged, incl. Pingualuit in the world search"], size=14.5, gap=0.1)
caption(s, "Funnel: screenshot of our app. Mine filter: Maus et al. 2022 mining polygons. Impact flag: list of 88 "
           "confirmed structures. Cell size ≈ an Artemis III candidate region (NASA, 2022).")
notes(s, "Speaker A (Caspar) · ~26 s",
      "In one night we searched about 265,000 cells, each the size of an Artemis III landing region. 1,825 crater-like places, closed depressions, were scored. It even found 111 open-pit mines; we filtered them out, and 1,261 places remain. It also flags known impact craters, including Pingualuit in the world search. Sofi will show you.")

# ---------- 5. Live demo ----------
s = new_slide()
title(s, "Live demo", "One place, one datasheet: Tibesti, Chad")
W5 = 8.0
H5 = W5 * 1080 / 1920
pad = 0.12
box(s, 0.72 - pad, 1.9 - pad, W5 + 2 * pad, H5 + 2 * pad, fill=PANEL, radius=0.03)
s.shapes.add_movie(str(IMG / "demo.mp4"), Inches(0.72), Inches(1.9), Inches(W5), Inches(H5),
                   poster_frame_image=str(IMG / "demo_poster.jpg"), mime_type="video/mp4")
X = 9.25
steps = [
    ("1", "Fly into 3D", "the teal ring is the bowl we scored"),
    ("2", "Radar fingerprint", "every criterion against Shackleton, the outer ring"),
    ("3", "Closest lunar twin", "Shackleton, 48 %, and what the place lacks: the light"),
]
for i, (n_, head, sub) in enumerate(steps):
    y = 1.95 + i * 1.5
    num(s, n_, X, y, d=0.55, fill=ACCENT, size=19)
    text(s, X + 0.75, y - 0.02, 3.0, 1.4, [[(head, {"font": TITLE_FONT, "bold": True, "size": 24})],
                                          [(sub, {"size": 14.5, "color": MUTED})]], gap=0.1)
caption(s, f"Live: {APP_URL} · video: recorded from the live app, the fallback if the demo fails", y=6.75)
notes(s, "Speaker B (Sofi) · LIVE DEMO · ~50 s (browser open on the app, scrolled past the Earthrise screen, "
         "globe loaded). Fallback: click the video on this slide and say the same words.",
      "This is our app, live. Every dot is a crater-like place, a closed depression we ranked. "
      "[Click '54 km SW of Bardaï' in the Earth twins list] Let's fly to the Tibesti mountains in Chad. "
      "[Wait until the 3D terrain and the teal ring appear] Here it is in 3D. The teal ring is the bowl we scored. "
      "[Scroll down to the datasheet] Its datasheet. The radar compares every criterion with Shackleton, the outer "
      "ring. Steep walls and the flat base spot match well. Its closest lunar twin is Shackleton, at 48 percent. "
      "And it says honestly what it lacks: the light. "
      "[Scroll back up, then back to the slides]")

# ---------- 6. What we learned ----------
s = new_slide()
title(s, "What we learned", "Earth can copy the shape, not the light")
framed(s, IMG / "scatter.png", 0.72, 1.85, w=6.2, h_img=6.2 * 800 / 1047)
X = 7.55
items = [
    ("Shape twins are not light twins", "No place scores high on both", SIGNAL),
    ("Earth has no grazing Sun", "Shackleton floor: always in shadow · typical Earth floor: 16.5 %", ACCENT),
]
for i, (head, sub, col) in enumerate(items):
    y = 1.95 + i * 1.75
    num(s, i + 1, X, y + 0.04, d=0.6, fill=col, size=20)
    text(s, X + 0.85, y, 4.35, 1.6, [[(head, {"font": TITLE_FONT, "bold": True, "size": 28})],
                                     [(sub, {"size": 17, "color": MUTED})]], gap=0.15)
box(s, X, 5.6, 5.2, 0.95, fill=PANEL, radius=0.1)
text(s, X + 0.25, 5.6, 4.8, 0.95, [[("Mare: ", {"bold": True, "color": WARN}),
                                    ("flat plains are common; only 1 of 500 reaches the Moon's small-crater density",
                                     {})]], size=15, anchor=MSO_ANCHOR.MIDDLE)
caption(s, "Scatter: 1,261 ranked Polar places, screenshot of our app. Small-crater density: 500 Earth Mare places "
           "vs the median of 20 lunar mare cells.")
notes(s, "Speaker B (Sofi) · ~25 s",
      "Shape twins are not light twins: no place scores high on both. And Earth has no grazing Sun: "
      "Shackleton's floor is always in shadow, a typical Earth crater floor only 16.5 percent of the time. "
      "For mare plains, flat ground is common, but only 1 of 500 places reaches the Moon's small-crater density.")

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

prs.core_properties.title = PRODUCT
prs.core_properties.author = "Team EspaceOdyssey"
out = HERE / f"{PRODUCT.replace(' ', '_')}.pptx"
prs.save(out)
print("saved", out)
