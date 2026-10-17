"""Executable regressions for the ceff5f4 red-team pass."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest

import test_build
from transit_map.__main__ import main as cli
from transit_map.build import FILES, digest, materialize, publish, write
from transit_map.core import REVIEW_STATUSES, review_worklist, status_label


class RedTeamTests(unittest.TestCase):
    def setup_transaction(self, folder, operations):
        root = test_build.BuildTests().workspace(folder)
        write(root / 'transactions/001.json', {'transaction_id': 'synthetic-test',
              'rationale': 'Synthetic regression only, not a research observation',
              'sources': ['https://www.wmata.com/'], 'operations': operations})
        return root

    def new_review(self):
        state, _ = materialize()
        reviewed = {r['entrance_id'] for r in state['reviews']['records']}
        record = next(r for r in state['entrances']['records'] if r['id'] not in reviewed)
        return {'entrance_id': record['id'], 'reviewed_on': '2026-10-16',
                'status': 'New entrance needed', 'notes': 'Synthetic regression evidence only'}

    def test_every_allowed_status_survives_transaction_and_both_outputs(self):
        for status in sorted(REVIEW_STATUSES):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                review = dict(self.new_review(), status=status)
                root = self.setup_transaction(folder, [{'table': 'reviews', 'action': 'add',
                    'id': review['entrance_id'], 'record': review}])
                state, manifest = materialize(root)
                publish(state, manifest, root / 'site')
                tasks = (root / 'site/tasks.html').read_text()
                self.assertIn('data-entrance-id="' + review['entrance_id'] + '"', tasks)
                self.assertIn(status, tasks)
                for name, path in FILES.items():
                    write(root / path, state[name])
                args = ['review-queue', '--output', str(root / 'queue.md')]
                for flag, name in [('inventory', 'entrances'), ('stations', 'stations'), ('osm', 'osm'), ('reviews', 'reviews')]:
                    args.extend(['--' + flag, str(root / FILES[name])])
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(cli(args), 0)
                section = (root / 'queue.md').read_text().split('## ' + review['entrance_id'] + ':')[1].split('\n## ')[0]
                self.assertIn(status_label(status), section)

    def test_missing_empty_or_nontext_notes_rejected_during_materialization(self):
        for notes in [None, '', ' ', 123]:
            with self.subTest(notes=notes), tempfile.TemporaryDirectory() as folder:
                review = self.new_review()
                if notes is None:
                    del review['notes']
                else:
                    review['notes'] = notes
                root = self.setup_transaction(folder, [{'table': 'reviews', 'action': 'add',
                    'id': review['entrance_id'], 'record': review}])
                with self.assertRaisesRegex(ValueError, 'nonempty notes'):
                    materialize(root)

    def test_station_metadata_update_works_and_new_station_requires_snapshot_migration(self):
        state, _ = materialize()
        old = state['stations']['records'][0]
        with tempfile.TemporaryDirectory() as folder:
            root = self.setup_transaction(folder, [{'table': 'stations', 'action': 'update',
                'id': old['name'], 'before_sha256': digest(old),
                'record': dict(old, source_url='https://www.wmata.com/')}])
            result, manifest = materialize(root)
            self.assertEqual(result['stations']['records'][0]['source_url'], 'https://www.wmata.com/')
            publish(result, manifest, root / 'site')
        with tempfile.TemporaryDirectory() as folder:
            record = dict(state['entrances']['records'][0], id='WMATA-TEST', station='SYNTHETIC')
            root = self.setup_transaction(folder, [
                {'table': 'stations', 'action': 'add', 'id': 'SYNTHETIC',
                 'record': {'name': 'SYNTHETIC', 'source_url': 'https://www.wmata.com/'}},
                {'table': 'entrances', 'action': 'add', 'id': record['id'], 'record': record}])
            with self.assertRaisesRegex(ValueError, 'OSM query coverage mismatch'):
                materialize(root)

    def test_all_records_visible_and_reuse_requires_review_even_when_confirmed(self):
        state, _ = materialize()
        inventory, osm, reviews = state['entrances']['records'], state['osm'], state['reviews']['records']
        work = review_worklist(inventory, osm, reviews)
        self.assertEqual({r['entrance_id'] for r in work}, {r['id'] for r in inventory})
        reused = [r for r in work if r['candidate_reuse_count'] > 1]
        self.assertEqual(len(reused), 31)
        # Only an explicit accepted/rejected decision on the screened candidate closes the warning.
        for r in reused:
            shared_open = any('Shared' in reason for reason in r['review_reasons'])
            self.assertEqual(shared_open, r['candidate_decision'] not in {'accepted', 'rejected'})
        review = {'entrance_id': reused[0]['entrance_id'], 'status': 'Existing entrance confirmed',
                  'reviewed_on': '2026-10-16', 'notes': 'Synthetic test'}
        updated = [r for r in deepcopy(reviews) if r['entrance_id'] != review['entrance_id']] + [review]
        task = next(r for r in review_worklist(inventory, osm, updated) if r['entrance_id'] == review['entrance_id'])
        self.assertTrue(task['review_required'])
        self.assertTrue(any('Shared' in reason for reason in task['review_reasons']))
