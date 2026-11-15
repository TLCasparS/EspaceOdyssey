## Agent report: Task 4 App stress test at night-run scale
Status: done

What I did:
- Wrote `scripts/make_fake_outputs.py`: clearly fake exports (places `FAKE_0001…`, runs `fake_rXX`, random values,
  fixed seed) in the export v2 format of `src/export_app.py`, for 200 / 2,000 / 5,000 / 10,000 places, 20,000
  coverage tiles, and cells only near places (each place's own cell + 3 neighbours). Output: `outputs_fake/<n>/`.
- Added a small `?data=` flag to `app/app.js` (approved by Sofia): `app/index.html?data=outputs_fake/2000` reads that
  folder instead of `../outputs/`. Only `outputs_fake/<number>` is accepted. Without the parameter nothing changes.
  With it, the "Fake data" badge shows and two `performance.mark`s record load timing.
- Loaded the app at each size in a real browser (Chromium in the Claude desktop app, Apple M5, 16 GB, viewport
  1440×900) and measured load time, file sizes, globe labels/meshes, list rows, DOM size, click cost, globe frame
  cost, heatmap rebuild and memory.
- Tried the two biggest fixes in the browser console (labels for the top 200 only + one merged points layer; coverage
  as one merged layer) to measure what they gain. Nothing in the app was changed for this.
- Wrote prioritised fixes with `app/app.js` line numbers (below). Sofia decides which ones to make.

Files changed / created:
- `scripts/make_fake_outputs.py` (new)
- `outputs_fake/README.md` (new; the data folders themselves are not committed, ~35 MB with 5,000, regenerate in 1 s)
- `app/app.js`: `?data=` flag only (lines 8–11, 18–22, 1322, 1327, 1340 on this branch)
- `docs/APP_SCALE_TEST.md` (this file), `docs/ai_usage/task4.md`

Tests: `python3 scripts/make_fake_outputs.py` → writes 200 / 2000 / 10000 in 0.5 s;
`node --check app/app.js` → OK; app without `?data=` loads `outputs/` as before (11 sites, 7 list rows);
`git status outputs/` → unchanged.

Open points / needs a human decision:
- Which fixes to make (list below). Fix 1 and 2 alone make 10,000 places usable in my measurements.
- The night guide's "nobody touches `app/`" row vs. Task 4's "tiny fix behind a flag": I used the Task 4 exception
  (Sofia approved the `?data=` flag). Drop the `app/app.js` commit if you'd rather keep `app/` untouched.
- The app does not read `coverage.json` or `regions.json` (export v2) yet. Numbers for drawing coverage are below.

Unverified items (and why):
- Measured on a fast laptop (Apple M5). A typical judge's laptop will be slower; I did not measure one, so the
  "breaks at" number may be lower there.
- Frame cost is measured by rendering 10 frames directly and waiting for the GPU (`gl.finish()`), because the
  browser pane was not on screen during the night run and the browser then throttles animation (the FPS counter
  read 1–2 fps at every size, which is the throttling, not the app). Real FPS on screen was not measured.
- Memory is the JS heap (`performance.memory`), not GPU memory; values jump with garbage collection
  (5,000 and 10,000 read almost the same).
- How many places tonight's run will really produce: not known to me. Compare with the table when real data arrives.

Data downloaded (size): none.

---

## Result: usable up to about 2,000 places; breaks at about 5,000 places

| Places | 0 (today's `outputs/`) | 200 | 2,000 | 5,000 | 10,000 |
|---|---|---|---|---|---|
| Data files loaded (scores + raw + heatmap + cells + targets) | 88 KB | 331 KB | 3.2 MB | 8.0 MB | 15.9 MB |
| of which `cells.json` | 66 KB | 212 KB | 2.1 MB | 5.3 MB | 10.7 MB |
| Data loaded (`loadAll`) | – | 0.08 s | 0.23 s | 0.48 s | 1.4 s |
| First render (list, card, globe set up) | – | 0.25 s | 0.51 s | 1.2 s | 2.7 s |
| Main thread blocked during load (sum of long tasks) | – | 0.25 s | 0.32 s | 0.82 s | 1.6 s |
| Globe labels / three.js meshes | 11 / 35 | 207 / 423 | 2,007 / 4,068 | 5,007 / 10,143 | 10,007 / 20,268 |
| Globe frame (render + GPU) | 0.6 ms | 1.2 ms | 5.8 ms | 15.8 ms | 37.5 ms |
| → best possible frame rate | 60 fps | 60 fps | 60 fps | ~60 fps (at the limit) | ~26 fps |
| List rows / DOM nodes | 7 / 405 | 201 / 2,333 | 2,001 / 20,333 | 5,001 / 50,332 | 10,001 / 100,332 |
| `renderList()` | 0.8 ms | 5.8 ms | 23 ms | 57 ms | 130 ms |
| `ranked()` (called ~8× per click) | – | 2.7 ms | 5.6 ms | 14 ms | 34 ms |
| Click a site: synchronous part (`select`) | – | 6 ms | 34 ms | 101 ms | 222 ms |
| Click a site: globe rebuilds labels afterwards | – | 0 | 0.11 s | 0.51 s | 1.1 s |
| **Click → screen settles** | – | **instant** | **~0.15 s** | **~0.6 s** | **~1.4 s** |
| Heatmap rebuild (when zooming past the heatmap threshold) | – | 1.1 s | 1.3 s | 1.9 s | 2.6 s |
| JS heap | 137 MB | 130 MB | 210 MB | 824 MB | 863 MB |

`coverage.json` with 20,000 tiles: 2.0 MB, fetch 11 ms, `JSON.parse` 7 ms. Not drawn by the app yet.

How to read it: a click should feel instant under ~0.1 s and feels broken above ~1 s; the globe turns smoothly
when a frame takes under 16.7 ms (60 fps) and looks jerky above 33 ms (30 fps). At **2,000** places everything is
still fine (a click takes ~0.15 s). At **5,000** clicks take ~0.6 s, the frame is at the 60 fps limit and the heap is
~0.8 GB: noticeably laggy. At **10,000** a click takes ~1.4 s, the globe drops to ~26 fps and the list has 100,000
DOM nodes: **broken**. So: **breaks at about 5,000 places** on this machine; on a slower laptop, earlier.

What grows with the number of places, in order of cost:
1. **Globe labels.** One label = 2 meshes (text + dot), all re-created on every click and zoom step. 10,000 places
   = 20,000 meshes: the frame cost (37.5 ms) and the 1.1 s rebuild after each click.
2. **`ranked()` called many times per click.** It scores and sorts every site each time; `renderList`,
   `renderCard`, `updateGlobe`, `currentSite`, `twinsOf` and `scoredCount` each call it again.
3. **The list renders every row** (10,000 rows, 100,000 DOM nodes).
4. **`cells.json`** is two thirds of the download (10.7 MB at 10,000) but the app only uses it to draw one box per
   region and count statuses.
5. **The heatmap rebuild** costs 1–2.6 s at every size (most of it is a fixed cost of globe.gl's heatmap). It only
   happens when the zoom crosses the heatmap threshold, but then the page freezes for that long.

## Prioritised fixes (line numbers: `app/app.js` on `agent/app-scale`; on `main` subtract 4, and 5 after line 1322)

| # | Fix | Where | Measured / expected gain | Effort |
|---|---|---|---|---|
| 1 | **Labels only for the top N** (e.g. 150, plus the selected site and the flashing twins); all other places as **one merged points layer** (`pointsData(...).pointsMerge(true)`) | `updateGlobe` → `g.labelsData(shown…)` line 877; `declutterLabels` 803–820 (run it on the top N only); label setup 746–756 | Measured at 10,000 in the console: frame **39 ms → 3 ms**, meshes 20,268 → 655, relabelling after a click 1.1 s → 0 | small |
| 2 | **Compute `ranked()` once per change** (cache the result; clear the cache when filters, base or data change) | `ranked` 263–268, `visibleSites` 269, callers 291, 369, 388, 419–422, 555, 1002, 1306, 1338 | Click sync part ~8 × 34 ms → ~34 ms at 10,000 (expected from the per-call timing) | small |
| 3 | **List: first 100 rows + "Show more"** (the ranking is sorted, nobody scrolls 10,000 rows) | `renderList` 416–430 (`list.innerHTML = rows.map…`) | `renderList` 130 ms → ~3 ms, DOM 100,000 → ~1,400 nodes at 10,000 (expected from the 200-place row) | small |
| 4 | **`rawFor` with a Map** instead of `rawRows.find` per row (O(n²): 50 M comparisons at 10,000) | line 160 | Part of the 1.4 s data load at 10,000 | tiny |
| 5 | **Read `regions.json` (export v2) instead of `cells.json`** for the region boxes and counts | `DATA.cells` line 22, `loadAll` 155, `searchedRegions` 280–289 | Download at 10,000: 15.9 MB → 5.3 MB (`regions.json` is 72 KB). Needs the v2 export on main | small |
| 6 | **Don't rebuild the heatmap on zoom**: build it once, and hide it by toggling the layer's visibility instead of `heatmapsData([])` / `heatmapsData([…])` | `onGlobeZoom` 829–832 (line 831) | Removes a 1–2.6 s freeze when zooming in or out past the threshold. How to hide the layer without a rebuild in globe.gl 2.32: not tested | small–medium |
| 7 | **Coverage as one layer** (when Sofia wants to show `coverage.json`): one merged points layer (one dot per 1° tile), not one path or tile per tile | new, next to `setEarthPaths` 838–843 | Measured: 20,000 tiles → 1 mesh, frame +0.8 ms, one-off build 0.56 s | small |
| 8 | Zoom handler only redraws labels when needed (after fix 1 this is cheap anyway) | `onGlobeZoom` 821–835 → `updateGlobe(false)` line 834 | Zooming at 10,000 currently re-creates all labels each step | tiny |

With fixes 1–3 the measured costs at 10,000 places are close to today's 2,000-place numbers. Fix 1 has one
trade-off: places drawn as merged points can't be clicked individually on the globe (only the top N labels can);
the list stays the way to reach every place.

## How to repeat the test

```bash
python3 scripts/make_fake_outputs.py                  # 200, 2000, 10000 (+ --sizes 5000 for the middle point)
python3 -m http.server 8000                           # from the repo root
# open http://localhost:8000/app/index.html?data=outputs_fake/2000
```

In the browser console, after the page has loaded:
`performance.getEntriesByName('scale:data-loaded')[0].startTime` and `…('scale:first-render')…` give the load
times; `state.globe.labelsData().length` the label count; `performance.memory.usedJSHeapSize` the heap.
