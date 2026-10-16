# Data sources and contribution boundaries

## WMATA descriptions and vicinity maps

Source: [WMATA Rider Tools](https://www.wmata.com/ridertools). Per-record station
URLs and Station View URLs are in `data/wmata/entrances.json`; map links used in
desktop reviews are in `data/reviews.json`. These are research references. This
repository does not assert permission to import WMATA material into OSM.

Station universe: [DC GIS Metro Station Entrances (Regional), layer 111](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_Rail_Bus_WebMercator/MapServer/111).
The GIS layer was used to discover station URLs; its 260 point records are not
treated as a verified census or bundled here as proposed edits.

## Google-derived reference positions

The latitude/longitude values under `research_reference` were parsed from Google
panorama URLs embedded in WMATA's Station View records. The same values appear
in the historical research CSV. They are not independently surveyed entrance pins.
Their `osm_edit_source` field is always `false`.

Do not use these positions, Google imagery, or Google place listings as the source
of OSM edits without appropriate permission. OSM explains this in its
[Legal FAQ](https://wiki.openstreetmap.org/wiki/Legal_FAQ) and
[copyright page](https://www.openstreetmap.org/copyright).

## OpenStreetMap

The OSM feature dataset is derived from read-only requests to
`https://api.openstreetmap.org/api/0.6/map`. Exact query URLs, source feature IDs,
versions, and edit timestamps are retained. Attribution: **© OpenStreetMap
contributors**. The OSM-derived database is available under the
[Open Database License](https://www.openstreetmap.org/copyright).

Relevant tagging guidance:

- [Subway entrance](https://wiki.openstreetmap.org/wiki/Tag:railway%3Dsubway_entrance)
- [Train station entrance](https://wiki.openstreetmap.org/wiki/Tag:railway%3Dtrain_station_entrance)
- [Pedestrian navigation and vertical connections](https://wiki.openstreetmap.org/wiki/Guidelines_for_pedestrian_navigation)

An entrance name is not necessarily the station name. A station label is not a
separate entrance. An elevator node may already supply the necessary geometry
without a standalone place listing. Inspect existing connections before editing.

The repository has no blanket license covering every source. OSM data retains
ODbL terms; other material retains its applicable source rights. No code license
has been assigned in this initial repository population.
