# Night run, 14/15 Nov 2026

Configs: Polar `config-v1` (frozen), Mare `mare-v1` (frozen, Mateo's lunar target). All commands from the repo root
`C:\Users\Tillm\OneDrive\Dokumente\Hackathon\Space\EspaceOdyssey` in PowerShell. Work data goes to
`%LOCALAPPDATA%\espaceodyssey_night` (outside OneDrive). Downloads: Copernicus DEM + ESA WorldCover from AWS, no login.

## Measured so far (hotspot, 14 Nov)
| Read | Size |
|---|---|
| WorldCover 3° tile, full 10 m | 120 MB (we only read overviews) |
| GLO-90 1° tile | 4.6 MB (one 2048 block: any full-resolution read loads the whole tile) |
| GLO-30 1° tile | 37.5 MB in 16 blocks of 1024² (~2.3 MB each) |
| Stage 0 world, 1 tile (WorldCover ~1 km + GLO-90 300 px) | ~0.4–0.5 MB (adapter upper bound, 4 tiles measured) |
| Stage 1 (B1), 1 tile, 30 cells | 4.1 MB, 1.9 s |
| Track A + B, 1 Tibesti tile, 49 cells (17:28 test) | ~81 s per tile (stage 0 ~15 s, A ~57 s, B ~7 s) |

## Track A since 14 Nov evening: A1 -> A2, parallel tiles
- **A1** (cheap, whole tile): GLO-90 read once per tile (+3 km pad, cached in `cache\glo90`, shared with B1), bowl
  detector at native 90 m with lenient limits (>= 25 m deep, >= 700 m wide, elongation <= 2). Command-line options
  `--a1-min-depth --a1-min-width --a1-max-elong --a1-pad-km`, **not** config-v1: they only pick the cells for A2.
  Real check: Meteor Crater, Al Wahbah, Roter Kamm and El Elegante (Pinacate) all give A1 candidates.
- **A2**: the frozen config-v1 pipeline at 30 m, only for cells with an A1 depression (30 m DEM read only around
  those cells). Other cells store the A1 skip reason.
- `--workers N` (default cores − 1): tiles run in parallel processes; only the main process writes
  `progress.json` / `night.log`, so resume stays safe.
- Every raw record has `prov` (git commit, config-v1 / mare-v1 check, DEM source + resolution, UTC time).
  A2 / B2 candidates get a DEM crop in `crops\` (60 m grid, int16 decimetres, npz): ~270–350 KB each on real
  terrain (measured on Haughton / Lo Manthang 30 m rasters), i.e. ~0.3 GB per 1,000 candidate cells.

## The three commands

### 1. Stage 0 worldwide (coarse prescreen of all 19,433 land tiles, 60° S to 84° N)
```powershell
.venv\Scripts\python.exe src\stage0_world.py --workers 8
```
- Expected download: **~3–4 GB** (range 2–6 GB). WorldCover is read once per 3° block (~2,600 blocks × ~0.1 MB);
  the GLO-90 overview (~0.3 MB) only for tiles whose land cover leaves a candidate.
- Runtime: ~1–2 h with 8 parallel reads (network-bound). Resumes if interrupted (same command again).
- Cheaper first look (optional): `--lc-only` reads land cover only (~0.3–0.5 GB) and prints how many tiles need a DEM read.
- Result: `%LOCALAPPDATA%\espaceodyssey_night\world\world_priority.json` (tiles with candidates, deserts first).

### 2. Sample test (Tibesti, 12 tiles, all tracks incl. B2, separate work dir)
```powershell
.venv\Scripts\python.exe src\night_run.py --work $env:LOCALAPPDATA\espaceodyssey_sample --only tibesti --tracks A,B1 --workers 7
.venv\Scripts\python.exe src\night_run.py --work $env:LOCALAPPDATA\espaceodyssey_sample --score
.venv\Scripts\python.exe src\export_app.py out\night_polar out\night_mare --out $env:LOCALAPPDATA\espaceodyssey_sample\outputs
```
- Expected download: **~1.2–1.5 GB**: A ~50 MB per tile (12 tiles ≈ 0.6 GB), B1 ~10–18 MB per tile (≈ 0.15 GB),
  B2 (runs automatically: Mare target is verified) re-reads 30 m for the selected cells (≈ 0.5–0.6 GB).
- Runtime: ~25–35 min. Check afterwards: `night.log` timings (s per tile), `--status`, Trou au Natron in
  `out\night_polar\cells.geojson` (position from memory ~20.95 N, 16.53 E, unchecked).
- The export goes to the sample folder so it does not overwrite `outputs/` in the repo.

### 3. Night run (world, priority order, stops cleanly at the time limit)
```powershell
.venv\Scripts\python.exe src\night_run.py --world --tracks A,B1 --max-hours 9 --workers 7
```
- Processes stage-0 tiles from most to fewest candidates (deserts first); A (Polar crater, 30 m) on A candidates,
  B1 (Mare coarse, 90 m) on B candidates. The whole world does not fit in one night (19,433 tiles at ~80 s for a
  full desert tile); the time limit decides how far it gets, and the same command resumes.
- Expected download: **~2–4 GB per hour** (A ~50 MB per tile with A candidates, B1 ~10–18 MB, WorldCover ~2 MB;
  ~45–90 tiles per hour). With `--max-hours 9`: **~20–35 GB**. If that is too much for your line, use
  `--max-hours 4` (~10–15 GB) or run `--tracks B1` only (~15 MB per tile, faster).
- B2 (30 m Mare pass for the top 500) starts automatically only if the tile loop finishes; with a time limit
  it is deferred. Next morning: `.venv\Scripts\python.exe src\night_run.py --b2` (~4–7 GB: ~500 cells × 9–14 MB).

### Morning
```powershell
.venv\Scripts\python.exe src\night_run.py --status
.venv\Scripts\python.exe src\night_run.py --b2          # if B2 was deferred
.venv\Scripts\python.exe src\night_run.py --score
.venv\Scripts\python.exe src\export_app.py out\night_polar out\night_mare out\meteor_crater out\pinacate
```
**15 Nov 2026, export actually used for the app (config-v1.1 post-run filters, offline names):**
```powershell
.venv\Scripts\python.exe src\night_run.py --score --tracks A,B2
.venv\Scripts\python.exe src\export_app.py out\night_polar out\night_mare out\meteor_crater out\pinacate `
  --post-filters config\post_filters.yaml --place-names $env:LOCALAPPDATA\espaceodyssey_data `
  --anchors config\site_anchors.csv --dedupe-km 1 --cells-near-km 16
```
Needs in `%LOCALAPPDATA%\espaceodyssey_data`: `maus_v2\global_mining_polygons_v2.gpkg`, `naturalearth\extracted\`
(admin 0 countries + geography regions), `geonames\extracted\cities1000.txt`; links in `config/post_filters.yaml`
and `src/place_names.py`. Details: `docs/MORNING_REPORT.md`.
Failed tiles are listed by `--status` and retried by running the night command again.

## Laptop checklist (before command 3)
1. **Power:** plugged in; no battery-saver mode.
2. **No sleep on AC** (PowerShell as admin; restore with your old values afterwards):
   ```powershell
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   powercfg /change monitor-timeout-ac 10
   powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0   # closing the lid does nothing
   powercfg /setactive SCHEME_CURRENT
   ```
3. **Windows Update:** Settings → Windows Update → *Pause updates* (1 week), so no restart in the night.
4. **OneDrive:** pause syncing (tray icon → Pause syncing → 24 h). The work data is outside OneDrive anyway, but
   `out\` is inside the repo; this avoids sync traffic and file locks during `--score`/export.
5. **Disk:** ~5 GB free on C: (GLO-90 cache ~4.6 MB per tile touched, crops ~0.3 GB per 1,000 candidates; raw values are small).
6. **Network:** LAN cable if possible; no VPN; the hotspot is not enough for command 3.
7. **Terminal:** start in a normal PowerShell window that stays open (not inside VS Code, which might restart).
   Optional log copy: `... | Tee-Object -FilePath night_console.log`.
8. **Antivirus:** the many small writes in `%LOCALAPPDATA%\espaceodyssey_night` are fine; no action needed unless
   it prompts.
