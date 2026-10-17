# Incremental red-team log

## Pass 1 — baseline ceff5f4 (2026-10-16)

External review reproduced 242 source records / 98 stations / 714 OSM features / 14 desktop reviews, 20 passing tests and 342 generated pages. It identified a Reston directional contradiction, possible cross-side candidate reuse, query-window sensitivity, and transaction/publication inconsistencies. The geographic allegations remain unresolved; none is promoted into a corrected research observation by this pass.

## Step 2 — transaction probes and queue corrections (2026-10-16)

Each probe used a separate temporary copy of the unchanged baseline and a synthetic transaction. Test data never entered the canonical ledger.

| Probe | Expected behavior | Observed at ceff5f4 | Disposition |
| --- | --- | --- | --- |
| Add a valid `New entrance needed` review | Review visible in tasks and CLI queue | Materialization succeeds; both outputs omit it | Confirmed defect; fixed by shared, complete worklist |
| Add a review with no `notes` | Validation rejects unusable review | Materialization succeeds; publication raises `KeyError: notes` | Confirmed defect; reject absent, blank, or nontext notes during validation |
| Add station plus entrance | Explicitly enforce snapshot coverage | `ValueError: OSM query coverage mismatch` | Membership extension remains unsupported pending snapshot migration; documented |
| Update existing station source URL with correct before hash | Materialize and publish | Both succeed | Refutes the broader claim that no station transaction can pass |

Regression coverage applies every allowed review status through a transaction and checks both HTML tasks and CLI output. It also checks missing/blank/nontext notes, station metadata updates, station membership rejection, all-record visibility, and a confirmed review whose automated candidate is shared.

Both task outputs now list all 242 source records. The baseline has 31 records with shared automated candidates, and all 31 receive an explicit identity-review reason regardless of distance or desktop status. There are 237 records with open review reasons and five desktop-confirmed records without open reasons. These are workflow states, not findings that entrances are missing. Automated screen labels/counts and baseline source/review assertions are unchanged.

### Remaining work

- **F1 unresolved:** use WMATA access maps and OSM geometry to investigate Reston north/south identities, then Herndon. Live OSM alone does not establish which source/review is wrong.
- **F2 partially addressed:** all records and reuse conflicts are now exposed. Cross-side identity validation itself has not been performed.
- **F3 unresolved:** assess query-window sensitivity separately; zero tagged features in a small window does not establish physical absence.
- **F4 bounded:** publication omissions and missing-notes acceptance fixed. Station membership changes still require a versioned OSM snapshot migration; metadata updates work.

Executable regressions: `tests/test_red_team.py`. Reproduce with `python -m unittest discover -s tests -v`, then `python -m transit_map validate`, `python -m transit_map audit`, `python -m transit_map review-queue` and `python -m transit_map.build`.

## Step 3 — Reston and Herndon directional review (2026-10-16)

Scope: existing OSM query snapshots, visual inspection of WMATA's June 2025 vicinity maps for both stations, and a live OSM API check of six key nodes. All six retain the versions/coordinates in the recorded snapshot. Source panoramas were not visually inspected, and there was no field survey. The evidence extract retains node versions, selected access ways, road context, map URLs and SHA-256 hashes, and reproducible reference distances in [reston-herndon-2026-10-16.json](evidence/reston-herndon-2026-10-16.json). OSM-derived evidence is attributed under ODbL; source reference distances remain research-only.

### Reston: directional identity supported; source-reference conflict remains

The independent WMATA map distinguishes the north pavilion on the Sunset Hills Road side from the south pavilion beside the south bus bays. Recorded OSM roads and access ways place these features on the corresponding sides of the Dulles corridor:

| Feature | North | South |
| --- | --- | --- |
| Tagged railway entrance | node/7433034321 | node/7432921910 |
| Elevator | node/13853418711 | node/13853391339 |
| Entrance vertical connection | way/794703764 | way/794694302 |

