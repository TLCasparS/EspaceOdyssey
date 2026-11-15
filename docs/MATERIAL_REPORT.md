# Material report: GLiM rock classes (unattended session, 15 Nov 2026)

Branch `material-glim` (worktree `EspaceOdyssey-glim`). No night run, no change to scores, configs, outputs or exports.
Method and limits: `docs/MATERIAL.md`.

## TL;DR
- **The full GLiM polygons were NOT downloaded.** The Dropbox link works (1.14 GB), but the file has **no licence statement**, and the hosting body's (CCGM) digital-map licence is paid, research-only and bans redistribution. Under the session rule ("licence not open → skip") I skipped it.
- **Fallback used:** the same dataset as a 0.5° grid from PANGAEA (CC-BY 3.0, 38 KB). This grid has the dominant class per ~55 km cell. It is fine for "basalt region yes/no" and **not** a real 5 km share.
- Rock class written for all 1,825 Polar and 500 Mare places. **Only 9 of 500 Mare base spots lie in a basalt (`vb`) cell.**
- Proposed c23 (weight 1.0, tolerance 0.5) moves those 9 to the top of Mare. **The team's "no data → renormalise" rule breaks here:** coastal no-data cells jump ahead of all non-basalt cells. This needs a team decision before c23 can count.

## 1. Dataset
| | Full polygons (wanted) | 0.5° grid (used) |
|---|---|---|
| Name | `LiMW_GIS 2015.gdb.zip` | Global Lithological Map Database v1.0 (gridded to 0.5°) |
| Source | Dropbox `https://www.dropbox.com/s/9vuowtebp9f1iud/LiMW_GIS%202015.gdb.zip`, linked from CSDMS (`csdms.colorado.edu/wiki/Alldata:GLiM`) and CCGM (`ccgm.org/en/?p=863`) | PANGAEA doi:10.1594/PANGAEA.788537 → `epic.awi.de/31092/1/hartmann-moosdorf_2012.zip` |
| Size | 1,138,691,332 bytes (HTTP header, 15 Nov 2026; not downloaded) | 38,670 bytes zip; 1,235,039 bytes ASCII grid |
| Licence | **none stated** on CSDMS, CCGM or the Uni Hamburg GLiM page; CCGM's only digital-map licence (`ccgm.org/en/licence-agreement-for-the-digital-maps-…`) = paid, education/research only, no redistribution | **CC-BY 3.0** (PANGAEA page) |
| Layer / class field | not verified (not downloaded); code assumes `xx` | ESRI ASCII 720 × 360, 0.5°, NODATA −9999; `Classnames.txt` columns `OBJECTID;Value_;Count_;xx`, `xx` = first-level code (16 values: su vb ss pb sm sc va mt pa vi wb py pi ev nd ig) |
| Stored | — | `%LOCALAPPDATA%\espaceodyssey_data\glim_pangaea_0p5deg\` (`raw\` zip, `extracted\` files) |

Cite: Hartmann, J., Moosdorf, N. (2012): The new global lithological map database GLiM. G3 13, Q12004, doi:10.1029/2012GC004370.

## 2. What was built
| file | what |
|---|---|
| `src/pipeline/material.py` | Rock class at a point + class shares within 5 km. STRtree spatial index, bbox/tile reads for polygon files, true circle per point (local AEQD). Sea and GLiM `nd` = no data, never 0 |
| `src/compute_rock_classes.py` | Runs on `out/night_polar` (low point) and `out/night_mare` (base spot) → `data/material/rock_classes.csv`. Switch to the polygons with `--gdb` |
| `src/mare_basalt_whatif.py` | c23 what-if table; changes no score |
| `tests/test_material.py` | 12 tests (synthetic polygons, boundary split vs analytic circular segment, sea, 80° N, NaN, projected GPKG via the file loader, ASCII grid). Full suite: 127 passed, 1 skipped (`pvlib` missing, unrelated) |
| `docs/MATERIAL.md` | method + limits |

`data/material/*.csv` is **git-ignored** (`data/`), so the CSVs are local only. Re-create them in under 5 s:
`python src/compute_rock_classes.py --out-root ..\EspaceOdyssey\out`, then `python src/mare_basalt_whatif.py --out-root ..\EspaceOdyssey\out [--only-with-c23] [--weight w]`.
Columns of `rock_classes.csv`: `run, rank, cell, lon, lat, point, ROCK_CLASS, covered_share, share_su … share_wb`.

## 3. Results: rock class at the point (0.5° grid)
| class | Polar (low point) | Mare (base spot) |
|---|---:|---:|
| su unconsolidated sediments | 843 | 130 |
| ss siliciclastic sedimentary | 178 | 80 |
| sm mixed sedimentary | 167 | 100 |
| sc carbonate sedimentary | 123 | 59 |
| py pyroclastics | 33 | 2 |
| ev evaporites | 9 | 1 |
| mt metamorphics | 61 | 51 |
| pa acid plutonic | 56 | 30 |
| pi intermediate plutonic | 11 | 8 |
| pb basic plutonic | 7 | 3 |
| va acid volcanic | 36 | 4 |
| vi intermediate volcanic | 92 | 8 |
| **vb basic volcanic** | **165** | **9** |
| ig ice and glaciers | 22 | 0 |
| wb water bodies | 6 | 0 |
| no data (sea / GLiM nd) | 16 | 15 |
| total | 1,825 | 500 |

- Mixed discs (largest share < 0.99): Polar 289, Mare 86. These are points near a 0.5° cell edge, not real 5 km mixes.
- Discs not fully covered: Polar 19, Mare 21 (coasts). Fully no data: Polar 4, Mare 7.
- `share_vb > 0`: Polar 211, Mare 12; `share_vb ≥ 0.5`: Polar 168, Mare 9.

### Polar: display only (criterion 22 not possible)
GLiM has **no anorthosite class**. Anorthosite sits inside the plutonic classes at the first level, so "highland-type rock" can't be scored. Polar top 20, rock class at the low point:

| rank | cell | lon | lat | rock class | largest share 5 km |
|---:|---|---:|---:|---|---|
| 1 | b098_r004c1291 | 74.984 | 46.990 | wb | wb 0.41 |
| 2 | b010_r000c516 | -73.813 | -49.084 | ig | ig 1.00 |
| 3 | b130_r002c105 | -84.443 | 81.464 | sm | sm 1.00 |
| 4 | b010_r002c517 | -74.038 | -48.813 | pa | pa 0.84 |
| 5 | b094_r004c1432 | 82.391 | 42.572 | py | py 1.00 |
| 6 | b028_r005c708 | -70.989 | -28.811 | pi | pi 1.00 |
| 7 | b029_r001c713 | -70.806 | -28.296 | su | su 1.00 |
| 8 | b085_r006c438 | -109.371 | 33.100 | va | va 1.00 |
| 9 | b039_r004c775 | -70.708 | -17.043 | pa | pa 1.00 |
| 10 | b007_r003c488 | -73.324 | -51.929 | py | py 1.00 |
| 11 | b087_r001c407 | -113.206 | 34.585 | ss | ss 1.00 |
| 12 | b059_r001c1611 | 37.706 | 4.270 | su | su 1.00 |
| 13 | b092_r002c358 | -116.716 | 40.249 | ss | ss 1.00 |
| 14 | b009_r003c505 | -74.647 | -49.758 | pa | pa 1.00 |
| 15 | b090_r001c1473 | 71.467 | 37.873 | sm | sm 0.85 |
| 16 | b032_r007c750 | -69.051 | -24.217 | sc | sc 1.00 |
| 17 | b014_r003c1851 | 168.774 | -44.369 | mt | mt 1.00 |
| 18 | b072_r001c1497 | 32.593 | 18.409 | mt | mt 1.00 |
| 19 | b091_r005c1254 | 39.149 | 39.500 | pb | pb 0.50 |
| 20 | b034_r006c763 | -68.900 | -22.287 | su | su 1.00 |

Polar #1 shows the coarseness: its low point gets "water bodies" because the 0.5° cell is mostly a large lake. I haven't checked whether the bowl itself is wet.

## 4. Proposal: Mare c23 basalt (mare-v1.1, post-run addition)
- raw = share of `vb` within 5 km of the base spot; **Moon value 1.0** (mare = basalt plain).
- score = exp(−((raw − 1.0) / tol)²), the same rule as the other Mare axes.
- **Team start values: weight 1.0** (equal to c9/c10/c12/c13, all 1.0 in mare-v1), **tolerance 0.5** (share 0.5 → 0.37, share 0 → 0.018).
- c23 = no data if less than 50 % of the 5 km disc has GLiM data.
- **Not applied anywhere.** mare-v1 stays frozen; this would be mare-v1.1, a post-run addition.

With the grid, raw is almost always 0 or 1, so c23 acts like a yes/no basalt flag. A basalt spot gains a little; a non-basalt spot loses about 0.2. That's larger than the whole score spread of the top ~200 (0.996 → ~0.97).

### Variant B (recommended for reading): rank only the 485 cells that have a c23 value
Weight 1.0, tolerance 0.5:

| new rank | old rank | cell | lon | lat | rock class | vb share 5 km | old score | s_c23 | new score |
|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| 1 | 24 | b093_r001c1594 | 105.253 | 41.131 | vb | 1.00 | 0.9916 | 1.000 | 0.9932 |
| 2 | 55 | b112_r002c372 | -73.482 | 61.887 | vb | 1.00 | 0.9892 | 1.000 | 0.9914 |
| 3 | 150 | b074_r005c1367 | 17.448 | 21.054 | vb | 1.00 | 0.9808 | 1.000 | 0.9846 |
| 4 | 190 | b085_r006c1480 | 58.213 | 33.128 | vb | 1.00 | 0.9771 | 1.000 | 0.9817 |
| 5 | 239 | b093_r001c1595 | 105.432 | 41.131 | vb | 1.00 | 0.9726 | 1.000 | 0.9781 |
| 6 | 250 | b088_r005c1609 | 88.919 | 36.248 | vb | 1.00 | 0.9713 | 1.000 | 0.9770 |
| 7 | 317 | b065_r002c1622 | 42.628 | 10.880 | vb | 1.00 | 0.9610 | 1.000 | 0.9688 |
| 8 | 331 | b084_r005c1217 | 13.253 | 31.907 | vb | 1.00 | 0.9583 | 1.000 | 0.9666 |
| 9 | 461 | b084_r005c421 | -113.096 | 31.907 | vb | 1.00 | 0.8768 | 1.000 | 0.9015 |
| 10 | 259 | b087_r007c445 | -106.325 | 35.434 | su | 0.37 | 0.9706 | 0.208 | 0.8181 |
| 11 | 338 | b088_r002c1603 | 86.536 | 35.841 | ss | 0.39 | 0.9574 | 0.223 | 0.8105 |
| 12 | 1 | b077_r003c1261 | 6.126 | 24.039 | su | 0.00 | 0.9961 | 0.018 | 0.8005 |
| 13 | 2 | b094_r003c1513 | 96.558 | 42.488 | pi | 0.00 | 0.9956 | 0.018 | 0.8001 |
| 14 | 3 | b079_r000c1422 | 32.903 | 25.802 | su | 0.00 | 0.9953 | 0.018 | 0.7999 |
| 15 | 4 | b094_r003c1554 | 104.050 | 42.488 | pa | 0.00 | 0.9948 | 0.018 | 0.7995 |
| 16 | 5 | b086_r006c1129 | 4.045 | 34.213 | ss | 0.00 | 0.9945 | 0.018 | 0.7992 |
| 17 | 6 | b124_r003c155 | -98.804 | 75.045 | sm | 0.00 | 0.9944 | 0.018 | 0.7992 |
| 18 | 7 | b082_r003c1384 | 34.271 | 29.465 | sc | 0.00 | 0.9943 | 0.018 | 0.7991 |
| 19 | 8 | b094_r002c1525 | 98.148 | 42.352 | pa | 0.00 | 0.9940 | 0.018 | 0.7989 |
| 20 | 9 | b083_r007c1581 | 68.854 | 31.093 | sm | 0.00 | 0.9939 | 0.018 | 0.7988 |

- Of the old top 20, **9 stay and 11 leave** (old #10–#20 → new #21–#31). 11 enter: the 9 basalt cells plus 2 partly basalt cells (old #259, #338).
- Non-basalt cells keep their old order among themselves (c23 is the same 0.018 for all of them).
- Weight 0.5: 10 stay (old #1–#10), 10 leave. All 9 basalt cells and 1 partly basalt cell (old #259) enter.
- Weight 0.25: 12 stay, 8 leave. Only the 8 full-basalt cells enter.

### Variant A (current team rule: c23 no data → left out, weights renormalised)
Weight 1.0: **12 of the new top 20 are no-data cells** (Canadian Arctic islands, Namibian/Angolan coast, two GLiM `nd` cells in Mongolia/China, and one in Yemen). Of the old top 20, 0 stay. The same happens at weights 0.5 and 0.25. A missing value escapes the ~0.2 penalty that every non-basalt cell takes, so "no data" ranks above "known non-basalt". Full tables: `data/material/mare_c23_whatif_{A,B}_w*_t0.5.csv` (local).

## 5. Skipped and why
| what | why |
|---|---|
| Download of the full GLiM polygons (`LiMW_GIS 2015.gdb.zip`, 1.14 GB) | no licence statement; CCGM's licence is not open (session rule: unclear/not open → skip). Alternative tried once: PANGAEA 0.5° grid (CC-BY 3.0), used |
| Layer and class field names of the GDB | file not downloaded; code assumes field `xx`, unverified |
| Criterion 22 (anorthosite) | GLiM has no anorthosite class |
| Any change to scores, `config/pipeline.yaml`, lunar targets, `outputs/`, `src/export_app.py`, the criteria doc | outside this task / frozen (mare-v1, config-v1) |
| Anything in `..\EspaceOdyssey` | not touched except reading `out\night_polar` and `out\night_mare` |
| `git push` of `material-glim` | first try hung at the GitHub sign-in (timed out); the retry without prompts failed with "could not read Username for 'https://github.com'". **Commits are local only**: run `git push -u origin material-glim` in this worktree |

pip installs into `..\EspaceOdyssey\.venv`: `geopandas 1.2.0`, `pyogrio 0.13.0`, `shapely 2.2.0` (+ their dependencies). Note: this is the other session's venv; the packages were approved, but tell that session they are new.

## 6. What you must decide
1. **Polygon licence:** email the GLiM authors (Uni Hamburg) for the licence of `LiMW_GIS 2015.gdb`, or accept the risk for a non-commercial hackathon? Only the polygons give real 5 km shares; the grid is a basalt-region flag at ~55 km.
2. **Use c23 at all with the grid?** Option: display only (a "basalt region" badge) until polygons are available. My suggestion, given limits 1–2 in `docs/MATERIAL.md`.
3. **If c23 counts:** weight (1.0 / 0.5 / 0.25) and tolerance (0.5). And a rule for c23 no data that does not reward missing data (variant B "rank only cells with c23", or score no-data cells on the 4 axes but show them in a separate list). The current renormalise rule (variant A) gives a misleading top 20.
4. **Versioning:** c23 changes the frozen Mare total → mare-v1.1 / mare-v2, which per CLAUDE.md means a new Mare validation (Lanzarote). I did not run or look at Lanzarote or Craters of the Moon.
5. **Coverage threshold** for no data (I used 50 % of the disc).
