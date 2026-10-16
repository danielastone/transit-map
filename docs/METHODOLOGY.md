# Methodology

## Source inventory

The station universe is the 98 station URLs in the DC GIS regional entrance layer.
Current WMATA station-info pages expose named `stationViewEntrancesCMF` records
inside their rendered application data. The inventory includes elevator views
as separate source records when WMATA labels them separately. An empty Huntington
placeholder was excluded. Therefore 242 is a count of named source views, not a
certified count of every physical doorway or public access point.

Grosvenor-Strathmore has two east-side panorama records whose descriptions differ
only by a trailing space. Both source views and their existing IDs are retained.
Validation reports the normalized-label ambiguity; trimming and deduplicating the
labels would lose one source view. This is another reason to avoid interpreting
the inventory as a physical-entrance census.

WMATA's wheelchair flag is preserved as `Yes` or `Not marked`. The second value
means the source did not flag access; it does not mean the entrance is inaccessible.

## OSM collection

Each station's query window extends approximately 150 m beyond its outermost
WMATA reference points. The recorded bounds and exact OSM API URL are included
in `data/osm/features.geojson`. All 98 initial map requests succeeded.

The collection keeps nodes and ways with any of:

- `railway=subway_entrance` or `railway=train_station_entrance`;
- `highway=elevator`;
- any `entrance=*` tag.

Stop-area relations are retained separately as supporting evidence of station
membership. The 714-feature snapshot includes nearby unrelated building entrances
and indoor elevators. Tag presence and proximity do not establish station ownership,
public access, the correct level, or a usable pedestrian connection. Ways preserve
their actual OSM node geometry. Contributor account names and UIDs are not included.

## Candidate screening

For each WMATA research point, find the nearest feature in each of three categories:
rail entrance, elevator, and other entrance. Consider only features intersecting
the successfully retrieved station window. Compute short-range distances with a
local equirectangular projection:

- nodes: point distance;
- open ways: nearest segment;
- simple closed elevator/entrance areas: nearest boundary, or zero inside.

The thresholds are triage choices, not geographic evidence:

| Condition, evaluated in order | Screen |
| --- | --- |
| Elevator source record and elevator within 30 m | Nearby elevator candidate |
| Rail entrance within 30 m | Nearby rail entrance; elevator detail may remain unresolved |
| Rail entrance within 75 m | Farther rail candidate |
| Elevator within 30 m | Elevator geometry nearby; entrance tag unresolved |
| Other entrance within 30 m | Other entrance geometry nearby |
| None of these | Review candidate |

A failed query or absent reference location remains unchecked, never a missing
entrance. If several WMATA records select one OSM feature, all receive its reuse
count. This is an ambiguity flag, not proof of either duplication or completeness.

## Desktop review

The 14 original review candidates were compared with existing OSM paths, stairs,
entrance nodes, stop-area membership, and current WMATA vicinity maps. Five were
matched to existing entrance/elevator features. Nine have existing approach geometry
but require independent confirmation of the entrance threshold or tagging.

The five confirmed matches are Gallery Place C, Judiciary Square south, Minnesota
Avenue west tunnel access, and the north entrance and elevator at Reston Town
Center. Source descriptions and station context were more useful than nearest
distance alone. For example, Judiciary Square's closest node was an elevator,
while its matching south entrance was farther away.

The historical CSV preserves the spreadsheet's original center-based way distances.
CLI results use geometry-aware distances and may differ from that historical
snapshot. Neither output is an OSM edit file. Human outcomes live separately in
`data/reviews.json` and are not silently overwritten by a refresh.

## Limits and remaining work

Panorama positions can be on a sidewalk or road junction well away from the
entrance they depict. A 75 m threshold produced several false gaps. A nearby path
without an entrance tag may represent a real mapping opportunity, an appropriately
mapped open station approach, or the wrong physical point. Elevated and surface
stations need particular care.

Before editing, verify the actual threshold, existing node/way connections, public
access, vertical levels, and the evidence source. Use the OSM editor's permitted
imagery or independent survey. The Google-derived reference points must not be
used as upload coordinates. No automatic imports or proposed OSM changesets are
provided by this project.