The existing north entrance/elevator reviews remain supported. The south-labelled references (WMATA-173/175) are only 48.9 m from the north entrance and 44.6 m from the north elevator, but 154.0 m and 138.6 m respectively from their south counterparts. This explains why proximity retrieves the wrong side for the intended south-access description. It does not establish whether the panorama coordinate, panorama selection, or source label caused the inconsistency. The two south reviews therefore use `Source location needs correction`; no replacement coordinates are invented. Separate mapped south geometry is recorded as evidence, without approving an OSM edit.

**F1 disposition:** the hypothesis that the original review swapped the mapped north/south features is not supported by the map/topology check. The north-side identities are retained, while the south source-reference inconsistency remains open for visual source or survey verification.

### Herndon: Park and Ride is south, not north

The WMATA map puts the Park and Ride/parking garages and south bus bays south of the highway. Node/3105651341 matches the south pavilion and node/7432921936 the north pavilion. The earlier external characterization of the Park and Ride as north was incorrect.

| Source | North-node distance | South-node distance | Outcome |
| --- | ---: | ---: | --- |
| WMATA-102 Park and Ride | 227.1 m | 40.8 m | Broad south-side source view; distinct physical entrance identity remains unverified |
| WMATA-103 585 Herndon Pkwy | 1.4 m | 199.6 m | North entrance confirmed by description, map and access geometry |
| WMATA-104 South Busbay elevator | 198.9 m | 30.2 m | South access exists; specific elevator geometry unverified |
| WMATA-105 585 Herndon Pkwy elevator | 29.6 m | 204.3 m | North access exists; specific elevator geometry unverified |
| WMATA-106 South Busbay | 199.2 m | 4.5 m | South entrance confirmed by description, map and access geometry |

Candidate reuse by WMATA-102 and WMATA-106 is not evidence of a cross-side conflict. Nor does it prove the two source views identify distinct physical entrances. Both IDs are retained. The WMATA map depicts north- and south-pavilion elevators (and a separate garage elevator); the recorded Herndon query contains no elevator-tagged feature. Nearby railway entrances and wheelchair tags do not resolve the elevator identities, and missing tags do not prove physical absence.

### Changes and limits

Transaction `2026-10-16-001-reston-herndon-directional-review.json` updates two existing north-side reviews and adds seven reviews. Materialized review count is now 21: seven existing entrances confirmed, twelve geometry/position unresolved, and two source-location inconsistencies. Frozen source files, OSM snapshot, automated screens and research-reference coordinates are unchanged. No OSM changes submitted.

The review-worklist policy continues to flag shared candidates even when a desktop match is supported. Other reuse groups (Gallery Place, Grosvenor, Largo and others), query-window sensitivity, and exact Herndon elevator geometry remain open. This step resolves two specific allegations; it does not validate all automated candidates or certify station accessibility.

## Step 4 — Gallery Place A/D candidate identity (2026-10-16)

The A/D reuse group is a confirmed automated candidate identity mismatch for A. The source inventory names A at 7th/F and D as an elevator at 7th/G. The independent WMATA vicinity map (December 2025) depicts separate escalator and elevator access along 7th Street. The recorded OSM geometry has four distinct entrance nodes with references A/B/C/D; all four belong to stop-area relations 359558 and 7945932. Live OSM checks retain the recorded versions, tags and coordinates for the four nodes.

| Source entrance | Supported OSM identity | Distance from research reference | Automated candidate |
| --- | --- | ---: | --- |
| A / WMATA-082 | node/324153442, ref=A | 80.7 m | node/9951151070, ref=D, 37.1 m — wrong identity for A |
| B / WMATA-083 | node/9951151069, ref=B | 56.2 m | Same B node |
| C / WMATA-084 | node/324153414, ref=C | 76.3 m | No selected candidate within the screen threshold; existing review already confirms C |
| D / WMATA-085 | node/9951151070, ref=D, elevator | 39.3 m | Same D node |

