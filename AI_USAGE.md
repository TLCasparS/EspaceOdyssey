Sat 10:40 | Claude | wrote first version of src/profiles.py | reviewed and
edited by (name)
Sat 14:15 | Claude | summarised (paper title) | numbers checked against the
paper
Fri 13 Nov | Claude | wrote src/shadowsim/ (DEM, horizon, sun, yearly light simulation, score), src/run_shadow_sites.py, data/sites.csv, tests/ | sun positions checked against pvlib; tests on synthetic crater; real Copernicus download not yet tested by a human
Sat 14 Nov | Claude | wrote src/moon_dem.py (crop LOLA south-pole DEM around Shackleton, resample to 30 m, rim/floor zones, quicklook) | tested on a synthetic crater, the Site04 tile (no floor) and LDEM_80S_20MPP_ADJ (D 20.9 km, depth ~4.0 km); crater centre coords to check against the IAU gazetteer
