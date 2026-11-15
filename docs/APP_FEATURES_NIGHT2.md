## Agent report: three app features (night of 14–15 Nov 2026)
Status: done (all three), not merged. Branch `agent/app-features`, one commit per feature, so any of them can be
dropped on its own.

What I did:
- **Idea 2 · Opportunities & challenges** (commit 96de0be): for the five scored sites (Meteor Crater, El Elegante,
  Al Wahbah, Roter Kamm, Pinacate NW) the card now has a box with short "Opportunities" and "Challenges" lines.
  Every line ends with a source number `[n]` that links to the numbered source list, or with an "our data" tag
  when the value comes from our own pipeline (`outputs/raw_values.csv`, config-v1). It replaces "What we could
  test here" where it exists ("what to test" is now part of Opportunities). Meteor Crater keeps "How it has
  helped exploration" as well. Text lives in `app/sample/site_info.json` → `outlook`.
- **Idea 1 · Moon base to scale** (commit 57932a0): new button "Moon base to scale" in the 3D view. It draws a
  habitat (6.5 m) and a landing pad (24 m, blast zone 54 m) at real size on the flat spot our pipeline picked,
  and Shackleton's rim (20.9 km) around the crater. Two buttons in the caption: "Close-up of the base" and
  "Compare with Shackleton". Drawn by code, no images.
- **Idea 3 · Astronaut guide** (commit f49ef9a): a "Guide" button (bottom right, simple astronaut drawing, no
  logos) opens a panel with a 5-step tour (globe → list → card → Moon → honest limits), "What does it mean?" for
  every criterion of the selected base, and 7 ready-made questions. Answers are fixed text from our docs or
  computed from the loaded data. No AI runs in the app. All in `app/guide.js`.
- Also fixed two dead NASA links in the existing notes (they returned 404): the Haughton-Mars Project page and
  the ALSJ geology-training PDF, replaced by a NASA Earth Observatory page on HMP and the NASA report
  SP-2015-626 (Phinney, Science training history of the Apollo astronauts).
- Footer AI note: added that the guide's answers are pre-written text plus live numbers, with no AI in the app.

Files changed / created:
- `app/app.js` (outlook box; base layer in the 3D view), `app/style.css`, `app/index.html` (base button,
  `guide.js` script tag, AI note), `app/sample/site_info.json` (`outlook` + new sources), `app/guide.js` (new)
- `docs/APP_FEATURES_NIGHT2.md` (this file), `docs/ai_usage/app-features.md`

Tests:
- `node --check` on `app.js` and `guide.js`: OK.
- In the browser (Chromium in the desktop app): all five outlook boxes render with working `[n]` links; base
  layer at Meteor Crater, El Elegante, Al Wahbah and Roter Kamm, also when switching sites with the base on;
  "Compare with Shackleton" shows the ring; guide tour highlights all 5 parts; all 7 answers render with
  correct numbers; phone width (375 px): no sideways scrolling, all buttons reachable. No console errors.
- Every source URL in `site_info.json` checked: all open (a few sites block scripts with 403 but open in a
  browser; UNESCO checked in the browser).
- `src/export_app.py` only reads the site names from `site_info.json`, so the new `outlook` field doesn't
  affect it. (pytest isn't installed in this Python, so I didn't run the test suite; no Python file changed.)

Open points / needs a human decision:
- Keep all three, or drop some: each is one commit.
- The base layout (habitat 200 m from the pad) is our illustration; the caption says so. Change `spacing` in
  `BASE_SCALE` (app.js) if you prefer another distance.
- On a phone the 3D view gets crowded with the base on (the map is only ~380 px tall). It works, but the
  desktop is where it shines; worth showing it on a laptop at the pitch.

Unverified items (and why):
- Access facts can change: Pinacate blockades are from a Nov 2022 report, Tsau ǁKhaeb access from April 2021,
  Visit Saudi's "only through tour operators" page was updated April 2024. The lines give the year.
- Al Wahbah's size: published numbers disagree (2–3 km wide, 220–380 m deep); the challenge line says so.
- Landing pad 24/54 m comes from one study's illustration (Metzger & Autry 2022, "for illustration purposes"),
  not a NASA requirement. Habitat 6.5 m is NASA's 2022 reference design, not a final flight design.
- Not tested in Safari or Firefox.
- If tonight's run adds new scored sites, they get no outlook box (the old "What we could test here" box shows).

Data downloaded (size): none (only web pages and 3 PDFs read for checking, about 2.5 MB, not committed).

---

## Sources added (all opened and checked)

| Site | Source | Used for |
|---|---|---|
| Meteor Crater | Barringer Crater Company FAQ, barringercrater.com/faq | privately owned; visitors stay on rim paths, may not climb to the bottom (slopes erode, unstable) |
| Meteor Crater | Eos (2024), The art of doing fieldwork on the Moon | Artemis geology field camp at Meteor Crater or another analog; ~1 km vs lunar craters hundreds of km |
| Meteor Crater | NPR/KNAU (17 Jul 2025) | backpack lidar and ground-penetrating radar tested at the crater ahead of a Moon landing |
| Pinacate (both) | UNESCO World Heritage list 1410 | inscribed 2013; 10 large maar craters; whole property under CONANP |
| Pinacate (both) | USGS Open-File Report 2005-1190, Table 1 | Apollo training trips to Pinacate 1965–1967, Apollo 14 crew 14–18 Feb 1970 |
| Pinacate (both) | University of Arizona (2019) | Apollo astronauts trained for lunar exploration in the area |
| Pinacate (both) | KJZZ/Fronteras (17 Nov 2022) | blockades by communal landowners cut off parts of the reserve incl. visitor centre |
| Al Wahbah | Visit Saudi (official, updated 8 Apr 2024) | "accessible only through tour operators"; 3,000 m, ~380 m |
| Al Wahbah | Arab News (29 Jul 2026) | visitors descend to the salt floor; most visitors in winter and spring |
| Roter Kamm | ESA (2020) | in Tsau ǁKhaeb (Sperrgebiet) National Park; 2.5 km; ~5 million years |
| Roter Kamm | Nienhaus et al. (2022), CRC 1211 database | sand fill up to ~300 m, mapped with TEM/AMT |
| Roter Kamm | University of Cologne (23 Mar 2022) | rangers prohibited driving into the crater; measurements inside done on foot |
| Roter Kamm | Allgemeine Zeitung (12 Apr 2021) | limited access, a single tour concession licence |
| Base to scale | Burke, Howard & Kessler (2022), NASA NTRS 20220013669 | habitat inflatable part 6.5 m outer diameter |
| Base to scale | Metzger & Autry (2022), arXiv 2205.00378 | landing pad inner radius 12 m, outer 27 m (illustration values) |
| Base to scale | our LOLA measurement (`config/lunar_targets.json`) | Shackleton rim 20.9 km |