This is a specific demonstration that proximity can select a different entrance while the intended entrance already exists. The A/D source references do not justify merging the entrances. No missing entrance or new geometry is established. D's source street description is preserved verbatim; identity rests on reference, elevator type, map location and topology, not a precise interpretation of the named intersection.

Transaction `2026-10-16-002-gallery-place-identities.json` adds A/B/D desktop confirmations. C's existing confirmation is retained. Materialized totals are now 24 reviews: ten confirmed, twelve geometry/position unresolved, two source-location conflicts. Complete accessibility routes, current equipment operation and the source panoramas were not verified. Automated screen values are intentionally retained as reproducible candidate retrieval; the desktop reviews reject the A candidate interpretation. The worklist continues to expose the A/D reuse warning.

Evidence: [selected OSM topology, live node checks, map hash and reference distances](evidence/gallery-place-2026-10-16.json). Source files and coordinates are unchanged, and no OSM edit was submitted. Remaining reuse groups include Grosvenor and Largo; window sensitivity remains open.

## Step 5 — Grosvenor east/west access geometry (2026-10-16)

The WMATA vicinity map (June 2026), inspected visually, explicitly marks a tunnel to the station on the west side of Rockville Pike. OSM already contains the west approach and crossing tunnel; the screen instead assigns the west source view to an east-side tagged entrance node.

| Source | Automated selected node | Distance | Independent/contextual evidence | Outcome |
| --- | --- | ---: | --- | --- |
| WMATA-099 east view | node/9127756071 | 10.9 m | East access footways 263159301 and 987506650 | Geometry present; exact view/threshold identity unverified |
| WMATA-100 second east view | node/9127756072 | 13.9 m | East end of access system, connected to tunnel via steps/escalator 263159300 | Geometry present; distinct physical entrance identity unverified |
| WMATA-101 west view | node/9127756072 | 45.8 m | West tunnel endpoint node/2687926494 is 2.5 m from research reference; west approach way/263159296 connects to tunnel way/263159299 | Existing west access, not an identity match to the east tagged node |

The tunnel runs from node/2687926494 to node/2687926496; steps/escalator way/263159300 then reaches node/9127756072 on the east side. The west endpoint has no tags. This supports existing access geometry at the west source description, without establishing the appropriate station-entrance threshold or tag. No new path, standalone entrance, or entrance-tag change is justified by this desktop review alone.

WMATA-099 and WMATA-100 have identical labels after whitespace normalization, different panorama URLs, and nearby but distinct tagged OSM nodes. Neither the label duplication nor proximity establishes whether the source views describe distinct physical entrances. Both stable source IDs remain; no physical-entrance count is inferred. All three reviews use `Geometry present; entrance position unverified`.

Transaction `2026-10-16-003-grosvenor-access-geometry.json` adds three reviews. Materialized review total is now 27: ten confirmed, fifteen geometry/position unresolved, two source-location conflicts. A live check of the two railway nodes, west tunnel endpoint and three west-access ways retains recorded versions. [Evidence extract](evidence/grosvenor-2026-10-16.json) preserves versions, topology, map URL/hash and research distances. Source panoramas, current field conditions and complete accessibility paths were not inspected.

Automated screen counts, source coordinates and frozen baseline remain unchanged; no OSM edits submitted. Largo is the next named reuse group. Query-window sensitivity and other shared-candidate records remain open.

## Step 6 — Downtown Largo shared candidate (2026-10-16)

The WMATA vicinity map (June 2026), visually inspected, shows station access at distinct ends of the station/parking complex. The source inventory has a Lottsford Road (North) view and a Truman/Largo Drive view. Both retrieve the sole railway entrance tag in the recorded window, node/8651370043; this is not sufficient to identify both source descriptions as the same entrance.

