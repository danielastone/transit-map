"""N1/N2: explicit candidate decisions drive the worklist and review-adjusted summaries."""
from copy import deepcopy
import unittest

from transit_map.build import materialize
from transit_map.core import audit, review_worklist, validate


class CandidateDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, _ = materialize()
        s = cls.state
        cls.args = (s['entrances']['records'], s['osm'], s['reviews']['records'])
        cls.work = {r['entrance_id']: r for r in review_worklist(*cls.args)}
        cls.audit = audit(*cls.args)
        cls.rows = {r['entrance_id']: r for r in cls.audit['records']}

    def test_case1_gallery_place_a_rejects_d_and_keeps_supported_identity(self):
        a = self.rows['WMATA-082']
        self.assertEqual(a['candidate_id'], 'node/9951151070')          # raw screen unchanged
        self.assertEqual(a['candidate_decision'], 'rejected')
        self.assertEqual(a['accepted_feature_id'], 'node/324153442')
        self.assertEqual(a['review_outcome'], 'Accepted identity')
        self.assertFalse(self.work['WMATA-082']['review_required'])
        d = self.rows['WMATA-085']                                       # D keeps the same node
        self.assertEqual(d['accepted_feature_id'], 'node/9951151070')

    def test_case2_reston_south_rejects_north_but_conflict_stays_open(self):
        for rid in ('WMATA-173', 'WMATA-175'):
            w = self.work[rid]
            self.assertEqual(w['candidate_decision'], 'rejected')
            self.assertIsNone(w['accepted_feature_id'])
            self.assertEqual(w['review_outcome'], 'Screened candidate rejected; identity unresolved')
            self.assertTrue(w['review_required'])
            self.assertIn('Open review status: Source reference conflict', w['review_reasons'])
            self.assertFalse(any('Shared' in r for r in w['review_reasons']))

    def test_case3_supported_shared_candidate_closes_identity_warning(self):
        for rid in ('WMATA-052', 'WMATA-106', 'WMATA-065'):
            w = self.work[rid]
            self.assertGreater(w['candidate_reuse_count'], 1)
            self.assertEqual(w['candidate_decision'], 'accepted')
            self.assertEqual(w['review_reasons'], [])

    def test_case4_unresolved_elevator_stays_open_beside_supported_entrance(self):
        self.assertFalse(self.work['WMATA-065']['review_required'])     # general entrance closed
        elevator = self.work['WMATA-066']                               # same node, elevator record
        self.assertEqual(elevator['candidate_id'], self.work['WMATA-065']['candidate_id'])
        self.assertEqual(elevator['candidate_decision'], 'unresolved')
        self.assertTrue(elevator['review_required'])
        self.assertTrue(any('Shared' in r for r in elevator['review_reasons']))
        self.assertTrue(any('Open review status' in r for r in elevator['review_reasons']))

    def test_confirmation_alone_does_not_close_shared_warning(self):
        reviews = deepcopy(self.args[2])
        target = next(r for r in reviews if r['entrance_id'] == 'WMATA-052')
        del target['candidate_decisions']
        w = next(r for r in review_worklist(self.args[0], self.args[1], reviews) if r['entrance_id'] == 'WMATA-052')
        self.assertTrue(any('Shared' in r for r in w['review_reasons']))
        self.assertIn('Confirmation lacks an accepted candidate decision', w['review_reasons'])

    def test_summaries_are_distinct_and_reconcile(self):
        raw = self.audit['summaries']['raw_screening']['counts']
        adjusted = self.audit['summaries']['review_adjusted']
        self.assertEqual(raw, self.audit['screen_counts'])
        self.assertEqual(sum(raw.values()), 242)
        self.assertEqual(sum(adjusted['counts'].values()), 242)
        accepted = {r['entrance_id'] for r in self.rows.values() if r['accepted_feature_id']}
        self.assertEqual(adjusted['accepted_identity_records'], len(accepted))
        # Rejected candidates never count as accepted matches.
        for r in self.rows.values():
            if r['candidate_decision'] == 'rejected':
                self.assertNotEqual(r['accepted_feature_id'], r['candidate_id'])
        self.assertEqual(adjusted['accepted_identity_differs_from_screen'], 2)          # 082, 127
        self.assertEqual(adjusted['accepted_identity_without_screened_candidate'], 5)  # original 'Review' screens
        self.assertIn('not unique physical entrances', adjusted['meaning'])
        self.assertIn('does not imply that an entrance is missing', adjusted['meaning'])

    def test_materialization_rejects_missing_evidence_file(self):
        import tempfile
        import test_build
        from transit_map.build import digest, write
        with tempfile.TemporaryDirectory() as folder:
            root = test_build.BuildTests().workspace(folder)
            state, _ = materialize(root)
            old = state['reviews']['records'][0]
            record = dict(old, candidate_decisions=[{
                'feature_id': 'node/324153414', 'decision': 'unresolved',
                'reason': 'Synthetic test', 'evidence': ['docs/evidence/missing.json']}])
            write(root / 'transactions/001.json', {
                'transaction_id': 'missing-evidence-test', 'rationale': 'Regression test',
                'sources': ['https://www.wmata.com/'], 'operations': [{
                    'table': 'reviews', 'action': 'update', 'id': old['entrance_id'],
                    'before_sha256': digest(old), 'record': record}]})
            with self.assertRaisesRegex(ValueError, 'missing evidence file'):
                materialize(root)

    def test_validation_rejects_malformed_decisions(self):
        inv, osm, reviews = self.args
        base = next(r for r in reviews if r['entrance_id'] == 'WMATA-052')
        good = base['candidate_decisions'][0]
        bad_cases = {
            'bad decision': dict(good, decision='maybe'),
            'array decision': dict(good, decision=[]),
            'object decision': dict(good, decision={}),
            'hostless URL': dict(good, evidence=['https://']),
            'malformed URL': dict(good, evidence=['https://[']),
            'empty reason': dict(good, reason='  '),
            'no evidence': dict(good, evidence=[]),
            'http evidence': dict(good, evidence=['http://example.org']),
            'bad feature': dict(good, feature_id='node/abc'),
            'accepted outside snapshot': dict(good, feature_id='node/1'),
            'extra key': dict(good, confidence='high'),
        }
        for name, decision in bad_cases.items():
            with self.subTest(name):
                changed = [dict(r, candidate_decisions=[decision]) if r is base else r for r in reviews]
                with self.assertRaises(ValueError):
                    validate(inv, self.state['stations']['records'], osm, changed)
        for invalid_container in (None, [], {}, "accepted"):
            with self.subTest(container=invalid_container):
                changed = [dict(r, candidate_decisions=invalid_container) if r is base else r for r in reviews]
                with self.assertRaisesRegex(ValueError, 'nonempty list'):
                    validate(inv, self.state['stations']['records'], osm, changed)
        two_accepted = [good, dict(good, feature_id='node/324153442')]
        changed = [dict(r, candidate_decisions=two_accepted) if r is base else r for r in reviews]
        with self.assertRaisesRegex(ValueError, 'at most one accepted'):
            validate(inv, self.state['stations']['records'], osm, changed)


if __name__ == '__main__':
    unittest.main()
