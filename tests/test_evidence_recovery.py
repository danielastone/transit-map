"""N4: cited-element reproducibility ratchet and review-time recovery logic (no network)."""
import unittest

from transit_map.build import ROOT, materialize
from transit_map.evidence import (cited_elements, recover, review_cutoff,
                                  reproducible_ids, unreproducible_citations, version_at)

# Elements cited by baseline review notes that no repository file retains. This set may
# only shrink: recovered evidence removes entries; a new review must not add any.
KNOWN_UNREPRODUCIBLE = {}


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
        notes = 'footway 834810244; https://www.openstreetmap.org/way/834810244 and node 6542276608'
        self.assertEqual(cited_elements(notes), ['node/6542276608', 'way/834810244'])

    def test_citations_include_prose_aliases_and_lists(self):
        self.assertEqual(cited_elements('Footways 447761002/447761004/447761005; '
                                        'junction 7792548646; nodes 9384597573/9384597574; steps 305852780'),
                         ['node/7792548646', 'node/9384597573', 'node/9384597574',
                          'way/305852780', 'way/447761002', 'way/447761004', 'way/447761005'])

    def test_cutoff_is_end_of_review_day_in_washington(self):
        self.assertEqual(review_cutoff('2026-10-16').isoformat(), '2026-10-17T04:00:00+00:00')

    def test_cutoff_respects_winter_and_excludes_next_day(self):
        self.assertEqual(review_cutoff('2026-12-01').isoformat(), '2026-12-02T05:00:00+00:00')
        cutoff = review_cutoff('2026-10-16')
        self.assertIsNone(version_at([node(1, 1, '2026-10-17T04:00:00Z', 1, 1)], cutoff))

    def test_today_recovery_does_not_claim_future_end_of_day(self):
        from datetime import datetime, timezone
        observed = datetime(2026, 10, 17, 1, tzinfo=timezone.utc)
        histories = {'node/5': [node(5, 1, '2020-01-01T00:00:00Z', 1, 1),
                                node(5, 2, '2026-10-17T02:00:00Z', 2, 2)]}
        review = {'entrance_id': 'X', 'reviewed_on': '2026-10-16', 'notes': ''}
        doc = recover({'X': ['node/5']}, {'X': review}, {'X': {'id': 'X'}},
                      histories.__getitem__, observed_at=observed)
        self.assertEqual(doc['review_cutoff_utc'], '2026-10-17T01:00:00Z')
        self.assertEqual(doc['elements'][0]['version'], 1)

    def test_partial_way_does_not_close_reproducibility_gap(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'partial.json'
            path.write_text(json.dumps({'elements': [{'id': 'way/12345', 'node_refs': ['node/1', 'node/2']}]}))
            self.assertNotIn('way/12345', reproducible_ids({'features': []}, folder))
            path.write_text(json.dumps({'elements': [{'id': 'way/12345', 'node_refs': ['node/1', 'node/2'],
                                                     'coordinates': [[1, 2], [3, 4]]}]}))
            self.assertIn('way/12345', reproducible_ids({'features': []}, folder))

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

    def test_batch_latest_nodes_prove_unchanged_versions_and_fall_back_for_later_edits(self):
        from datetime import datetime, timezone
        histories = {
            'way/10': [way(10, 1, '2020-01-01T00:00:00Z', [1, 2])],
            'node/2': [node(2, 1, '2020-01-01T00:00:00Z', 1, 2),
                       node(2, 2, '2027-01-01T00:00:00Z', 8, 9)]}
        asked = []
        def fetch(key):
            asked.append(key)
            return histories[key]
        def batch(ids):
            self.assertEqual(ids, ['node/1', 'node/2'])
            return [node(1, 1, '2020-01-01T00:00:00Z', 1, 1), histories['node/2'][-1]]
        review = {'entrance_id': 'X', 'reviewed_on': '2026-10-16', 'notes': ''}
        doc = recover({'X': ['way/10']}, {'X': review}, {'X': {'id': 'X'}}, fetch,
                      observed_at=datetime(2026, 10, 18, tzinfo=timezone.utc), fetch_nodes=batch)
        self.assertEqual(asked, ['way/10', 'node/2'])
        self.assertEqual(doc['elements'][0]['coordinates'], [[1, 1], [2, 1]])
        self.assertEqual(doc['node_dependencies'][0]['version_source'], 'latest_before_cutoff')
        self.assertTrue(doc['node_dependencies'][1]['changed_after_cutoff'])

    def test_recover_reports_elements_absent_at_review_time(self):
        histories = {'node/5': [node(5, 1, '2027-01-01T00:00:00Z', 1, 1)]}
        review = {'entrance_id': 'X', 'reviewed_on': '2026-10-16', 'notes': ''}
        doc = recover({'X': ['node/5']}, {'X': review}, {'X': {'id': 'X'}}, histories.__getitem__)
        self.assertEqual(doc['elements'], [])
        self.assertEqual(len(doc['problems']), 1)


if __name__ == '__main__':
    unittest.main()