| Source | Candidate distance | Additional evidence | Desktop outcome |
| --- | ---: | --- | --- |
| WMATA-051 Lottsford Rd. (North) | 55.2 m | North-area footway 1129902875, junction 11134904569, and footway 1200929257 exist, but no verified threshold/vertical connection identified | Geometry present; entrance position unverified |
| WMATA-052 Truman/Largo Dr. | 9.7 m | Tagged node on southern/southeastern boundary of building 613454503, connected to approach footway 942949375; consistent with the map's southern access area | Existing entrance confirmed |

The map-side and topology evidence support the southern match. They do not identify the north view's exact threshold, establish a missing north entrance, or justify reusing the south node as that identity. The north approach's untagged node 10467379951 lies on a bus-platform boundary, so it is not promoted into a station entrance. No new coordinates or tags are proposed. Current equipment operation and full accessibility routes were not checked.

Transaction `2026-10-16-004-largo-access-identities.json` adds two reviews. Materialized total: 29 reviews (eleven confirmed, sixteen geometry/position unresolved, two source-location conflicts). Three nodes and four ways checked live retain their recorded versions. [Evidence extract](evidence/largo-2026-10-16.json) retains selected geometry, versions, map URL/hash and reference distances. Source panoramas and field conditions were not inspected.

This completes an initial desktop pass over the five named reuse examples: Reston, Herndon, Gallery Place, Grosvenor and Largo. It does not complete review of all 31 shared-candidate records. Automated screen counts, source coordinates and frozen baseline are unchanged; no OSM edits submitted. Remaining work includes the other reuse groups, north Largo's threshold, Herndon's elevator geometry, Reston's source-reference conflict, and query-window sensitivity.

## Step 7 — Judiciary Square general entrance versus elevators (2026-10-16)

Inventorying the remaining 18 unreviewed shared-candidate records identified the Judiciary Square trio as an available next group. The WMATA vicinity map (June 2025) places north escalator/elevator access by F Street; the operator equipment page separately describes street-to-platform elevators for Glenmont and Shady Grove. These are different identities, not three independent confirmations of one nearby entrance.

- WMATA-114's general F Street entrance matches node/3621904756 and steps way/356785101; desktop identity confirmed. Reference distance: 48.9 m.
- WMATA-115 and WMATA-116 name different platform-specific elevators. Both select the same general entrance, tagged wheelchair=no, as their screen candidate. Two separate elevator nodes (9981798981 and 9981798982) and their sidewalk/room geometry exist. Both references also retrieve 9981798982 as nearest elevator; neither nearest-entrance nor nearest-elevator retrieval establishes the platform-direction assignment.
- The inspected map, recorded tags and geometry do not identify which elevator node serves which direction. Both elevator reviews remain `Geometry present; entrance position unverified`. No elevator is declared missing, duplicated or assigned a platform direction.

Three live node checks retain the recorded versions. [Evidence extract](evidence/judiciary-2026-10-16.json) preserves selected access geometry, operator source links, map hash and distances. Equipment operation, source panoramas, field conditions and complete accessible routes were not verified.

Transaction `2026-10-16-005-judiciary-elevator-identities.json` adds three reviews. Totals: 32 desktop reviews (twelve confirmed, eighteen geometry/position unresolved, two source-location conflicts). Fifteen of the 31 shared-candidate records still lack desktop review. Baseline/source coordinates and automated screens are unchanged; no OSM edits submitted.

## Step 8 — Farragut West 18th/I entrance and elevator (2026-10-16)

WMATA-065 and WMATA-066 both select named railway entrance node/1643428783. The general entrance reference is 15.6 m away; the elevator-labelled reference is 3.4 m away. The WMATA map (June 2025) separately shows escalator and elevator access at the northwest 18th/I corner.

The node's steps/escalator connection (way/1429421926) and footway (way/1429421925), together with operator-map location and source description, support the general entrance match. The node lacks highway=elevator; the recorded query contains no elevator-tagged feature, including no raw element with an elevator key/value. This is not evidence of physical absence or a basis to tag the general steps-connected node as an elevator. Exact elevator position, level connection and suitable existing geometry remain unverified.

