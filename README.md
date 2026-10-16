# transit-map

WMATA entrance inventory and OpenStreetMap mapping review. The project identifies
existing entrances, incomplete tagging, and records that need independent location
verification before an OSM edit.

## Current state

The October 16, 2026 snapshot contains **242 named WMATA entrance-view records
across 98 stations**, **714 OSM features**, and **14 desktop reviews**.

| Desktop outcome | Records |
| --- | ---: |
| Matched to an existing OSM entrance or elevator | 5 |
| Access geometry exists; exact entrance/tag position unverified | 9 |

The other 228 records have automated proximity screens, not completed desktop
reviews. No new OSM entrance has yet been confirmed necessary, and no OSM edits
have been submitted. Read the [review queue](docs/REVIEW_QUEUE.md).

**Location provenance matters:** the WMATA Station View coordinates were extracted
from Google panorama URLs embedded on WMATA's website. They are research reference
points, **not OSM upload coordinates**. Independently verify edit positions with
field observations or OSM-permitted imagery. See [data sources](docs/DATA_SOURCES.md).

## Run locally

Python 3.10+; no third-party runtime dependencies. Run these commands from the
repository root:

```sh
python -m transit_map validate
python -m unittest discover -s tests -v
python -m transit_map audit --output build/audit.json
python -m transit_map review-queue --output build/review-queue.md
```

The audit produces **research candidates**, preserves desktop reviews separately,
flags multiple WMATA records pointing to one OSM feature, and never labels an
unmatched record as a confirmed missing entrance. It measures distance to actual
OSM geometry rather than a way's center. [Methodology](docs/METHODOLOGY.md) explains
the thresholds and limits.

## Refresh the sources

These commands make read-only requests. They write to ignored `build/` paths and
do not replace the committed snapshot:

```sh
python -m transit_map fetch-wmata --output build/wmata.json
python -m transit_map fetch-osm --output build/osm.geojson
python -m transit_map validate --inventory build/wmata.json --osm build/osm.geojson
python -m transit_map audit --inventory build/wmata.json --osm build/osm.geojson
```

Responses are cached and requests are paced. Add `--refresh` to bypass cached
responses. A partial fetch exits unsuccessfully and records its failures. OSM
refreshes use the 98 recorded station-area windows; inspect their coverage before
using a refreshed WMATA inventory with changed or additional entrance locations.
New station URLs must be added to `data/wmata/stations.json` explicitly.

Existing entrance IDs survive source reordering. New descriptions receive hashed
IDs when no existing source view or unique exact label matches. Source-view identity
is checked before labels; ambiguous normalized labels are reported rather than
deduplicated. Human reviews join on stable IDs, never spreadsheet row numbers.

## Repository data

| File | Purpose |
| --- | --- |
| [data/wmata/entrances.json](data/wmata/entrances.json) | 242 source descriptions, stable IDs, and explicitly restricted research reference points |
| [data/wmata/stations.json](data/wmata/stations.json) | 98 current WMATA source URLs and station-universe provenance |
| [data/osm/features.geojson](data/osm/features.geojson) | 714 unique OSM features with actual point, line, or area geometry; 98 query windows and stop-area evidence |
| [data/reviews.json](data/reviews.json) | 14 desktop outcomes with OSM feature links, source maps, and remaining checks |
| [data/research/audit_snapshot.csv](data/research/audit_snapshot.csv) | The reviewed spreadsheet's 242-row audit snapshot, including its original center-based distances |
| [data/snapshot.json](data/snapshot.json) | Snapshot counts and review totals |

The source-feature tab in the working spreadsheet contains a narrower subset:
453 features within 100 m of the panorama points. The repository retains all
714 tagged entrance/elevator features returned by the 98 station-area queries,
including nearby building doors that may be unrelated to Metro. OSM data is
attributed to **OpenStreetMap contributors** and is available under the
[ODbL](https://www.openstreetmap.org/copyright). Other source material retains its
applicable rights; the repository does not relicense it as OSM contribution data.

## Next validation step

Start with one pending entrance in the review queue. Establish its actual threshold,
existing OSM node/way connection, street/level access, and a permitted source for
any new position or tag. Record the evidence before preparing an edit. The CLI
does not generate or submit OSM change files.
