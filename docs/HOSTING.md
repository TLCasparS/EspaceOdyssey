# Hosting the app (GitHub Pages)

The app is plain files (HTML, JavaScript, CSV/JSON data, two globe images), so GitHub Pages can serve the
repository as it is. No build step, no server, no accounts, no keys.

Live link once Pages is on: **https://tlcaspars.github.io/EspaceOdyssey/app/**
(the repo root, https://tlcaspars.github.io/EspaceOdyssey/, forwards to it).

## Turn it on (someone with admin rights on the repo, once)

1. On GitHub: **Settings → Pages**.
2. Source: **Deploy from a branch**. Branch: **main**, folder: **/ (root)**. Save.
3. Wait 1–5 minutes; the page shows the link when it is live. Each merge to `main` republishes it
   (see the **Actions** tab, "pages build and deployment").

## Files added for hosting

- `.nojekyll`: tells GitHub to publish the files as they are (no Jekyll processing).
- `index.html` at the root: forwards to `app/`.

## Rules to keep (Space Apps)

- The link must open with no password, permission or registration. Test it in a private window.
- **After the deadline (Sun 15 Nov 2026, 23:59 CET) nobody merges to `main`.** Every merge changes the
  live app, and only the submitted version should be judged.
- Outside pieces the app loads from the web (list them in the project's References): globe.gl and
  MapLibre GL (unpkg), Google Fonts (Fira Sans), AWS Terrain Tiles (elevation), EOX Sentinel-2 cloudless
  (satellite imagery, 2016 layer, CC BY 4.0; the newer layers are non-commercial, so we don't use them).

## Checks after it is live

- Opens in a private window, on a phone and on a laptop.
- Globe, ranked list, cards, Moon globe and 3D terrain load; no errors in the browser console.