Transaction `2026-10-16-006-farragut-west-elevator-review.json` adds one general entrance confirmation and one `Geometry present; entrance position unverified` review. The live railway entrance node retains its recorded version. [Evidence extract](evidence/farragut-west-2026-10-16.json) contains the selected topology, map hash, live node check and research distances. No source panorama, field condition, current operating status or full accessible route was verified.

Totals: 34 desktop reviews (thirteen confirmed, nineteen geometry/position unresolved, two source-location conflicts). Thirteen shared-candidate records remain unreviewed. Baseline/source coordinates and automated screens are unchanged; no OSM edits submitted.

## Step 9 — McLean shared candidate and vertical semantics (2026-10-16)

The Scotts Crossing general and elevator source views (WMATA-129/128) both select railway entrance node/10242056060, respectively 8.0 m and 9.6 m from their research references. However, the node also belongs to railway platform area/810065189 tagged level=2 and layer=2. Its connected footway/1119813162 has no explicit level. A second railway entrance node/13334336661 belongs to station building/227612806 and connects to footway/1453963154. This is an unresolved level/threshold association, not a basis to count two street entrances or select the nearest one as confirmed.

The independent WMATA vicinity map (June 2025) depicts entrance/elevator access on the station side and across Dolley Madison Boulevard. It does not establish the exact surveyed street thresholds or resolve the OSM level associations. The nearby elevator candidate, node/13325542089, is tagged level=0;-1;-2;-3;-4 and connected to footway/1453014394, but this review establishes no station-serving identity. It must not be promoted into a station elevator based on proximity, and a wheelchair=yes entrance tag is not a specific elevator identity.

Transaction `2026-10-16-007-mclean-level-identities.json` adds two `Geometry present; entrance position unverified` reviews. [Evidence extract](evidence/mclean-2026-10-16.json) includes node/building/platform membership, approach geometry, live checks and research distances. All three live key nodes retain recorded versions. No source panorama, field conditions, surveyed level, current equipment operation or complete accessibility path was verified.

Totals: 36 desktop reviews (thirteen confirmed, twenty-one geometry/position unresolved, two source-location conflicts). Eleven shared-candidate records remain unreviewed. The Colshire-side McLean source views are outside this pair's scope and remain unreviewed. No baseline/source coordinate or automated-screen changes; no OSM edits submitted.

## Step 10 — Pentagon City east access and source freshness (2026-10-16)

WMATA-162/163 share named railway entrance node/449437258 on the east side of Hayes Street. The general view is 15.5 m away; the elevator view 18.0 m away. Source description, WMATA map (June 2025) and sidewalk/1086281513 support the general east entrance identity. They do not identify the elevator's exact geometry: the shared node is wheelchair=yes but not highway=elevator, and the recorded window has no elevator-tagged feature, including no raw element with an elevator key/value. Nearby railway node/11767528252 connects to steps, not a verified elevator. Exact elevator position and vertical route remain open.

### Independent source-coverage task

Arlington County's [second elevator project page](https://www.arlingtonva.us/Government/Projects/Project-Types/Transportation-Projects/Pentagon-City-Metro-Station-Second-Elevator) reports completion on September 17, 2025, with a second street-level elevator installed/open on the west side of Hayes Street at 12th Street South. The June 2025 vicinity map predates that event. The recorded three WMATA source views include general east access, east elevator and general west access, but no separately labelled west elevator. A general west view may include additional access; no claim that the source omits all west access is made.

This independently documented opening requires inventory reconciliation before treating the scraped views as complete. It is not used to invent a fourth Station View record, reuse a coordinate from the county's embedded map, or assert where to edit OSM. The task remains documented in the log and existing review notes; the current publication's worklist only contains existing source records, so this additional source-coverage task is not a standalone published entrance record. A bounded future source/task schema change may be needed to expose such discoveries directly.

