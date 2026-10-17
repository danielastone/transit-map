"""Deterministic baseline + transaction materialization and static publication."""
import argparse
from copy import deepcopy
import hashlib
from html import escape
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from .core import audit, review_worklist, status_label, validate

ROOT = Path(__file__).resolve().parents[1]
FILES = {'entrances': 'data/wmata/entrances.json', 'stations': 'data/wmata/stations.json',
         'osm': 'data/osm/features.geojson', 'reviews': 'data/reviews.json'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def materialize(root=ROOT):
    root = Path(root)
    state = {name: read(root / path) for name, path in FILES.items()}
    hashes = {name: digest(value) for name, value in state.items()}
    if hashes != read(root / 'data/baseline-lock.json'):
        raise ValueError('Frozen baseline changed; use an append-only transaction')
    manifest = {'baseline_sha256': hashes, 'transactions': []}
    seen = set()
    for path in sorted((root / 'transactions').glob('*.json')):
        tx = read(path)
        if not tx.get('transaction_id') or tx['transaction_id'] in seen:
            raise ValueError('Missing or duplicate transaction ID')
        if not tx.get('rationale') or not tx.get('sources') or not tx.get('operations'):
            raise ValueError('Transaction requires rationale, sources and operations')
        if not isinstance(tx['sources'], list) or any(not isinstance(url, str) or urlsplit(url).scheme != 'https' or not urlsplit(url).netloc for url in tx['sources']):
            raise ValueError('Transaction sources must be HTTPS URLs')
        seen.add(tx['transaction_id'])
        before = digest(state)
        for op in tx['operations']:
            table = op['table']
            if table not in {'entrances', 'stations', 'reviews'}:
                raise ValueError('Unsupported transaction table')
            key = {'entrances': 'id', 'stations': 'name', 'reviews': 'entrance_id'}[table]
            rows = state[table]['records']
            existing = next((r for r in rows if r[key] == op['id']), None)
            action = op['action']
            if action == 'add':
                if existing is not None or op['record'][key] != op['id']:
                    raise ValueError('Duplicate or mismatched add')
                rows.append(deepcopy(op['record']))
            elif action in {'update', 'delete'}:
                if existing is None or op.get('before_sha256') != digest(existing):
                    raise ValueError('Missing record or stale before_sha256')
                if action == 'update' and op['record'][key] != op['id']:
                    raise ValueError('Record identity cannot change')
                index = rows.index(existing)
                if action == 'delete':
                    rows.pop(index)
                else:
                    rows[index] = deepcopy(op['record'])
            else:
                raise ValueError('Unsupported operation')
        validate(state['entrances']['records'], state['stations']['records'], state['osm'], state['reviews']['records'])
        manifest['transactions'].append({'file': path.name, 'transaction_id': tx['transaction_id'],
            'transaction_sha256': digest(tx), 'before_sha256': before, 'after_sha256': digest(state),
            'operation_count': len(tx['operations'])})
    validate(state['entrances']['records'], state['stations']['records'], state['osm'], state['reviews']['records'])
    for review in state['reviews']['records']:
        for decision in review.get('candidate_decisions', []):
            for item in decision['evidence']:
                if not item.startswith('https://') and not (root / item).is_file():
                    raise ValueError(f"{review['entrance_id']}: missing evidence file {item}")
    manifest['final_sha256'] = digest(state)
    return state, manifest


def publish(state, manifest, output):
    """One publication model, semantic HTML, relative routes, no client-side joins."""
    output = Path(output)
    entrances = sorted(state['entrances']['records'], key=lambda r: r['id'])
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', r['id']) for r in entrances):
        raise ValueError('Entrance ID is not safe for a stable route')
    reviews = {r['entrance_id']: r for r in state['reviews']['records']}
    model = audit(entrances, state['osm'], list(reviews.values()))
    model['provenance_sha256'] = manifest['final_sha256']
    write(output / 'data/audit.json', model)
    write(output / 'data/semantic-manifest.json', manifest)
    pages = {}
    def page(title, body, prefix=''):
        return ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{escape(title)} · Transit Map</title><link rel="stylesheet" href="{prefix}style.css">'
                f'<header><a href="{prefix}index.html">Transit Map</a></header><main><h1>{escape(title)}</h1>{body}</main>'
                '<footer>Research snapshot · © OpenStreetMap contributors · '
                '<a href="https://www.openstreetmap.org/copyright">ODbL</a></footer></html>')
    def link(url, label):
        if urlsplit(url).scheme != 'https':
            raise ValueError('Source links must use HTTPS')
        return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'
    station_links = []
    for station in sorted(state['stations']['records'], key=lambda r: r['name']):
        # Hash-derived routes remain stable when station ordering changes.
        route = 'stations/' + digest(station['name'])[:16] + '.html'
        records = [r for r in entrances if r['station'] == station['name']]
        station_links.append(f'<li><a href="{route}">{escape(station["name"])}</a> ({len(records)})</li>')
        listing = ''.join(f'<li><a href="../entrances/{r["id"]}.html">{escape(r["description"])}</a></li>' for r in records)
        pages[route] = page(station['name'], link(station['source_url'], 'WMATA station source') + '<ul>' + listing + '</ul>', '../')
    worklist = review_worklist(entrances, state["osm"], list(reviews.values()))
    write(output / "data/review-queue.json", {"records": worklist})
    tasks = []
    for record in entrances:
        review = reviews.get(record['id'])
        status = status_label(review['status']) if review else 'No desktop review recorded'
        body = f'<p>{escape(record["station"])}</p><p>{escape(record["description"])}</p><h2>Desktop review</h2><p>{escape(status)}</p>'
        if review:
            body += f'<p>{escape(review["notes"])}</p>'
            decisions = review.get('candidate_decisions', [])
            if decisions:
                body += ('<h2>Candidate decisions</h2><p>Rejected candidates remain as research history; '
                         'a rejection does not mean an entrance is missing.</p><table><thead><tr>'
                         '<th>OSM feature</th><th>Decision</th><th>Reason</th><th>Evidence</th></tr></thead><tbody>')
                for d in decisions:
                    evidence = ' '.join(link(e, 'source') if e.startswith('https://') else f'<code>{escape(e)}</code>'
                                        for e in d['evidence'])
                    body += (f'<tr><td>{link("https://www.openstreetmap.org/" + d["feature_id"], d["feature_id"])}</td>'
                             f'<td>{escape(d["decision"])}</td><td>{escape(d["reason"])}</td><td>{evidence}</td></tr>')
                body += '</tbody></table>'
        body += '<h2>Provenance</h2>' + link(record['source_url'], 'WMATA source')
        body += '<p>Source panorama coordinates are research references only; they are not an OSM edit source. Automated distance screening does not establish a missing entrance. No record is approved for OSM upload.</p>'
        pages[f'entrances/{record["id"]}.html'] = page(record['id'], body, '../')
    for task in worklist:
        reasons = '; '.join(task['review_reasons']) or 'Desktop confirmation recorded; no open task'
        tasks.append(f'<li data-entrance-id="{escape(task["entrance_id"], quote=True)}" data-review-status="{escape(task["review_status"], quote=True)}"><a href="entrances/{escape(task["entrance_id"], quote=True)}.html">{escape(task["entrance_id"])}</a>: {escape(task["review_label"])} — {escape(reasons)}</li>')
    pages['index.html'] = page('WMATA entrance research',
        f'<p>{len(entrances)} source entrance records across {len(station_links)} stations; {len(reviews)} desktop reviews.</p>'
        '<p>This is a research inventory, not a live service or accessibility guide.</p>'
        '<p><a href="tasks.html">Research tasks</a> · <a href="data/audit.json">Automated screening JSON</a> · '
        '<a href="data/semantic-manifest.json">Build provenance</a></p>' + summary_tables(model['summaries']) +
        '<h2>Stations</h2><ul>' + ''.join(station_links) + '</ul>')
    pages['tasks.html'] = page('Research tasks', '<p>All source records are listed. Shared-candidate questions close only through explicit accepted or rejected decisions; other review questions remain open. Proximity is not a confirmed match.</p><p><a href="data/review-queue.json">Review queue JSON</a></p><ul>' + ''.join(tasks) + '</ul>')
    for path, html in pages.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding='utf-8')
    (output / 'style.css').write_text('body{font:1rem/1.6 system-ui,sans-serif;max-width:72rem;margin:auto;padding:1.5rem;color:#172b35;background:#fafcfb}a{color:#006b70}main{min-height:70vh}li{margin:.4rem 0}table{border-collapse:collapse;margin:1rem 0}caption{text-align:left;font-weight:600}th,td{border:1px solid #ccd6d6;padding:.3rem .6rem;text-align:left;vertical-align:top}header,footer{padding:1rem 0;border-bottom:1px solid #ccd6d6}p{max-width:80ch}', encoding='utf-8')
    check_site(output)
    return len(pages)


