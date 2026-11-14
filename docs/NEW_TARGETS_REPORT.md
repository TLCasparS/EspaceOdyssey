## Agent report: Task 5 New lunar targets
Status: done (10 Polar + 4 Mare candidate targets computed, 3 Polar regions skipped with reason; all `verified: false`)
What I did:
- Polar: one candidate target per **Artemis III candidate region (NASA, 19 Aug 2022, 13 regions)**, same method as Shackleton (LOLA `LDEM_80S_20MPP_ADJ` window ±35 km → 60 m, `pipeline.polar` code, light c1–c4 from PGDA `AVGVISIB_85S_060M_201608` / `LPSR_85S_060M_201608` via `pipeline.lunar_light.moon_light`).
- Region centres taken from data, not memory: centre of the extent of each region's PGDA product 78 5 m site DEM (GeoTIFF header read over HTTP).
- Mare: split the 20-cell target into Tranquillitatis, Serenitatis, Imbrium, Crisium (5 cells each), median + IQR, `tolerance = max(IQR, floor)` with the existing `pipeline.mare.target_from_cells` and frozen floors.
- One preview PNG per Polar region (also for skipped ones) and one Mare comparison plot.
- Flagged where a region doesn't fit the Polar definition instead of forcing it.

Files changed / created:
- `src/compute_polar_candidates.py` (new), `src/compute_mare_candidates.py` (new)
- `config/lunar_targets_candidates.json` (new, 17 entries: 13 Polar incl. 3 skipped, 4 Mare)
- `figures/moon/targets/polar_<site>.png` (13), `figures/moon/targets/mare_per_mare.png`
- `docs/NEW_TARGETS_REPORT.md`, `docs/ai_usage/task5.md`
- Not touched: `config/lunar_targets.json`, `config/pipeline.yaml`, `src/pipeline/*`, `src/fetch_lola_window.py`, `src/compute_lunar_target.py` (only imported).

Tests: `python -m pytest -q` → 102 passed, 1 skipped (incl. `test_config_freeze.py`, `test_mare_freeze.py`). No new tests (scripts write data files only, no new library code).

Open points / needs a human decision:
1. **Ridge/peak regions don't really fit the Polar definition.** The definition needs a closed bowl in the 15 km region with a base pad on its rim. Artemis regions are chosen for sunny ridges, peaks and massifs, so the script picks whatever small crater (1.3–9.4 km) has its low point in the square, often near the square's edge (low point 1.9–7.8 km from the centre). Result: c1 (sunny rim) is **below 1** for every computed region (0.53–0.98; Shackleton 1.56): the sunny ridge the region is known for is not in that small bowl's rim zone. Whether these count as Polar targets is a team call. My suggestion: accept only those where the previews show a sensible bowl + rim pad, and treat the rest as "no Polar fit".
2. **Skipped, no closed bowl** (≥ 50 m deep, ≥ 1 km wide, elongation ≤ 2, low point in the region): **Malapert Massif (Site23), Nobile Rim 1 (Site06), Connecting Ridge Extension (SL3).** Not forced.
3. **Duplicate:** de Gerlache Rim 1 (Site11) and Rim 2 (SL2) pick the **same bowl** (low points 45 m apart, values within ~5 %). Keep one.
4. **No light values** for Nobile Rim 2 (DM2) and Amundsen Rim (DM1): they lie north of 85 S, outside the PGDA illumination maps. c1–c3 = null; c4 computed from latitude only. A wider illumination product would be needed.
5. Haworth: the chosen bowl is a 3.1 km crater inside the region, not Haworth crater itself: in this ±35 km window the script found only one qualifying depression with its low point in the region. I did not check Haworth crater's size or position, which is why it isn't picked (probably the big-crater window limit noted in `CLAUDE.md`). UNVERIFIED.
6. **c14 aspect = 0.0** for 8 of 10: none of these small bowls has pixels steeper than 20°, so the existing rule returns 0 (polar.py convention "no steep walls"). Display only (weight 0), no effect on scores.
7. **Mare:** per mare, only c9 relief (and a little c13) differs: c9 median Serenitatis 118 m / Imbrium 121 m vs Tranquillitatis 241 m / Crisium 286 m. c10 and c12 have IQR below the frozen floors, so their tolerance is the floor and the four targets are almost identical there. 5 cells per mare is a small sample; the IQR is a rough spread estimate.
8. **Polar entries carry no `tolerance`**: Task 3 should use the per-criterion tolerances from `config/pipeline.yaml` (polar) as for Shackleton. Mare entries carry their own `tolerance`.
9. `git_commit` in the JSON is `df8b4e9` (branch base); the scripts were not yet committed when they ran. They are in the first commit of this branch.