Transaction `2026-10-16-008-pentagon-city-elevator-review.json` adds one general entrance confirmation and one geometry/position unresolved review. Two live OSM nodes retain recorded versions. [Evidence extract](evidence/pentagon-city-2026-10-16.json) preserves selected geometry, node checks, map hash and the county's dated factual claim without map coordinates. No source panorama, field condition, full accessibility path or current operating status verified.

Totals: 38 desktop reviews (fourteen confirmed, twenty-two geometry/position unresolved, two source-location conflicts). Nine shared-candidate records remain unreviewed. The existing general west source record is outside this pair's scope. Baseline/source coordinates and automated screens are unchanged; no OSM edits submitted.

## Step 11 — Complete initial pass on remaining shared candidates (2026-10-16)

Scope: the remaining nine unreviewed shared-candidate records at Loudoun Gateway, Rosslyn, Tysons and Union Station. The four WMATA vicinity maps were visually inspected. Eleven selected nodes checked live retain the versions and coordinates in the recorded snapshots. No source panorama or field inspection was performed.

| Source IDs | Supported interpretation | Outcome |
| --- | --- | --- |
| WMATA-125 | A steps-connected railway entrance near the north busbay does not identify the station elevator; map distinguishes station and garage elevator access | Geometry/position unresolved |
| WMATA-127 | Garage doorway node/8870302198 lies on WMATA parking building/294419005 and connects to bridge/863453474, consistent with map. The screen instead selects a railway node 59.9 m away | Garage entrance identity confirmed; not a new railway threshold |
| WMATA-183 | Generic east N. Moore source view may overlap elevator access; separate western railway entrances also exist. Exact generic-view threshold is not established | Geometry/position unresolved |
| WMATA-184 | Operator map, WMATA elevator tags on node/576549187 and sidewalk/892764182 support the mapped east-side elevator access | Elevator-access identity confirmed; individual cars/route unverified |
| WMATA-212 | General railway node is not an elevator; nearest elevator way is an indoor level-1 area 234.7 m away without verified station-serving identity | Geometry/position unresolved |
| WMATA-213 | Named Tysons railway entrance and level-0 approach align with general north-side source/map access | General entrance confirmed |
| WMATA-217/218/219 | Shared south railway node cannot establish all street, terminal and upper-concourse identities. Separate north railway entrance, terminal doorway and elevator geometry exist | Three source identities/level connections unresolved |

The Union Station map shows separate north and south access. WMATA's dated 2011 access/capacity report corroborates different First Street/north-mezzanine and Amtrak-concourse contexts but is not treated as current surveyed topology. The Massachusetts Avenue reference is close to a relevant south entrance, but its upper-concourse/bus/shop route remains unverified; no full-record identity is promoted from proximity alone.

Transaction `2026-10-16-009-remaining-shared-candidate-reviews.json` adds all nine reviews: three supported access identities and six unresolved records. Evidence extracts are in `docs/evidence/remaining-reuse-*-2026-10-16.json`, preserving selected geometry, live checks, map hashes and research-only candidate distances.

### Review coverage at completion of this pass

- All **31 shared-candidate records now have an initial desktop review**. None is represented as cleared solely because a review exists; the worklist conservatively retains all 31 identity-review flags.
- Overall there are **47 reviewed source records**: seventeen confirmations (including a garage access identity), twenty-eight geometry/position unresolved, and two source-location inconsistencies. These are source-record outcomes, not counts of unique physical station entrances.
- **195 source records remain without desktop review.** Completing the shared-candidate subset is not a completeness audit of all 242 records.
- The north Largo threshold, platform-specific Judiciary elevators, McLean level semantics, source-view ambiguities, other elevator identities and Pentagon City's west-elevator source-coverage task remain open. Query-window sensitivity has not yet been tested.
- Frozen baseline, research coordinates and automated screen counts are unchanged; no OSM edits submitted.

## Step 12 — Candidate decisions and review-adjusted publication (N1/N2, 2026-10-16)

