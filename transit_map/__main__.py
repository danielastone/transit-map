"""Small, dependency-free command line interface."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import audit, parse_osm, parse_wmata, review_worklist, validate

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "transit-map/0.1 (https://github.com/danielastone/transit-map; read-only research)"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def download(url, cache, refresh=False):
    cache = Path(cache)
    if cache.exists() and not refresh:
        return cache.read_bytes(), True
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=40) as response:
                content = response.read()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(content)
            return content, False
        except HTTPError as error:
            if error.code not in {429, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Download exhausted retries")


def source_data(args):
    defaults = [str(ROOT / path) for path in ("data/wmata/entrances.json", "data/wmata/stations.json", "data/osm/features.geojson", "data/reviews.json")]
    if [args.inventory, args.stations, args.osm, args.reviews] == defaults:
        from .build import materialize
        state, _ = materialize()
        return state['entrances']['records'], state['stations']['records'], state['osm'], state['reviews']['records']
    return (read_json(args.inventory)["records"], read_json(args.stations)["records"],
            read_json(args.osm), read_json(args.reviews)["records"])


def fetch_wmata(args):
    previous = read_json(args.inventory)["records"]
    stations = read_json(args.stations)["records"]
    records, failures, retrievals = [], [], []
    for station in stations:
        url = station["source_url"]
        try:
            raw, cached = download(url, Path(args.cache) / (station["name"].replace("/", "_") + ".html"), args.refresh)
            records.extend(parse_wmata(raw.decode("utf-8"), station["name"], url, previous))
            retrievals.append({"station": station["name"], "cached": cached})
        except (HTTPError, URLError, OSError, ValueError) as error:
            failures.append({"station": station["name"], "error": str(error)})
        time.sleep(args.delay)
    result = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "records": records,
              "complete": not failures, "failures": failures, "retrievals": retrievals}
    write_json(args.output, result)
    print(json.dumps({"records": len(records), "failures": len(failures), "output": args.output}))
    return 1 if failures else 0


def fetch_osm(args):
    # Read the recorded windows rather than silently changing geographic scope.
    manifest = read_json(args.osm)
    features, areas, windows = {}, {}, []
    for old_window in manifest["query_windows"]:
        south, west, north, east = old_window["bounds"]
        url = "https://api.openstreetmap.org/api/0.6/map?" + urlencode({
            "bbox": f"{west:.7f},{south:.7f},{east:.7f},{north:.7f}"})
        cache = Path(args.cache) / (old_window["station"].replace("/", "_") + ".xml")
        window = {"station": old_window["station"], "bounds": old_window["bounds"], "source_url": url}
        try:
            raw, cached = download(url, cache, args.refresh)
            found, stop_areas = parse_osm(raw)
            features.update((feature["id"], feature) for feature in found)
            areas.update((str(area["id"]), area) for area in stop_areas)
            window.update(status="ok", cached=cached)
        except (HTTPError, URLError, OSError, ValueError) as error:
            window.update(status="error", error=str(error))
        windows.append(window)
        time.sleep(args.delay)
    result = {
        "type": "FeatureCollection", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "attribution": "© OpenStreetMap contributors", "license": "ODbL-1.0",
        "license_url": "https://www.openstreetmap.org/copyright",
        "query_windows": windows,
        "features": [features[k] for k in sorted(features)],
        "stop_areas": [areas[k] for k in sorted(areas)],
    }
    write_json(args.output, result)
    failures = sum(w["status"] != "ok" for w in windows)
    print(json.dumps({"features": len(features), "failed_windows": failures, "output": args.output}))
    return 1 if failures else 0


def recover_evidence(args):
    """N4: fetch review-time OSM history for cited elements the repo does not retain."""
    from . import evidence
    inventory, _, osm, reviews = source_data(args)
    by_review = {r["entrance_id"]: r for r in reviews}
    gaps = evidence.unreproducible_citations(reviews, osm, ROOT / "docs/evidence")
    if args.review:
        gaps = {k: v for k, v in gaps.items() if k in set(args.review)}
    if not gaps:
        print(json.dumps({"unreproducible_citations": 0}))
        return 0
    cache = Path(args.cache)

    def fetch_history(element_id):
        kind, ident = element_id.split("/")
        raw, _ = download(f"{evidence.API}/{kind}/{ident}/history.json",
                          cache / f"{kind}-{ident}.json", args.refresh)
        time.sleep(args.delay)
        return json.loads(raw)["elements"]

    def fetch_bytes(url):
        raw, _ = download(url, cache / ("map-" + url.rsplit("/", 1)[-1].replace("%20", "_")), args.refresh)
        return raw

    maps = evidence.map_records([by_review[r] for r in gaps], fetch_bytes if args.maps else None)
    result = evidence.recover(gaps, by_review, {r["id"]: r for r in inventory}, fetch_history, maps)
    write_json(args.output, result)
    changed = sum(c["changed_after_review"] for c in result["live_checks"])
    print(json.dumps({"reviews": len(gaps), "elements": len(result["elements"]),
                      "changed_after_review": changed, "problems": result["problems"],
                      "output": args.output}, indent=2))
    return 1 if result["problems"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "audit", "review-queue", "fetch-wmata", "fetch-osm", "recover-evidence"):
        command = sub.add_parser(name)
        command.add_argument("--inventory", default=str(ROOT / "data/wmata/entrances.json"))
        command.add_argument("--stations", default=str(ROOT / "data/wmata/stations.json"))
        command.add_argument("--osm", default=str(ROOT / "data/osm/features.geojson"))
        command.add_argument("--reviews", default=str(ROOT / "data/reviews.json"))
        if name != "validate":
            default = {"audit": "build/audit.json", "review-queue": "build/review-queue.md",
                       "fetch-wmata": "build/wmata.json", "fetch-osm": "build/osm.geojson",
                       "recover-evidence": "build/evidence/baseline-recovery.json"}[name]
            command.add_argument("--output", default=default)
        if name == "recover-evidence":
            command.add_argument("--review", action="append", help="Limit to an entrance ID (repeatable)")
            command.add_argument("--maps", action="store_true", help="Also download cited WMATA maps and hash them")
        if name.startswith("fetch-") or name == "recover-evidence":
            command.add_argument("--cache", default=f"build/cache/{name}")
            command.add_argument("--refresh", action="store_true", help="Bypass cached responses")
            command.add_argument("--delay", type=float, default=0.5, help="Seconds between requests")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch-wmata":
            return fetch_wmata(args)
        if args.command == "fetch-osm":
            return fetch_osm(args)
        if args.command == "recover-evidence":
            return recover_evidence(args)
        inventory, stations, osm, reviews = source_data(args)
        if args.command == "validate":
            print(json.dumps(validate(inventory, stations, osm, reviews), indent=2))
        elif args.command == "review-queue":
            by_id = {r["id"]: r for r in inventory}
            lines = ["# Desktop review queue", "", "Generated from materialized research records.", "",
                     "All records remain visible. Proximity does not confirm entrance identity.", "",
                     "Shared-candidate questions require explicit accepted or rejected decisions; status questions remain open.", ""]
            for task in review_worklist(inventory, osm, reviews):
                record = by_id[task["entrance_id"]]
                reasons = "; ".join(task["review_reasons"]) or "No open review question"
                decisions = [f"- {d['decision']}: {d['feature_id']} — {d['reason']}"
                             for d in task["candidate_decisions"]]
                lines.extend([f"## {record['id']}: {record['station']}", "",
                              record["description"], "", task["review_label"], "", reasons, "",
                              *(decisions + [""] if decisions else []), task["review_notes"], ""])
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("\n".join(lines), encoding="utf-8")
            print(str(output))
        else:
            result = audit(inventory, osm, reviews)
            write_json(args.output, result)
            print(json.dumps({name: summary["counts"] for name, summary in result["summaries"].items()}, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
