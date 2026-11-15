# Top-50 Polar places: satellite check

Request (Caspar, 15 Nov): check the top 50 Polar places in `outputs/night_export/scores.csv`
with satellite images. Is each one a mine, glacier, lake or real bowl? Look especially at the
Himalaya/Tibet bowls (e.g. 27.8 N, 92.5 E), which may be elevation errors.

- Imagery: Esri World Imagery (`server.arcgisonline.com/.../World_Imagery/MapServer/export`),
  7 x 7 km tiles (wider for big bowls), with the bowl diameter drawn as a circle.
- Verdicts are by eye from imagery. They are not ground truth. Confidence is given per row.
- Names are only given where a source puts the site within a few km. Everything else stays unnamed.
- Full table: [`docs/top50_check.csv`](top50_check.csv). It covers the 50 places plus 10 high-Asia
  places from ranks 51–123.

## Result for the top 50

| Verdict | Count | Ranks |
|---|---|---|
| Open-pit mine | 20 | 1, 6, 7, 8, 9, 11, 13, 16, 20, 23, 26, 27, 30, 31, 33, 35, 36, 40, 44, 46 |
| Glacier / ice basin | 10 | 2, 3, 4, 10, 14, 17, 38, 41, 47, 48 |
| Mountain lake basin | 1 | 5 |
| No bowl visible (valley, folded ridges, badlands) | 8 | 15, 19, 24, 29, 34, 37, 39, 43 |
| Unclear (cloud cover) | 1 | 49 |
| **Real bowl** | **10** | 12, 18, 21, 22, 25, 28, 32, 42, 50 (volcanic craters); 45 (Meteor Crater) |

So only 10 of the top 50 are natural bowls of the kind we mean.

Mines with a source-backed name: Cuajone (#9, 0.3 km from the listed point), Chuquicamata (#20, 2 km),
Grasberg (#46, 0.5 km). #8 and #16 sit inside NASA ASTER images of Morenci and Escondida, so they are
"probably" those mines. #1 looks like a pit near Balkhash. The published Kounrad point is 11 km away,
so that name is UNVERIFIED.

## Himalaya / Tibet

There are 186 places in high Asia in the night export. The two near 27.8 N, 92.5 E that Caspar named
are both outside the top 50:

| Rank | Lat, lon | Diameter | Spill depth | Depth / width | Imagery |
|---|---|---|---|---|---|
| 51 | 27.796, 92.629 | 1.35 km | 655 m | 0.48 | snowy ridges, no depression |
| 83 | 27.806, 92.513 | 3.2 km | 1,553 m | 0.49 | river valleys and ridges, no depression |

For comparison, depth/width is 0.197 for Shackleton, 0.258 at most for the real bowls in the top 50,
and 0.306 at most for the mines. A natural bowl about twice as deep as Shackleton for its width,
with nothing visible on the ground, is **most likely a DEM artifact** (voids or steep-terrain errors).

Other high-Asia places checked:

- #62, #82, #92, #95, #100 are mountain valleys or gorges, with no bowl.
- #94 is the edge of a Karakoram glacier.
- #108 and #123 are in a megadune desert at about 39.8 N, 101–102 E, with interdune lakes nearby.
  There's a cluster of these dune hollows at ranks ~108–149. They're real closed depressions,
  but they aren't craters.

## Suggested filters (for Caspar to decide)

1. **Mine mask.** This would remove 20 of the top 50. (Caspar is already adding one.)
2. **Glacier mask.** The `ice_floor` column was 0 for 6 of the 10 glacier places, so the current ice
   share does not catch them. A wider mask or a buffer (e.g. RGI outlines + 1 km) may be needed.
3. **Depth/width cap of about 0.35.** This drops #51 and #83 and touches no real bowl or mine in the
   top 50. It's a threshold I picked by looking at these numbers, so it needs agreement before use.
4. **Dune-field flag** (optional) for the Badain Jaran–type cluster.
5. The 8 "no bowl visible" places (low point at 950–4,400 m) look like valley closures. A minimum
   rim-completeness test, or a "closed on all sides in the DEM *and* in a second DEM" check, would
   catch most of them. This is untested.

The numbers in this file come from `scores.csv` / `raw_values.csv` of the night export.
No scores were changed.
