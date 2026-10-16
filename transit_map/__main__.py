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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "audit", "review-queue", "fetch-wmata", "fetch-osm"):
        command = sub.add_parser(name)
        command.add_argument("--inventory", default=str(ROOT / "data/wmata/entrances.json"))
        command.add_argument("--stations", default=str(ROOT / "data/wmata/stations.json"))
        command.add_argument("--osm", default=str(ROOT / "data/osm/features.geojson"))
        command.add_argument("--reviews", default=str(ROOT / "data/reviews.json"))
        if name != "validate":
            default = {"audit": "build/audit.json", "review-queue": "build/review-queue.md",
                       "fetch-wmata": "build/wmata.json", "fetch-osm": "build/osm.geojson"}[name]
            command.add_argument("--output", default=default)
        if name.startswith("fetch-"):
            command.add_argument("--cache", default=f"build/cache/{name}")
            command.add_argument("--refresh", action="store_true", help="Bypass cached responses")
            command.add_argument("--delay", type=float, default=0.5, help="Seconds between requests")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch-wmata":
            return fetch_wmata(args)
        if args.command == "fetch-osm":
            return fetch_osm(args)
        inventory, stations, osm, reviews = source_data(args)
        if args.command == "validate":
            print(json.dumps(validate(inventory, stations, osm, reviews), indent=2))
        elif args.command == "review-queue":
            by_id = {r["id"]: r for r in inventory}
            lines = ["# Desktop review queue", "", "Generated from materialized research records.", "",
                     "All records remain visible. Proximity does not confirm entrance identity.", "",
                     "Shared candidates require review regardless of distance or desktop status.", ""]
            for task in review_worklist(inventory, osm, reviews):
                record = by_id[task["entrance_id"]]
                reasons = "; ".join(task["review_reasons"]) or "Desktop confirmation recorded; no open task"
                lines.extend([f"## {record['id']}: {record['station']}", "",
                              record["description"], "", task["review_status"], "", reasons, "",
                              task["review_notes"], ""])
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("\n".join(lines), encoding="utf-8")
            print(str(output))
        else:
            result = audit(inventory, osm, reviews)
            write_json(args.output, result)
            print(json.dumps(result["screen_counts"], indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
