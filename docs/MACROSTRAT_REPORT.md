# Macrostrat: rock at the site for the 500 Mare places

15 Nov 2026, branch `macrostrat-rock`. **Display only:** no score, rank or config changed, no new night run.
Source: **Macrostrat (macrostrat.org), CC BY 4.0** (every API response carries `"license": "CC-BY 4.0"`).

## Short answer
Coverage is **not good enough** for `BASALT_SITE` to count in a mare-v1.1.

- 208 of 500 places (42 %) get **no map unit** at large, medium or small scale. That includes every place in
  China (133) and Mongolia (43).
- Of the 292 places with an answer, 236 (81 %) come from **small-scale** maps (continental compilations). Only
  56 places (11 % of 500) have a medium- or large-scale map.
- **No place is flagged basalt at the site** (0 of 500). 245 are "clearly something else", 255 are empty.

## What was done
- Points: the 500 Mare base spots (`base_lon` / `base_lat` in `out/night_mare/ranking.csv`).
- API: `https://macrostrat.org/api/v2/geologic_units/map?lat=..&lng=..&scale=large`, then `medium`, then `small`
  until a unit comes back. The scale that answered is recorded. Source map names come from
  `/api/v2/defs/sources?source_id=..`.
- Code: `src/pipeline/macrostrat.py` (client, parser, basalt rule, export helpers), `src/compute_macrostrat.py`
  (`--runs mare` by default; `--runs mare polar` is ready for later), result in `data/macrostrat/rock_site.csv`
  (`run, cell, lon, lat, ROCK_SITE, ROCK_SITE_LITH, ROCK_SITE_SOURCE, ROCK_SITE_SCALE, BASALT_SITE, N_UNITS, SOURCE_ID`).
- Cache: one JSON file per request in `<LOCALAPPDATA or home>/espaceodyssey_data/macrostrat_cache`. At most
  3 requests per second (shared by 4 workers), retries with backoff, restart continues from the cache. This was
  used for real: the first run was stopped after 137 requests and the second run picked them up.

### Rules (choices made here, please review)
1. **Which unit, when several maps overlap** (114 of the 292 answers have more than one unit): the **youngest**
   unit is used (smallest top age, then smallest base age, then first in the response). Reason: the surface rock
   is the youngest unit; an overlapping basement map is older. Macrostrat gives no "surface" marker.
2. **`BASALT_SITE`**, from the unit's lithology text (only the `Major:{..}` part when the map separates major and
   minor rocks); if that text is empty or names no composition (e.g. "volcanic"), the unit name decides:
   - **1**: basalt, basanite, tholeiite, hawaiite, mugearite, picrite, nephelinite, or "mafic / basic volcanic".
     A unit that lists basalt together with other rocks counts as 1. "Metabasalt" does not count (metamorphic).
   - **0**: a clear other rock (granite, gneiss, sandstone, limestone, rhyolite, andesite, sand, alluvium, gabbro …).
   - **empty**: no unit, or nothing recognisable ("volcanic", "tuff", "undifferentiated"). Never 0 for missing.
   - A unit description never decides the flag (it is only shown as `ROCK_SITE_LITH` when the lithology is empty).

## Results
| ROCK_SITE_SCALE | places | BASALT_SITE = 1 | = 0 | empty |
|---|---|---|---|---|
| large | 4 | 0 | 4 | 0 |
| medium | 52 | 0 | 23 | 29 |
| small | 236 | 0 | 218 | 18 |
| no answer | 208 | 0 | 0 | 208 |
| **all** | **500** | **0** | **245** | **255** |

- Empty = 208 without a unit + 47 with a unit that names no clear rock.
- No answer by country: China 133, Mongolia 43, Pakistan 13, Yemen 9, Oman 4, Uzbekistan 3, Russia 1, Iran 1,
  Saudi Arabia 1.
- Source maps of the 292 answers (Macrostrat names): Africa 157, Arctic 26, Europe 1:5M 25, GMNA 23, Iran 17,
  Rae Craton and Queen Maud Block NU 14, Afghanistan 8, Geological Map of South America 2018 5, South Africa 4,
  State Geologic Map Compilation 4, Geologic Map of Arizona 2, Mexico 2, and one each: Vernal UT, Geologic Map of
  Nevada, S. Ellef Ringnes Island NU, Albuquerque Quad NM, Moab UT. The "Africa" map is the 1:10,000,000
  geological map of Africa (CGMW-BRGM, per its reference in the API) and also answers for the Arabian Peninsula.
