## Status update, 15 Nov 2026 ~08:30 (what is still missing)
Checked by an AI agent against `main` (0be1738) and the live site. Items from the report below that are now done:
- **Hosted app** (open point 1, 3.4): live at https://tlcaspars.github.io/EspaceOdyssey/app/ (HTTP 200, all
  features load, no console errors). Rule: nobody merges to `main` after 23:59 CET.
- **Imagery licence** (open point 2, 5.8): EOX states the 2018–2025 Sentinel-2 cloudless layers are CC BY-NC-SA 4.0
  and the 2016 layer CC BY 4.0 (cloudless.eox.at pricing page and the WMTS capabilities, read 15 Nov). Branch
  `agent/submission-final` switches the 3D view to the 2016 layer (`s2cloudless_3857`), same tiles service.
- **Night-run numbers** (open point 7): in `docs/SUBMISSION_DRAFT.md`, same as `docs/PITCH_OUTLINE.md`.

Still missing, most urgent first:
1. **Submit early** (1.1): fill the project page by ~17:00 and save; edit until 23:59.
2. **Public deck link** (3.3, 4.2): export the 7 slides to PDF / Google Slides, share without login, test in a
   private window. Slides need team + member names (4.3), one real app screenshot (4.4), the live link.
3. **Team details** (2.2, open point 5): full names; everyone on the Members tab, same Local Event, not waitlisted.
4. **Mine filter numbers** (`[TEAM: mine filter]` in the draft and pitch outline).
5. **App shows first-run data**: the live app reads `outputs/` (5 craters, Meteor 46 %), the deck and draft use the
   night run (1,825 places, Meteor 44 %). Either switch the app to `outputs/night_export/` or don't quote first-run
   numbers anywhere. Branch `agent/submission-final` keeps Sofia's site notes working after the switch
   (`_aliases` in `site_info.json`). Note: `outputs/night_export/README.md` lists a `cells.json` that is not in
   the folder.
6. **LICENSE file** for our code (open point 3, 5.9): e.g. MIT or Apache 2.0; without one, NASA uses Apache 2.0.
7. **Project page images** (3.9): 1–3 app screenshots (JPG/PNG, up to 10 MB).
8. **References field** (2.5, 3.8, 5.7): paste the lists from the draft; licences of globe.gl, MapLibre GL and
   Terrain Tiles still say `[check]`.
9. **NASA Earth data is thin** (open point 4): say it honestly in the description.
10. **Local pitch length: not published.** The Barcelona schedule (read 15 Nov) only says "17:30 Pitch
    competition", with no length or format. Ask the Local Lead (listed on the event page) at the venue.
11. **Demo video, if any**: the submission demo is 7 slides **or** a video of 30 s or less (4.1). A 2-minute
    video can't be the submission demo. Script for both in `docs/DEMO_VIDEO_SCRIPT.md`.
12. **Station list licence** (5.8, criterion 29, `docs/ACCESS.md` R2): COMNAP (non-commercial only) was dropped on
    15 Nov 2026. The INTERACT station list states no licence: cite it as "INTERACT GIS station list,
    interact-gis.org, accessed 15 Nov 2026" in the References field.
13. Two tick boxes at submission (2.5), China-review question (2.6), SI-idea confirmation (5.4): the team answers.

---