Unverified items (and why):
- All 14 targets: `verified: false` by rule. Values are computed, but nobody has checked the previews yet.
- **Region name → PGDA site mapping**: based on the matching labels on the PGDA product 78 page. **UNVERIFIED for de Gerlache Rim 1 vs Rim 2**: PGDA labels both Site11 and SL2 just "de Gerlache rim"; Rim 1 = Site11, Rim 2 = SL2 is my assumption. Moot if point 3 above is resolved by keeping one.
- **Region centre = PGDA site-tile centre**: a proxy, not an official NASA coordinate. NASA's release gives a map and "approximately 15 by 15 kilometers" per region, no centre coordinates.
- The 2024 update (9 regions, NASA 28 Oct 2024) adds Peak near Cabeus B, Mons Mouton, Mons Mouton Plateau and Slater Plain. PGDA product 78 has no site DEM for them, so they have no data-derived centre and are **not included**. Source for the 2024 list: press reports (e.g. [UPI](https://www.upi.com/Science_News/2024/10/28/nasa-artemis-moon-landing-regions/5971730152372/), [Space.com](https://www.space.com/space-exploration/artemis/nasa-announces-9-possible-moon-landing-sites-for-artemis-3-lunar-mission)); I did not check the NASA primary page.

Data downloaded (size): 13 LOLA 20 m windows (±35 km), 509 MB in total, cached in `<main repo>/data/moon/targets/` (git-ignored; via HTTP range reads, not the 2.7 GB full file). The PGDA 5 m site DEMs: header only (a few KB each). The PGDA illumination maps were already on disk.

---

## Sources

| What | Source |
|---|---|
| Artemis III candidate regions (13) and size ≈ 15 × 15 km | NASA RELEASE22-089, 19 Aug 2022: https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ |
| Region site DEMs (names, extents → centres) | PGDA product 78, "High-Resolution LOLA Topography for Lunar South Pole Sites" (M. K. Barker): https://pgda.gsfc.nasa.gov/products/78, files `https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/<site>/<site>_final_adj_5mpp_surf.tif` |
| Terrain (all Polar criteria) | LOLA `LDEM_80S_20MPP_ADJ.TIF`, PGDA product 90 (Barker et al. 2023), https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF |
| Light c1–c3 | PGDA product 69 `AVGVISIB_85S_060M_201608.TIF`, `LPSR_85S_060M_201608.TIF` (Mazarico et al. 2011); same known limitation as Shackleton (visible solar disc vs Sun centre) |
| Mare cell values | `config/lunar_targets.json` → `mare.cells` (SLDEM2015, computed by `src/compute_mare_target.py`) |

## Method

**Polar** (`src/compute_polar_candidates.py`), per region:
1. Centre = middle of the PGDA 5 m site DEM extent (polar stereographic, m).
2. LOLA 20 m window ±35 km around it (`fetch_lola_window.read_window`, with retries: PGDA returned an empty tile once), bilinear to the 60 m grid (`compute_lunar_target.load_grid`).
3. Region = 15 km square (`grid.cell_km`) centred there. Candidates = `pipeline.polar.find_depressions` with low point in the square; each scored by `_Cell.place` (body = moon, nothing masked).
4. Chosen place = the **valid** candidate (base pad found and ≤ `max_base_slope_deg`) with the largest depth × width. This is the rule that picked Shackleton (there: within 15 km of the pole).
5. Light: `lunar_light.moon_light` on the AVGVISIB/LPSR maps (same zones as Earth). c4 from latitude.
6. Preview: hillshade, 15 km region (green), bowl (cyan), floor (blue), inner wall (orange), rim crest (magenta), low point, base pad (`compute_lunar_target.crater_zones`).

Re-run: `python src/compute_polar_candidates.py --moon-dir <main repo>/data/moon [--only Site01,Site07]` (cached windows are reused).

**Mare** (`src/compute_mare_candidates.py`): groups the 20 stored cells by `mare`, calls `pipeline.mare.target_from_cells` with `mare.tolerance_floor` per mare. No DEM reads.

## Results: Polar (raw values; Shackleton for comparison)

Light values from AVGVISIB (visible solar disc). c9 and c14 are display only (weight 0), as for Shackleton.

| Target | c1 | c2 | c3 | c4 | c5 | c7 | c9 | c10 | c11 | c13 | c14 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Shackleton (current, verified) | 1.56 | 1 | 0.785 | 1.91 | 0.631 | 0.197 | 4077 | 0.664 | 27.2 | 24.5 | 0.398 |
| Connecting Ridge (Site01) | 0.902 | 1 | 1.05 | 1.95 | 0.879 | 0.0508 | 152 | 1.05 | 8.89 | 7.91 | 0 |
| Peak Near Shackleton (Site07) | 0.975 | 1 | 0.604 | 2.57 | 0.898 | 0.0385 | 177 | 1.02 | 7.55 | 7.02 | 0 |
| de Gerlache Rim 1 (Site11) | 0.782 | 1 | 1.89 | 3.05 | 0.9 | 0.0405 | 62.4 | 1.33 | 7.75 | 6.22 | 0 |
| de Gerlache Rim 2 (SL2) — same bowl as Site11 | 0.766 | 1 | 1.82 | 3.05 | 0.9 | 0.0408 | 63.8 | 1.28 | 7.8 | 6.45 | 0 |
| Nobile Rim 2 (DM2) | null | null | null | 7.7 | 0.755 | 0.0633 | 679 | 0.327 | 6.07 | 5.82 | 0.211 |
| de Gerlache-Kocher Massif (Site42) | 0.678 | 1 | 1.37 | 5.82 | 0.885 | 0.074 | 148 | 1.31 | 12.2 | 9.78 | 0 |
| Haworth (Haworth) | 0.867 | 1 | 1.12 | 4.81 | 0.876 | 0.0613 | 281 | 1.14 | 10.8 | 9.01 | 0 |
| Leibnitz Beta Plateau (Site20) | 0.554 | 1 | 1.04 | 6.24 | 0.854 | 0.0479 | 285 | 1.27 | 12 | 9.58 | 0 |
| Amundsen Rim (DM1) | null | null | null | 7.4 | 0.755 | 0.0739 | 233 | 1.1 | 12.2 | 8.78 | 0 |
| Faustini Rim A (LM7) | 0.526 | 1 | 1.09 | 3.48 | 0.68 | 0.164 | 422 | 0.838 | 21.9 | 18.3 | 0.285 |
| Malapert Massif (Site23) | skipped: no closed bowl | | | | | | | | | | |
| Nobile Rim 1 (Site06) | skipped: no closed bowl | | | | | | | | | | |
| Connecting Ridge Extension (SL3) | skipped: no closed bowl | | | | | | | | | | |

Chosen bowls (from `place` in the JSON): equivalent diameter 1.3–9.4 km, spill depth 53–593 m. Faustini Rim A is the only one close to Shackleton's shape (c7 0.164 vs 0.197, walls 21.9° vs 27.2°, floor 100 % LPSR).

## Results: Mare (median, tolerance)

| Target | c9 relief (m) | c10 flat base (°) | c12 drivable | c13 roughness (m) |
|---|---|---|---|---|
| Current 20-cell target | 154.0, 163.1 | 0.238, 0.5 | 0.993, 0.05 | 1.69, 1.0 |
| Tranquillitatis | 241.2, 101.3 | 0.267, 0.5 | 0.988, 0.05 | 1.94, 1.0 |
| Serenitatis | 118.1, 47.7 | 0.229, 0.5 | 0.995, 0.05 | 1.29, 1.0 |
| Imbrium | 121.3, 42.2 | 0.231, 0.5 | 0.998, 0.05 | 1.69, 1.0 |
| Crisium | 285.5, 116.3 | 0.247, 0.5 | 0.990, 0.05 | 2.02, 1.0 |

Preview: `figures/moon/targets/mare_per_mare.png`.

## Morning check (suggested)
1. Open the 13 Polar previews. Accept a target only if the bowl and pad look sensible for a "base on the rim of a dark bowl" story.
2. Decide on point 1 (ridge regions) and point 3 (de Gerlache duplicate).
3. Set `verified: true` per accepted target and criterion in `config/lunar_targets_candidates.json`.