External Pass 2 (at a4cd635) found two publication defects. **N1:** a shared candidate kept its warning even after review, so 236/242 records were permanently flagged, including 11 confirmations. **N2:** `audit.json` and its counts still presented rejected candidates (Gallery Place A→D; Reston south→north) as screens, with no adjudicated summary. **N3** (labels) was addressed where it affects these outputs; **N4** (baseline evidence recovery) and **F3** (window sensitivity) are deferred.

Changes:

- Reviews may record explicit `candidate_decisions` (accepted/rejected/unresolved, feature ID, reason, evidence), validated in `core.validate_candidate_decisions` and checked for evidence-file existence during materialization.
- Worklist: only an accepted or rejected decision on the screened candidate closes the shared-candidate warning; a confirmation without an accepted decision is an open reason; status questions stay open.
- `audit.json` keeps raw screens per record and adds `candidate_decision`, `accepted_feature_id` and `review_outcome`; `summaries.raw_screening` and `summaries.review_adjusted` are published separately and shown on the index page. Entrance pages list decisions; tasks and the CLI queue use status labels.

Transaction `2026-10-16-010-candidate-decisions.json` updates 37 existing reviews with 39 decisions (17 accepted, 8 rejected, 14 unresolved). It encodes judgments already stated in the review notes; no new observation, coordinate or status change. One interpretation goes slightly beyond the note wording: WMATA-115/116 reject general steps entrance node 3621904756 (wheelchair=no) as the identity of a platform-specific elevator, because separate elevator entrance nodes are mapped; which elevator serves each direction stays unresolved. The six baseline-era confirmations cite their original note links because no evidence extract exists (N4).

