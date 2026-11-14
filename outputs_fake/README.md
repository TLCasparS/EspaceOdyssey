# outputs_fake/: FAKE data for the app scale test

Nothing here is a result. Written by `scripts/make_fake_outputs.py` (fixed seed): places `FAKE_0001…` with random
values, in the export format of `src/export_app.py`, one folder per size (`200/`, `2000/`, `10000/`, optional
`5000/`). The folders are not committed (~35 MB); regenerate them in about a second:

```bash
python3 scripts/make_fake_outputs.py
```

Open the app on one size with `app/index.html?data=outputs_fake/2000` (the page shows the "Fake data" badge).
Report: `docs/APP_SCALE_TEST.md`.