- The most common answer is one word from that map: "sedimentary" (116 places).

### Agreement with the GLiM 0.5° flag (`BASALT_REGION` in `outputs/raw_values.csv`)
| GLiM `BASALT_REGION` | site = 1 | site = 0 | site empty | all |
|---|---|---|---|---|
| 1 (basalt) | 0 | 3 | 6 | 9 |
| 0 | 0 | 230 | 246 | 476 |
| no data | 0 | 12 | 3 | 15 |

- Both flags exist for 233 places: **230 agree (both 0), 3 disagree** (GLiM basalt, site not basalt).
- Of the 9 GLiM basalt places: 3 have no Macrostrat unit, 3 have a unit that only says "volcanic" or "andesitic
  lava flows" (empty), 3 are "0" (sedimentary ×2, intrusive ×1). So Macrostrat confirms none of them.
- Macrostrat gives a clear "0" for 12 of the 15 places where GLiM has no data (coasts).

### Five examples
Links open Google Earth at the base spot.

| Place (Mare rank row) | Macrostrat | GLiM | Note |
|---|---|---|---|
| [58 km SE of Bardaï, Chad](https://earth.google.com/web/@21.11971,17.50362,0a,20000d,35y,0h,0t,0r) | "volcanic" (Africa, small) → empty | vb | Tibesti. Both say volcanic; the 1:10M map gives no composition, so no basalt flag. |
| [26 km W of Sonoyta, Mexico](https://earth.google.com/web/@31.93547,-113.10773,0a,20000d,35y,0h,0t,0r) | "sedimentary" (Mexico, medium) → 0 | vb | Disagreement. The spot lies just east of the Pinacate tuning box (−113.8…−113.2); GLiM gives one class per 55 km cell, the map unit at the pad is sedimentary. Not checked on imagery. |
| [181 km W of Bayan Nur, Gobi](https://earth.google.com/web/@41.08274,105.28087,0a,20000d,35y,0h,0t,0r) | no answer | vb | China: no Macrostrat map at these three scales. |
| [99 km W of Bīrjand, Iran](https://earth.google.com/web/@33.1502,58.21828,0a,20000d,35y,0h,0t,0r) | "Oligocene andesitic lava flows" (Iran, medium) → empty | vb | Lava, but andesitic, and only in the description; the rule leaves it empty. |
| [48 km SE of Vernal, Utah](https://earth.google.com/web/@40.0558,-109.3041,0a,20000d,35y,0h,0t,0r) | "mixed alluvium and colluvium" (Vernal UT, large) → 0 | ss | What a large-scale map gives: the real surface deposit at the pad. Only 4 places have this. |

## Download size
- **338,900 bytes** of response bodies in total (HTTP headers not counted): 1,457 cached responses = 1,440 map
  lookups + 17 source names. On disk the cache is 5.7 MB (one small file per request).
- Plus about 10 test requests by hand while building (under 15 kB), not in the cache.
- Run time: roughly 15–20 minutes for the 500 places (two sessions). The server answered in ~0.5 s per request, with slower stretches.

## Is it good enough for a later mare-v1.1? No.
1. **42 % without any answer**, and the gap is regional (all of China and Mongolia = 35 % of the Mare list). A
   scored criterion would be "no data" for a third of the candidates in one block.
2. **Mostly not fine-scale.** 236 of 292 answers are small-scale; the 1:10M Africa map alone gives 157. That is
   no finer than the GLiM 0.5° grid in practice. Site-level answers (medium + large) exist for 56 places.
3. **It finds no basalt.** With 0 of 500 flagged, the criterion would only ever lower a score or be empty.
   Either the Mare list holds almost no basalt plains (GLiM says 9 of 500), or the maps cannot show them; this
   data cannot tell which.
4. The flag depends on free text in ~17 different map legends. The rule above is simple and was checked by
   reading the outputs once (it caught "metabasalt"), not validated against field data.

Useful as it is: a **display line** on the card where a medium or large map exists, and a second opinion on the
GLiM flag (e.g. Sonoyta).

Possible next steps, not done: (a) Macrostrat also has a `tiny` scale (one test point without large/medium/small
had a `tiny` unit), which would fill gaps but is world-map level; (b) national geological maps for China and
Mongolia; (c) run `--runs polar` if wanted (1,825 places, so roughly 3–4 times the requests and download of Mare).

## Export and app
- `src/export_app.py --macrostrat data/macrostrat/rock_site.csv` adds the five columns at the end of
  `raw_values.csv` (join on `RUN` + `CELL`), `targets.json` → `_rock_site` (`score_method: "display"`, the note),
  and a section with the credit in `outputs/README.md`.
- **The full re-export with the command from docs/NIGHT_RUN.md could not be run on this machine.** It needs
  `out/meteor_crater`, `out/pinacate`, the mining polygons, Natural Earth, GeoNames and the GLiM grid, none of
  which are in the repo or on this Mac. Instead:
  - The option was checked on the two runs that are in the repo: export without and with `--macrostrat` →
    `raw_values.csv` identical after removing the five new fields (same SHA-256), `scores.csv`, `heatmap.json`,
    `cells.json`, `regions.json`, `coverage.json` byte-identical, `targets.json` differs only by `_rock_site`.
  - The committed `outputs/` were updated with `src/add_macrostrat_to_outputs.py`, which uses the same functions
    and only appends: all 2,329 lines of the old `raw_values.csv` are byte-exact prefixes of the new lines;
    `targets.json` is unchanged except for the new key; `scores.csv` and the other files were not touched.
  - Whoever has the inputs can run the documented command plus `--macrostrat data\macrostrat\rock_site.csv`; the
    result should match what is committed here.
  - **Second attempt, same day:** the public inputs were downloaded (mining polygons, Natural Earth, GeoNames,
    GLiM grid) and `meteor_crater` / `pinacate` were run again, then the documented command plus `--macrostrat`
    was run into a scratch folder (not into `outputs/`). Compared with the committed files:
    - `targets.json` is byte-identical; `raw_values.csv` and `scores.csv` have the same columns and the same
      2,328 rows. For the 2,325 night-run rows every column is identical (scores, GLiM, names, post-filters and
      the five Macrostrat columns) **except** the impact columns and 4 ranks.
    - What differs, and why it was not copied into `outputs/`: (1) the impact list
      (`data/impact/impact_structures.csv`) is not on this machine, so all impact values come out empty;
      (2) the re-run `meteor_crater` and `pinacate` cells score slightly differently from the committed ones
      (Meteor Crater 0.458 instead of 0.462, Pinacate r002c001 0.1784 instead of 0.1783; cause not looked into),
      which moves 4 night ranks; (3) the night runs' `cells.geojson` are not in the repo, so `cells.json` and
      `coverage.json` come out almost empty (14 cells / 6 tiles instead of 6,320 / 11,604).
    - So the complete re-export still has to be run on the machine that holds the full `out/` folder and the
      impact list. The committed `outputs/` stay as updated by `add_macrostrat_to_outputs.py`.
- App (`app/app.js`, `app/style.css`): the four text columns are read as text; Mare cards show
  "Rock at site: <lithology> (<source map>, <scale>-scale map)" and "Rock, regional: <GLiM class>, regional
  (0.5° map)" in the "On the ground" box; a "Basalt at site" badge appears when `BASALT_SITE` = 1 (no place has
  it today); the footer names "Macrostrat, CC BY 4.0". Checked locally at `/app/`: no console errors; cards for
  a large, medium, small and no-answer place show the expected lines; Polar cards show none. The badge was
  checked by setting the value in the browser's memory for one card, then resetting it.

## Tests
`tests/test_macrostrat.py` (39 tests, no network): basalt rule, unit choice, scale fallback, "no answer is empty,
never 0", cache / resume / retry with a fake network, export helpers, byte-exact append. Saved responses in
`tests/fixtures/macrostrat/` (15 Nov 2026). One of them (`idaho_medium.json`) is a point in the Craters of the
Moon lava field, the Mare tuning site: it is a geological-map lookup only, no pipeline run or result there.