Result: 17 accepted identities, 6 rejected-and-unresolved, 24 reviewed-unresolved, 195 unreviewed (sum 242). Raw screening counts are unchanged. Open worklist records fall from 236 to 225; open shared-candidate warnings from 31 to 14. Tests in `tests/test_candidate_decisions.py` cover the four specified cases (Gallery Place A rejects D with A's identity retained; Reston south rejects north with the conflict open; a supported shared candidate closes; an unresolved elevator stays open beside a supported entrance), confirmation-alone, summary reconciliation and malformed decisions. Frozen baseline unchanged; no OSM edits submitted.

### PR #12 verification

Independent review reproduced the 17/6/24/195 adjusted partition and unchanged raw screens. The WMATA-115/116 decisions reject a steps-connected general entrance as the identity of a specific elevator; they do not reject mapped elevator existence or assign a direction, so the interpretation is retained. Older confirmations remain subject to N4 evidence recovery.

Before merge, three validation gaps were reproduced and corrected: explicit null decision lists passed validation but failed downstream; nonstring decision values could raise TypeError instead of a validation error; hostless HTTPS evidence was accepted. Regressions now cover those cases and the build-time missing-evidence-file gate. Absent decision fields remain permitted for historical transaction replay; explicit null fields are rejected. Queue instructions now describe decision-based closure. No review judgments or adjusted counts changed in this verification.

## Step 13 — N4 evidence recovery tooling (2026-10-16)

**Scope, measured strictly.** An element counts as reproducible only if the OSM snapshot, its stop-area relations, or an evidence extract's element list retains it. Under that rule, **10 of the 14 baseline reviews cite 22 unique OSM elements** that no repository file retains: WMATA-021, 022, 107, 108, 142, 195, 208, 209, 210 and 211. All later reviews are reproducible. (External Pass 2 counted 12 reviews by substring matching; WMATA-172/174 are in fact covered by the Reston/Herndon extract.)

**Finding:** evidence extracts do not share a schema. `reston-herndon-2026-10-16.json` lists elements under `osm_elements`; later extracts use `elements`. The detector accepts both; schema normalization or validation is a separate task.

**Retrieval blocked in this environment.** The workspace network cannot reach `api.openstreetmap.org`, and the OSM API and Overpass both disallow automated fetching via robots.txt for the external research tool. No workaround was attempted. Recovery must run from a maintainer machine or CI.

**Tooling added (no data changes):**

- `transit_map/evidence.py` finds cited-but-unretained elements and recovers each element's **OSM history version as of the end of the review day (America/New_York)**, so the extract shows what the reviewer could have seen, not later edits. Way geometry uses node versions at the same cutoff. Contributor names/UIDs are dropped. It flags elements changed after the review, elements absent or deleted at review time, and computes research-only distances from source references.
- `python -m transit_map recover-evidence [--review ID] [--maps]` writes `build/evidence/baseline-recovery.json` using the existing cached, paced downloader. `--maps` also hashes cited WMATA vicinity maps; `edition` stays null until visually inspected. The command exits nonzero when any element cannot be recovered.
- `tests/test_evidence_recovery.py` covers cutoff selection, later-edit and deletion handling, way-node resolution, contributor stripping and distances using synthetic histories. A **ratchet test** pins the 10-review / 22-element gap: it fails if any review adds a new unreproducible citation, and allows the set only to shrink.

**To complete N4:** run `python -m transit_map recover-evidence --maps` with network access; inspect `problems` and `changed_after_review`; fill map editions after visual inspection; commit the result as `docs/evidence/baseline-recovery-2026-10-16.json`; then empty `KNOWN_UNREPRODUCIBLE`. The recovered distances should then be checked against note claims (for example, WMATA-210 says the panorama "coincides" with node 4448309368). Recovery reproduces cited geometry; it does not re-review or strengthen any outcome. Linking the extract from the ten reviews would be a separate transaction.

### PR #13 completion — evidence recovered in this session

Direct public OSM history API requests succeeded in this session. The original 22-element list covered explicit node/way forms but missed prose aliases/lists such as footways A/B/C, junctions and buildings. Extending the parser and measuring again found **35 unique missing elements across 12 reviews**, including the later Reston south review. The ratchet now checks those forms as well, and accepts retained geometry rather than an ID-only/incomplete way record.

Recovery saved `docs/evidence/baseline-recovery-2026-10-16.json`: 35 cited elements, 145 way-node coordinate dependencies with selected versions/timestamps, seven WMATA map hashes and inspected editions, no recovery problems, and no observed post-cutoff changes. Contributor user/uid/changeset metadata is excluded. `KNOWN_UNREPRODUCIBLE` is empty; citation-gap checking passes with no allowance. Raw network caches remain ignored. Earlier PR scope/counts above are preserved as history, superseded by this measurement.

Additional correctness fixes:

- Washington day boundaries now use America/New_York timezone rules, including winter offset, and exclude the next midnight itself.
- Because these reviews' calendar day was still in progress during retrieval, the effective cutoff is capped at recovery start. Both the next-midnight boundary and actual recovery timestamp are retained. End-of-day recovery remains an approximation when the original note lacks an exact observation timestamp; no future end-of-day state is claimed.
- Batched latest-node retrieval is used only when a current node's timestamp proves it predates the cutoff. Later/deleted/unreturned node cases still use full history. Dependency versions and the selection method are retained so a parent way's unchanged version cannot hide node-coordinate provenance.
- Tests cover timezone/boundary behavior, in-progress-day cutoffs, incomplete way records, prose lists and batched-node historical fallback.

The recovered WMATA-210 reference-to-node/4448309368 distance is **0.7 m**. This supports a nearly coincident reference, not exact equality and not an elevator identity. Recovered geometry retains upper-level footway/447761004 with layer=2; the original unresolved elevator/level review is not upgraded. Evidence recovery does not independently validate every narrative claim, survey a threshold, certify equipment operation or permit OSM edits.

All seven PDFs were rendered and inspected: Branch Avenue June 2026; Huntington, Minnesota Avenue, Reston Town Center, Southern Avenue and Twinbrook June 2025; Tysons December 2025. The existing review outcomes, accepted/rejected candidate decisions, source coordinates, raw screens and frozen baseline remain unchanged. F3 window sensitivity remains the next separate investigation.
