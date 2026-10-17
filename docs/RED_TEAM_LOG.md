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
