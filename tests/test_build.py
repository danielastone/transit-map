import json
from pathlib import Path
import shutil
import tempfile
import unittest

from transit_map.build import ROOT, check_site, digest, materialize, publish, write


class BuildTests(unittest.TestCase):
    def workspace(self, folder):
        root = Path(folder)
        shutil.copytree(ROOT / 'data', root / 'data')
        (root / 'transactions').mkdir()
        return root

    def test_baseline_lock_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.workspace(folder)
            path = root / 'data/reviews.json'
            value = json.loads(path.read_text())
            value['records'][0]['notes'] = 'changed'
            write(path, value)
            with self.assertRaisesRegex(ValueError, 'Frozen baseline'):
                materialize(root)

    def test_transaction_applied_and_stale_update_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.workspace(folder)
            state, _ = materialize(root)
            old = state['reviews']['records'][0]
            record = dict(old, notes=old['notes'] + ' Additional review required.')
            tx = {'transaction_id': 'test', 'rationale': 'test correction',
                  'sources': ['https://www.wmata.com/'], 'operations': [
                      {'table': 'reviews', 'action': 'update', 'id': old['entrance_id'],
                       'before_sha256': digest(old), 'record': record}]}
            write(root / 'transactions/001.json', tx)
            result, manifest = materialize(root)
            self.assertEqual(result['reviews']['records'][0], record)
            self.assertEqual(manifest['transactions'][0]['operation_count'], 1)
            tx['transaction_id'] = 'stale'
            write(root / 'transactions/002.json', tx)
            with self.assertRaisesRegex(ValueError, 'stale'):
                materialize(root)

    def test_publication_is_repeatable_and_has_all_records(self):
        state, manifest = materialize()
        self.assertEqual(materialize()[1], manifest)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.assertEqual(publish(state, manifest, first), 342)
            publish(state, manifest, second)
            for path in Path(first).rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (Path(second) / path.relative_to(first)).read_bytes())
            entrance = state['entrances']['records'][0]
            self.assertTrue((Path(first) / 'entrances' / (entrance['id'] + '.html')).is_file())
            (Path(first) / 'tasks.html').unlink()
            with self.assertRaisesRegex(ValueError, 'Broken publication link'):
                check_site(first)

    def test_data_only_extension_uses_existing_templates(self):
        from copy import deepcopy
        state, manifest = materialize()
        state = deepcopy(state)
        record = dict(state['entrances']['records'][0], id='WMATA-TEST')
        state['entrances']['records'].append(record)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(publish(state, manifest, folder), 343)
            self.assertTrue((Path(folder) / 'entrances/WMATA-TEST.html').is_file())


if __name__ == '__main__':
    unittest.main()
