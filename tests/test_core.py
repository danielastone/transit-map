import copy
import json
from pathlib import Path
import unittest

from transit_map.core import audit, geometry_distance, parse_osm, parse_wmata, validate

ROOT = Path(__file__).resolve().parents[1]


def feature(key="node/1", tags=None, lat=0.0, lon=0.0):
    return {"type": "Feature", "id": key,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"osm_type": "node", "osm_id": int(key.split("/")[1]),
                           "url": "https://www.openstreetmap.org/" + key,
                           "tags": tags or {"railway": "subway_entrance"}}}


def entrance(identity="WMATA-001"):
    return {"id": identity, "station": "Test", "description": "North", "kind": "Other entrance",
            "research_reference": {"latitude": 0.0, "longitude": 0.0, "osm_edit_source": False}}


def snapshot(features, status="ok"):
    return {"features": features, "query_windows": [
        {"station": "Test", "status": status, "bounds": [-0.01, -0.01, 0.01, 0.01]}]}


class GeometryTests(unittest.TestCase):
    def test_long_way_distance_uses_nearest_segment_not_center(self):
        geo = {"type": "LineString", "coordinates": [[0, 0], [0, 0.01]]}
        self.assertAlmostEqual(geometry_distance(0, 0.00001, geo), 1.11195, places=4)

    def test_inside_elevator_area_is_zero(self):
        geo = {"type": "Polygon", "coordinates": [[[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]]}
        self.assertEqual(geometry_distance(0, 0, geo), 0)

    def test_outside_polygon_measures_boundary(self):
        geo = {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]]}
        self.assertAlmostEqual(geometry_distance(0.0005, 0.002, geo), 111.195, places=2)


class AuditTests(unittest.TestCase):
    def test_failed_query_cannot_become_a_gap(self):
        result = audit([entrance()], snapshot([], status="error"))
        self.assertEqual(result["records"][0]["screen"], "Retrieval unavailable; unchecked")

    def test_no_tag_is_review_only_not_upload_ready(self):
        result = audit([entrance()], snapshot([]))
        self.assertTrue(result["records"][0]["screen"].startswith("Review:"))
        self.assertFalse(result["osm_upload_ready"])
        self.assertFalse(result["records"][0]["osm_upload_ready"])

    def test_multiple_references_to_one_node_are_flagged(self):
        result = audit([entrance("one"), entrance("two")], snapshot([feature()]))
        self.assertEqual([r["candidate_reuse_count"] for r in result["records"]], [2, 2])

    def test_elevator_can_remain_untagged_as_rail_entrance(self):
        record = entrance()
        record["kind"] = "Elevator"
        result = audit([record], snapshot([feature(tags={"highway": "elevator"})]))
        self.assertEqual(result["records"][0]["screen"], "Nearby elevator candidate")

    def test_remote_feature_outside_query_window_is_ignored(self):
        result = audit([entrance()], snapshot([feature(lat=1.0, lon=1.0)]))
        self.assertEqual(result["records"][0]["candidates"], {})


class ParsingTests(unittest.TestCase):
    def html(self, entries):
        chunk = json.dumps({"stationViewEntrancesCMF": entries})
        return "self.__next_f.push([1," + json.dumps(chunk) + "])"

    def test_ids_survive_source_reordering_and_blank_placeholder(self):
        entries = [{"entranceTitle": "South"}, {"entranceTitle": ""}, {"entranceTitle": "North"}]
        known = [{"id": "keep-id", "station": "Test", "description": "North"}]
        rows = parse_wmata(self.html(entries), "Test", "https://example.org", known)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["id"], "keep-id")
        reordered = parse_wmata(self.html(list(reversed(entries))), "Test", "https://example.org", known)
        self.assertEqual({r["id"] for r in rows}, {r["id"] for r in reordered})

    def test_source_schema_failure_is_not_empty_success(self):
        with self.assertRaises(ValueError):
            parse_wmata("<html>changed</html>", "Test", "https://example.org")

    def test_similar_labels_with_distinct_views_keep_their_ids(self):
        # Grosvenor has two east-side views whose labels differ only by trailing space.
        known = [{"id": "a", "station": "Test", "description": "East", "station_view_url": "view-a"},
                 {"id": "b", "station": "Test", "description": "East ", "station_view_url": "view-b"}]
        entries = [{"entranceTitle": "East ", "entranceViewUrl": "view-b"},
                   {"entranceTitle": "East", "entranceViewUrl": "view-a"}]
        rows = parse_wmata(self.html(entries), "Test", "https://example.org", known)
        self.assertEqual([r["id"] for r in rows], ["b", "a"])

    def test_new_same_label_view_does_not_steal_an_existing_id(self):
        known = [{"id": "old", "station": "Test", "description": "East", "station_view_url": "known"}]
        entries = [{"entranceTitle": "East", "entranceViewUrl": "new"},
                   {"entranceTitle": "East", "entranceViewUrl": "known"}]
        rows = parse_wmata(self.html(entries), "Test", "https://example.org", known)
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])
        self.assertEqual(rows[1]["id"], "old")

    def test_osm_way_preserves_geometry_without_contributor_account_fields(self):
        xml = b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon="1"/>
          <way id="9" version="2" user="someone" uid="123"><nd ref="1"/><nd ref="2"/>
          <tag k="highway" v="elevator"/></way></osm>'''
        features, _ = parse_osm(xml)
        self.assertEqual(features[0]["geometry"]["type"], "LineString")
        self.assertNotIn("uid", json.dumps(features))

    def test_error_page_is_not_successful_empty_osm_data(self):
        with self.assertRaisesRegex(ValueError, "not an OSM"):
            parse_osm(b"<html><body>unavailable</body></html>")


class SnapshotTests(unittest.TestCase):
    def load(self):
        read = lambda path: json.loads((ROOT / path).read_text())
        return (read("data/wmata/entrances.json")["records"], read("data/wmata/stations.json")["records"],
                read("data/osm/features.geojson"), read("data/reviews.json")["records"])

    def test_committed_snapshot_and_desktop_outcomes(self):
        result = validate(*self.load())
        expected = json.loads((ROOT / "data/snapshot.json").read_text())
        self.assertEqual(result["entrances"], expected["entrance_count"])
        self.assertEqual(result["stations"], expected["station_count"])
        self.assertEqual(result["osm_features"], expected["osm_feature_count"])
        self.assertEqual(result["review_counts"], expected["review_counts"])

    def test_unknown_review_target_is_rejected(self):
        inventory, stations, osm, reviews = self.load()
        reviews = copy.deepcopy(reviews)
        reviews[0]["entrance_id"] = "does-not-exist"
        with self.assertRaisesRegex(ValueError, "review ID"):
            validate(inventory, stations, osm, reviews)


if __name__ == "__main__":
    unittest.main()