## Agent report: Task 1 Challenge requirements and submission draft
Status: done (drafts need the final numbers from the night run and the team's names)

What I did:
- Read the challenge page (Details and Resources tabs), the Project Submission Guide, the Judging & Awards Guide,
  the Participant FAQs, the Terms & Conditions and the Barcelona event page (all read on 14 Nov 2026, night).
- Listed every deliverable and rule below with a quoted source line and a status from the repo (`main`, df8b4e9).
- Mapped our work to the challenge objectives and the five judging criteria (bottom of this file).
- Drafted titles, summary, full description, data sources with links and the SI/AI statement in
  `docs/SUBMISSION_DRAFT.md`.

Files changed / created: `docs/SUBMISSION_CHECKLIST.md`, `docs/SUBMISSION_DRAFT.md`, `docs/ai_usage/task1.md`

Tests: none (documents only). Every quote below was copied from the live page; the GitHub repo answers HTTP 200
without login (checked with curl).

Open points / needs a human decision (most important first):
1. **Hosted app link (Link to Final Project).** Not done. The repo is public, but the app needs a web server
   (`app/README.md`). Suggestion: GitHub Pages on the repo, then test the link in a private window.
2. **Imagery licence.** The 3D view uses Sentinel-2 cloudless 2020 by EOX under CC BY-NC-SA 4.0
   (`app/README.md`). The Terms & Conditions ask that non-NASA materials be "freely and publicly available without
   restriction or, at a minimum, ... licensed as open source as defined by the Open Source Initiative". A
   non-commercial licence is not OSI open source. Decide: keep it and list the licence (risk), or switch the 3D
   imagery to a source without the NC clause. I did not check which EOX years have which licence (UNVERIFIED).
3. **Licence for our own code.** No `LICENSE` file in the repo. T&C: if none is given, "NASA will distribute your
   original content under an Apache 2.0 license". Decide whether to add one (e.g. Apache 2.0 or MIT).
4. **NASA Earth data.** The objectives say "Using open NASA Earth data together with available Moon and Mars
   data". Our Earth side uses ESA/Copernicus data (DEM, WorldCover); the only NASA Earth data is the Blue Marble
   globe image. NASA Moon data (LOLA, PGDA, SLDEM2015, Diviner, LROC) is central. Relevance may lose a point here.
   Say it honestly in the description; MODIS LST is in the criteria doc but not used.
5. **Team details** the repo does not have: full names of all members, Mateo's role, whether there is a fourth
   member, and that all are confirmed (not waitlisted) for the Barcelona event.
6. **"Apollo 11 site"** appears as a place name in the app's Moon card. The SI rule bans NASA "mission identifiers"
   in generated content; we use it as a location name only, no patch or logo. Probably fine; a human should agree.
7. **Night-run numbers.** The draft uses the numbers in `outputs/` (9 regions, 228 cells, 5 ranked craters) and
   marks every place to update with `[UPDATE]`.

Unverified items (and why):
- Licences of globe.gl, MapLibre GL JS and Terrain Tiles on AWS: not stated with a licence name in the repo, so
  the draft lists them as "licence: [check]".
- Whether the Barcelona Local Lead has extra local rules or an earlier local deadline: the event page only shows
  the schedule ("17:30 Pitch competition" on Sunday). Ask the Local Lead.

Data downloaded (size): none (web pages only).

---

## Sources (read 14 Nov 2026)
| Key | Page |
|---|---|
| [CH] | Challenge page, Details tab: https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/ |
| [RES] | Challenge page, Resources tab: https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources |
| [SG] | Project Submission Guide: https://www.spaceappschallenge.org/resources/project-submission-guide/ (also the PDF in the team folder) |
| [JG] | Judging & Awards Guide: https://www.spaceappschallenge.org/resources/judging-awards-guide/ |
| [FAQ] | Participant FAQs: https://www.spaceappschallenge.org/resources/participant-faqs/ |
| [TC] | Terms & Conditions (Legal): https://www.spaceappschallenge.org/legal/ |
| [BCN] | Barcelona event schedule: https://www.spaceappschallenge.org/2026/local-events/barcelona/?tab=schedule |

Status: **done** = in the repo and meets the rule · **partly** = started, something missing · **missing** · **human** =
can't be checked from the repo · **n/a** = does not apply to us.

## 1. Deadlines (Barcelona = CET, UTC+1)
| # | Requirement | Source quote | Status |
|---|---|---|---|
| 1.1 | Submission closes **Sun 15 Nov 2026, 23:59 CET** | [SG] "Project submission closes on Sunday, November 15 at 11:59 p.m. in accordance with the time zone of your team’s Local Event." | **missing** (not submitted yet). Aim to submit by ~17:00, before the pitch, then edit |
| 1.2 | Late saves don't count | [SG] "Any projects saved or submitted past this deadline will not be eligible for judging." | – |
| 1.3 | Can resubmit until the end; last save counts | [SG] "You may edit and resubmit your project as many times as you'd like until the end of the hackathon. Only your last saved submission will be reviewed by the judges." | – |
| 1.4 | Local pitch: **Sun 15 Nov, 17:30** at 42 Barcelona | [BCN] "17:30 🎤 Competición de pitches / Pitch competition" | **partly** (deck skeleton, 7 slides, outside the repo) |
| 1.5 | Local judging may differ from global times | [SG] "Check with your Local Lead about times for your Local Event’s local judging and awards which may differ from the global submission times." | **human** (ask the Local Lead) |

## 2. Eligibility
| # | Requirement | Source quote | Status |
|---|---|---|---|
| 2.1 | Answer an official challenge | [JG] "Respond to one of the official NASA Space Apps Challenges." | **done** (CLAUDE.md: "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars") |
| 2.2 | All members registered at the same Local Event, not waitlisted, on the Members tab; max 6 | [JG] "have chosen the same Local Event (and are not waitlisted) ... and appear on the Members tab of your Team’s page. ... Teams may have no more than six (6) members." | **human** |
| 2.3 | All required fields complete | [SG] "All required fields in the project form must be completed." | **partly** (drafts in `SUBMISSION_DRAFT.md`) |
| 2.4 | English on the page and in linked materials | [SG] "All content in the project form must be in English." / "Slide decks must be in English." | **done** for repo, app and deck skeleton |
| 2.5 | Two check boxes: Terms & Conditions, and original work with all external resources listed in References | [JG] "...all external resources including code, text and images (even if they are open source or freely available) used in the project are listed in the References field..." | **partly** (reference list drafted; tick boxes at submission) |
| 2.6 | China funding restriction review | [JG] "teams will undergo review for prohibited bilateral activity with China, or a Chinese-owned entity" | **human** (nothing in the repo suggests it applies) |

## 3. Project page fields [SG] "Project Page Form Field Instructions"
| # | Field | What it asks (quote) | Status |
|---|---|---|---|
| 3.1 | Project Name | "What is the name of your project?" | **partly**: options in the draft; team kept "Earth Twins of the Moon" |
| 3.2 | High-Level Project Summary | "What did you develop? How does it address the challenge? Why is it important?" | **partly** (draft) |
| 3.3 | Link to Project Demo | "either in the form of a 7-slide presentation (including title and introductory slides) or a 30-second or less video presentation ... provide a publicly accessible link" | **partly**: 7-slide skeleton exists (claude.ai artifact, not in the repo); needs final numbers, screenshot, names and a public link |
| 3.4 | Link to Final Project | "Share a publicly accessible link to your final project ... should not require a password, permission, or registration" | **partly**: repo https://github.com/TLCasparS/EspaceOdyssey is public (HTTP 200); hosted app **missing** |
| 3.5 | Detailed Project Description | "What exactly does it do? How does it work? What benefits does it have? What do you hope to achieve? What tools, coding languages, hardware, or software did you use" | **partly** (draft) |
| 3.6 | Use of Super Intelligence (SI) | "Did you utilize any Super Intelligence (SI) tools ... If yes, how did you use them?" | **partly** (draft from `AI_USAGE.md` + app footer) |
| 3.7 | NASA Data | "Provide specific details about what NASA data and resources you used. To be eligible for a Global Award, you must use at least one NASA data or resource." | **done** in substance (LOLA LDEM, PGDA illumination, SLDEM2015, Diviner, Blue Marble, CGI Moon Kit); text in draft |
| 3.8 | Space Agency Partner Data and Other References | "List all of the data, resources, and tools used in your project. Resources should include any code, text, and images" | **partly** (draft list; licences of 3 libraries/data to check) |
| 3.9 | Images on the page | "The Project page DOES allow for the upload ... of images (JPG, PNG, GIF up to 10MB). However, it DOES NOT allow for the upload of videos or documents." | **missing**: pick 1–3 app screenshots |

## 4. Demo rules
| # | Requirement | Source quote | Status |
|---|---|---|---|
| 4.1 | Max 7 slides incl. title/intro, or video ≤ 30 s; over the limit = not eligible | [SG] "Adhere to the 30-second and 7-slide limits. Projects that exceed these limits will not be eligible for Global Judging." | **done** for the skeleton (exactly 7: cover, team, problem, how, app, results, future). Keep it at 7 |
| 4.2 | Hosted externally, public, no login | [SG] "ensure the link is publicly accessible. You will not be able to upload your video or slides to the NASA Space Apps website." | **missing** (export to PDF/Google Slides, share publicly, test in a private window) |
| 4.3 | Slides show team name, member names, the challenge | [SG] "Ensure that the content of your slides address the following: Team name / Names of team members / The challenge your team selected" | **partly** (team slide has `[surname]` placeholders) |
| 4.4 | Slides show the project, the user experience, how NASA/agency data makes it possible | [SG] "Display an image of the project / Describe the user experience / Include how NASA and space agency open and space based data and technology make your solution possible" | **partly** (app slide has a screenshot placeholder; data chips on the "How" slide) |
| 4.5 | Video in another language needs English subtitles | [SG] "it MUST include English language subtitles" | n/a (slides) |

## 5. SI (AI) use, branding, people, licences
| # | Requirement | Source quote | Status |
|---|---|---|---|
| 5.1 | Say where and how SI was used | [FAQ] "Each team's project submission must include a description of how SI tools were used during the development of their project." | **partly**: `AI_USAGE.md`, app footer, `ai-assistance` meta tag, `Co-Authored-By` lines; submission text drafted |
| 5.2 | Code and data made with SI: acknowledge in text **and metadata** | [SG] "Code and data: Must acknowledge SI generation in descriptive text and metadata." | **done** for the app (footer + meta tag + commit trailers) and pipeline (`AI_USAGE.md` + commit trailers); `docs/ai_usage/task*.md` to merge into `AI_USAGE.md` |
| 5.3 | SI images/video need a visible watermark | [SG] "Images and videos: Must include a visible watermark to indicate SI generation." | **n/a**: no AI-generated images or video (app README, footer). Keep it that way in the deck |
| 5.4 | SI must not come up with the idea | [SG] "SI should not be used to (come up with your idea of how to solve the challenge)." | **human** (the team confirms; the repo shows the idea and criteria in the team's criteria doc) |
| 5.5 | No NASA branding or design elements | [SG] "Generated content may not use, contain, or modify any NASA branding or design elements (such as the NASA logos, flags, or mission identifiers)." | **done** for logos (app README "Branding"; no logo files in `app/assets`). **human** for "Apollo 11 site" as a place name (open point 6) |
| 5.6 | No likeness of people under 18 | [SG] "may not include any images, video, audio, or other likeness to persons under 18 years old" | **done** (no photos of people in the app; `photos/` is empty). Check the final deck |
| 5.7 | Cite every source | [TC] "You must cite every source that is used in the creation of your project, even if it is open source or freely available." | **partly** (draft list) |
| 5.8 | Third-party materials free without restriction or OSI-licensed; licences listed | [TC] "you are responsible for ensuring that your Solution Materials are freely and publicly available without restriction or, at a minimum, are also licensed as open source" / "Any licenses applicable to your Solution Materials must be identified in the documentation" | **partly**: EOX Sentinel-2 cloudless is CC BY-NC-SA (open point 2); 3 licences to check |
| 5.9 | Own content is open; Apache 2.0 if no licence given | [TC] "If you do not specify a specific OSI compliant license, NASA will distribute your original content under an Apache 2.0 license." | **missing** `LICENSE` (open point 3) |
| 5.10 | No copyrighted material without permission | [JG] "my team has not used any copyrighted materials (i.e., music, images, text, etc.) that we don’t have permission to use" | **partly**: site notes quote/link sources; images are NASA (public domain) and EOX (see 5.8) |

## 6. Challenge objectives → our work
| Objective / consideration | Source quote | What we have (repo) | Status |
|---|---|---|---|
| Use open Earth, Moon and Mars data from NASA and other agencies | [CH] "Using open NASA Earth data together with available Moon and Mars data from other space agencies and open sources" | Moon: NASA LOLA LDEM 80°S, PGDA illumination, SLDEM2015 (LOLA + JAXA Kaguya), Diviner values. Earth: ESA Copernicus DEM GLO-30/90, ESA WorldCover. NASA Earth: Blue Marble (display only) | **partly** (NASA Earth data thin; Mars parked) |
| Identify and characterize Earth analogs for Moon bases | [CH] "identify and characterize one or more locations on Earth that could serve as useful analogs for candidate permanent Moon-base locations" | Pipeline ranks craters against Shackleton (Polar); Mare target from 20 lunar mare cells; per-criterion values in `outputs/` | **done** (Polar), **partly** (Mare: target done, Earth results from the night run) |
| Explain where the analogy holds and where it breaks | [CH] "Explain which characteristics or processes provide a strong analogy, where the analogy breaks down" | Card chips "closest to the Moon" / "what it lacks"; facts no Earth place can match (Grazing sun 1.91° max Sun elevation; Mare day–night swing); light limitation (Sun disc vs Sun centre) | **done** |
| Present as a map, visualization or tool | [CH] "present your findings as a map, visualization, or other tool" | App: Earth globe with heatmap and searched regions, Moon globe, ranked list, cards with radar, 3D terrain | **done** (not hosted yet) |
| Look beyond well-known sites; search systematically | [CH] "Look beyond well-known analog sites" / "develop a method for systematically searching Earth" | Method searches grid cells, not hand-picked sites; tuning sites excluded from results; world prescreen + night run planned (`docs/NIGHT_RUN.md`) | **partly** (world-scale results pending; don't claim them before they exist) |
| Remember Earth's limits | [CH] "Earth cannot reproduce important lunar and Martian conditions such as reduced gravity, the lunar vacuum, the thin Martian atmosphere, or their radiation environments." | Grazing sun and temperature facts in the app; gravity/vacuum/radiation not mentioned | **partly** (one sentence added in the draft description) |
| Connect to exploration | [CH] "Explain how the location or process you identify could help ... test instruments or technologies, prepare robotic or human operations" | Practical/ground values (drivable, bare ground, base pad slope); deck "Real training" | **partly** (keep claims general) |

## 7. Judging criteria [JG] (each scored 1–5) → where we are strong or weak
| Criterion | Source quote | Our evidence | Gap / action |
|---|---|---|---|
| Impact | "addressing either a minor or major problem ... The extent to which it inspires or helps others" | Open, repeatable way to rank Earth analogs for lunar bases; anyone can use the app in a browser | Say who would use it (analog-campaign planners, rover teams) without claiming users we don't have |
| Creativity | "introduces a novel concept ... or presents an improvement upon existing ideas in a meaningful way" | Same code measures Earth and Moon on one 60 m grid; light simulation of Earth craters vs the lunar pole; Earth + Moon globes linked | Show the "same ruler for both worlds" idea on the "How" slide |
| Validity | "grounded in scientific principles and demonstrates technical, functional, or logical feasibility" | Frozen configs (`config-v1`, `mare-v1`) with tests; predictions written before validation (`docs/VALIDATION_config-v1.md`); honest misses (Haughton, Askja, Tenoumer) shown in the app | Strongest point. Keep the misses in the deck ("Honest limits") |
| Relevance | "meaningfully integrates NASA data, utilizing it as a core component" | LOLA LDEM defines the Polar target; PGDA illumination the light criteria; SLDEM2015 the Mare target | NASA Earth data is thin (open point 4) |
| Presentation | "clearly conveying the challenge, their proposed solution, and its significance ... Judges evaluate the demo and full project" | Deck skeleton in app colours; app with 3D views | Final numbers, one strong screenshot, public links, names |
