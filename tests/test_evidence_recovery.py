"""N4: cited-element reproducibility ratchet and review-time recovery logic (no network)."""
import unittest

from transit_map.build import ROOT, materialize
from transit_map.evidence import (cited_elements, recover, review_cutoff,
                                  unreproducible_citations, version_at)

# Elements cited by baseline review notes that no repository file retains. This set may
# only shrink: recovered evidence removes entries; a new review must not add any.
KNOWN_UNREPRODUCIBLE = {
    "WMATA-021": ["way/305845881", "way/834810244"],
    "WMATA-022": ["way/305845881", "way/834810243"],
    "WMATA-107": ["node/6542276608", "way/305842958", "way/696658748"],
    "WMATA-108": ["node/5589300606", "way/584775752"],
    "WMATA-142": ["way/305847609"],
    "WMATA-195": ["way/1017457921"],
    "WMATA-208": ["node/3105395343", "way/305852778", "way/305852779"],
    "WMATA-209": ["node/10035031323", "way/1095734267", "way/305852778"],
    "WMATA-210": ["node/4448309368", "way/447761001", "way/447761004"],
    "WMATA-211": ["node/10243110918", "node/4448309372", "way/1119943184", "way/1201241347"],
}


def node(i, version, ts, lat, lon, visible=True, **tags):
    return {"type": "node", "id": i, "version": version, "timestamp": ts, "lat": lat, "lon": lon,
            "visible": visible, "tags": tags, "user": "someone", "uid": 42, "changeset": 1}


def way(i, version, ts, nodes, **tags):
    return {"type": "way", "id": i, "version": version, "timestamp": ts, "nodes": nodes,
            "visible": True, "tags": tags, "user": "someone", "uid": 42, "changeset": 1}


class EvidenceRecoveryTests(unittest.TestCase):
    def test_ratchet_unreproducible_citations_only_shrink(self):
        state, _ = materialize()
        gaps = unreproducible_citations(state['reviews']['records'], state['osm'], ROOT / 'docs/evidence')
        for entrance_id, ids in gaps.items():
            self.assertIn(entrance_id, KNOWN_UNREPRODUCIBLE, f'new unreproducible citation in {entrance_id}')
            self.assertLessEqual(set(ids), set(KNOWN_UNREPRODUCIBLE[entrance_id]))

    def test_cited_elements_parses_urls_and_prose(self):
        notes = 'footway 834810244 is not cited; https://www.openstreetmap.org/way/834810244 and node 6542276608'
        self.assertEqual(cited_elements(notes), ['node/6542276608', 'way/834810244'])

    def test_cutoff_is_end_of_review_day_in_washington(self):
        self.assertEqual(review_cutoff('2026-10-16').isoformat(), '2026-10-17T04:00:00+00:00')

    def test_version_at_ignores_later_edits_and_deletions(self):
        cutoff = review_cutoff('2026-10-16')
        hist = [node(1, 1, '2020-01-01T00:00:00Z', 1, 1), node(1, 2, '2026-10-17T03:59:59Z', 2, 2),
                node(1, 3, '2026-10-18T00:00:00Z', 3, 3)]
        self.assertEqual(version_at(hist, cutoff)['version'], 2)
        deleted = [node(2, 1, '2020-01-01T00:00:00Z', 1, 1),
                   node(2, 2, '2025-01-01T00:00:00Z', 1, 1, visible=False)]
        self.assertIsNone(version_at(deleted, cutoff))

    def test_recover_uses_review_time_geometry_and_strips_contributors(self):
        histories = {
            'way/10': [way(10, 1, '2020-01-01T00:00:00Z', [1, 2], highway='footway'),
                       way(10, 2, '2026-11-01T00:00:00Z', [1, 3], highway='steps')],
            'node/1': [node(1, 1, '2020-01-01T00:00:00Z', 38.9, -77.0)],
            'node/2': [node(2, 1, '2020-01-01T00:00:00Z', 38.9, -76.999),
                       node(2, 2, '2026-12-01T00:00:00Z', 39.5, -76.0)],
        }
        review = {'entrance_id': 'X', 'reviewed_on': '2026-10-16', 'notes': ''}
        entrance = {'id': 'X', 'research_reference': {'latitude': 38.9, 'longitude': -77.0}}
        doc = recover({'X': ['way/10']}, {'X': review}, {'X': entrance}, histories.__getitem__)
        (element,) = doc['elements']
        self.assertEqual(element['version'], 1)
        self.assertEqual(element['tags'], {'highway': 'footway'})
        self.assertEqual(element['coordinates'], [[-77.0, 38.9], [-76.999, 38.9]])   # node 2 v1, not v2
        self.assertTrue(doc['live_checks'][0]['changed_after_review'])
        self.assertEqual(doc['research_distances_m'][0]['distance_m'], 0.0)
        self.assertFalse(doc['research_distances_m'][0]['osm_edit_source'])
        self.assertNotIn('"user"', str(doc).replace("'", '"'))
        self.assertNotIn('uid', str(doc))
        self.assertEqual(doc['problems'], [])

    def test_recover_reports_elements_absent_at_review_time(self):
        histories = {'node/5': [node(5, 1, '2027-01-01T00:00:00Z', 1, 1)]}
        review = {'entrance_id': 'X', 'reviewed_on': '2026-10-16', 'notes': ''}
        doc = recover({'X': ['node/5']}, {'X': review}, {'X': {'id': 'X'}}, histories.__getitem__)
        self.assertEqual(doc['elements'], [])
        self.assertEqual(len(doc['problems']), 1)


if __name__ == '__main__':
    unittest.main()