def summary_tables(summaries):
    """Two distinct summaries: raw screens for reproducibility, review-adjusted outcomes."""
    def table(caption, counts):
        rows = ''.join(f'<tr><th scope="row">{escape(k)}</th><td>{v}</td></tr>' for k, v in counts.items())
        return f'<table><caption>{escape(caption)}</caption><tbody>{rows}</tbody></table>'
    raw, adjusted = summaries['raw_screening'], summaries['review_adjusted']
    return ('<h2>Raw screening counts</h2>' + f'<p>{escape(raw["meaning"])}</p>' +
            table('Automated proximity screens (source records)', raw['counts']) +
            '<h2>Review-adjusted outcomes</h2>' + f'<p>{escape(adjusted["meaning"])}</p>' +
            table('Outcome per source record', adjusted['counts']) +
            table('Candidate decisions', {'Rejected screened candidates': adjusted['rejected_screened_candidates'],
                                          'Accepted identity overrules a different screened candidate':
                                              adjusted['accepted_identity_differs_from_screen'],
                                          'Accepted identity where the screen selected no candidate':
                                              adjusted['accepted_identity_without_screened_candidate'],
                                          **{f'Decisions recorded: {k}': v for k, v in adjusted['candidate_decisions'].items()}}))


def check_site(output):
    from html.parser import HTMLParser
    output = Path(output).resolve()
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in {'href', 'src'} and value:
                    self.links.append(value)
    for path in output.rglob('*.html'):
        parser = Links()
        parser.links = []
        parser.feed(path.read_text(encoding='utf-8'))
        for url in parser.links:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme != 'https':
                    raise ValueError('Unsafe published link')
                continue
            target = (path.parent / parsed.path).resolve()
            if not target.is_relative_to(output) or not target.is_file():
                raise ValueError(f'Broken publication link: {path}: {url}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='build')
    args = parser.parse_args()
    state, manifest = materialize()
    output = Path(args.output)
    for name, value in state.items():
        write(output / 'data' / f'{name}.json', value)
    write(output / 'audit/semantic-manifest.json', manifest)
    if (output / 'site').exists():
        shutil.rmtree(output / 'site')
    print(json.dumps({'pages': publish(state, manifest, output / 'site'), 'final_sha256': manifest['final_sha256']}))


if __name__ == '__main__':
    main()
