"""Recover reproducible evidence for OSM elements cited in review notes (N4).

Review notes cite ways and nodes that the frozen snapshot does not retain (it keeps
only entrance/elevator-tagged features). This module finds those citations and,
with network access, retrieves each element's *version as of the review date* from
OSM history, so the evidence describes what the reviewer could have seen, not
whatever the element looks like later. Contributor names and UIDs are discarded.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import geometry_distance

ELEMENT_REF = re.compile(r"\b(node|way|relation)/([1-9][0-9]*)\b")
PROSE_REF = re.compile(
    r"\b(nodes?|junctions?|ways?|footways?|footbridges?|steps|approaches|approach|buildings?)\s+"
    r"([1-9][0-9]{4,}(?:(?:\s*[/,]\s*|\s+and\s+)[1-9][0-9]{4,})*)\b", re.IGNORECASE)
API = "https://api.openstreetmap.org/api/0.6"
WMATA_MAP = re.compile(r"https://www\.wmata\.com/content/dam/wmata-com/maps/[^\s;]+?\.pdf")


def cited_elements(notes):
    found = {f"{kind}/{ident}" for kind, ident in ELEMENT_REF.findall(notes)}
    for label, numbers in PROSE_REF.findall(notes):
        kind = "node" if label.lower().startswith(("node", "junction")) else "way"
        found.update(f"{kind}/{ident}" for ident in re.findall(r"[0-9]+", numbers))
    return sorted(found)


def reproducible_ids(osm, evidence_dir):
    """Element IDs whose data the repository itself retains."""
    known = {f["id"] for f in osm["features"]}
    known |= {f"relation/{area['id']}" for area in osm.get("stop_areas", [])}
    for path in sorted(Path(evidence_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        # Older extracts use "osm_elements"; both list retained element records.
        for key in ("elements", "osm_elements"):
            for e in data.get(key, []):
                if not isinstance(e, dict) or not isinstance(e.get("id"), str):
                    continue
                coords = e.get("coordinates")
                if e["id"].startswith("relation/"):
                    complete = isinstance(e.get("members"), list) or isinstance(e.get("entrance_members"), list)
                elif e["id"].startswith("node/"):
                    complete = isinstance(coords, list) and len(coords) == 2
                else:
                    complete = (isinstance(coords, list) and len(coords) >= 2 and
                                len(coords) == len(e.get("node_refs", coords)))
                if complete:
                    known.add(e["id"])
    return known


def unreproducible_citations(reviews, osm, evidence_dir):
    """{entrance_id: [element ids cited in notes but not retained anywhere in the repo]}."""
    known = reproducible_ids(osm, evidence_dir)
    gaps = {}
    for review in reviews:
        missing = [e for e in cited_elements(review["notes"]) if e not in known]
        if missing:
            gaps[review["entrance_id"]] = missing
    return gaps


def review_cutoff(reviewed_on):
    """Exclusive next-midnight boundary in Washington, respecting daylight saving."""
    next_day = date.fromisoformat(reviewed_on) + timedelta(days=1)
    return datetime.combine(next_day, datetime.min.time(), ZoneInfo("America/New_York")).astimezone(timezone.utc)


def version_at(history, cutoff):
    """Latest visible version with timestamp < cutoff, else None."""
    eligible = [v for v in history
                if datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00")) < cutoff]
    if not eligible:
        return None
    chosen = max(eligible, key=lambda v: v["version"])
    return chosen if chosen.get("visible", True) else None


def clean(version):
    """Keep identity, version, time, tags and geometry references; drop contributor data."""
    out = {"version": version["version"], "timestamp": version["timestamp"],
           "tags": version.get("tags", {})}
    if version["type"] == "node":
        out["coordinates"] = [version["lon"], version["lat"]]
    elif version["type"] == "way":
        out["node_refs"] = [f"node/{n}" for n in version["nodes"]]
    else:
        out["members"] = [{"type": m["type"], "ref": m["ref"], "role": m.get("role", "")}
                          for m in version.get("members", [])]
    return out


def recover(gaps, reviews_by_id, inventory_by_id, fetch_history, maps=None, observed_at=None, fetch_nodes=None):
    """Build one evidence document. `fetch_history(element_id)` returns OSM history
    elements (as in /history.json). Injected so tests never touch the network."""
    reviewed_on = sorted({reviews_by_id[r]["reviewed_on"] for r in gaps})
    if len(reviewed_on) != 1:
        raise ValueError("Recover one review date per evidence document")
    observed_at = observed_at or datetime.now(timezone.utc)
    day_end = review_cutoff(reviewed_on[0])
    cutoff = min(day_end, observed_at)

    cache, elements, checks, problems = {}, {}, [], []
    dependencies, latest_proven = {}, set()

    def history(element_id):
        if element_id not in cache:
            cache[element_id] = fetch_history(element_id)
        return cache[element_id]

    def node_coordinates(node_id):
        version = version_at(history(node_id), cutoff)
        if version is None:
            raise LookupError(f"{node_id} has no visible version at the review cutoff")
        current = max(history(node_id), key=lambda v: v["version"])
        dependencies[node_id] = {
            "id": node_id, "version": version["version"], "timestamp": version["timestamp"],
            "coordinates": [version["lon"], version["lat"]],
            "version_source": "latest_before_cutoff" if node_id in latest_proven else "history",
            "changed_after_cutoff": current["version"] != version["version"],
        }
        return [version["lon"], version["lat"]]

    element_ids = sorted({e for ids in gaps.values() for e in ids})
    # Fetch the parent histories first. Most referenced nodes have not changed
    # since the cutoff: a batched latest version can prove their historical state.
    # Later edits and deleted/unreturned nodes still require full history.
    if fetch_nodes:
        needed_nodes = set()
        for element_id in element_ids:
            chosen = version_at(history(element_id), cutoff)
            if chosen and chosen["type"] == "way":
                needed_nodes.update(f"node/{n}" for n in chosen["nodes"])
        for current in fetch_nodes(sorted(needed_nodes)):
            node_id = f"node/{current['id']}"
            if current.get("visible", True) and datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00")) < cutoff:
                if node_id not in cache:
                    cache[node_id] = [current]
                    latest_proven.add(node_id)

    for element_id in element_ids:
        hist = history(element_id)
        at_review = version_at(hist, cutoff)
        current = max(hist, key=lambda v: v["version"])
        if at_review is None:
            problems.append(f"{element_id}: no visible version at the review cutoff")
            continue
        record = {"id": element_id, **clean(at_review)}
        if element_id.startswith("way/"):
            try:
                record["coordinates"] = [node_coordinates(n) for n in record["node_refs"]]
            except LookupError as error:
                problems.append(str(error))
        elements[element_id] = record
        checks.append({"id": element_id, "review_time_version": at_review["version"],
                       "current_version": current["version"],
                       "current_visible": current.get("visible", True),
                       "changed_after_review": current["version"] != at_review["version"]})

    distances = []
    for entrance_id, ids in sorted(gaps.items()):
        reference = inventory_by_id[entrance_id].get("research_reference")
        for element_id in ids:
            record = elements.get(element_id)
            if not reference or not record or "coordinates" not in record:
                continue
            coords = record["coordinates"]
            geometry = ({"type": "Point", "coordinates": coords} if element_id.startswith("node/")
                        else {"type": "LineString", "coordinates": coords})
            distances.append({"entrance_id": entrance_id, "element": element_id, "osm_edit_source": False,
                              "distance_m": round(geometry_distance(reference["latitude"],
                                                                    reference["longitude"], geometry), 1)})
    return {
        "reviewed_on": reviewed_on[0],
        "attribution": "© OpenStreetMap contributors", "license": "ODbL-1.0",
        "license_url": "https://www.openstreetmap.org/copyright",
        "scope": ("Retrospective recovery of OSM elements cited in desktop review notes. "
                  "Each element is its OSM history version as of the end of the review day "
                  "(America/New_York), capped at recovery start if that day is still in progress; "
                  "way node coordinates are resolved at the same exclusive cutoff. "
                  "This reproduces cited geometry; it does not re-review or strengthen the outcomes. "
                  "Contributor names and UIDs omitted."),
        "review_day_end_utc": day_end.isoformat().replace("+00:00", "Z"),
        "recovery_started_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "review_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
        "cited_by": {k: v for k, v in sorted(gaps.items())},
        "maps": maps or [],
        "elements": [elements[k] for k in sorted(elements)],
        "live_checks": checks,
        "node_dependencies": [dependencies[k] for k in sorted(dependencies)],
        "research_distances_m": distances,
        "problems": problems,
    }


def map_records(reviews, fetch_bytes=None):
    """WMATA vicinity maps cited by the reviews. Edition needs visual inspection, so it
    is left null; the hash pins the file actually retrieved."""
    urls = sorted({u for r in reviews for u in WMATA_MAP.findall(r["notes"])})
    out = []
    for url in urls:
        entry = {"url": url, "edition": None, "sha256": None}
        if fetch_bytes:
            entry["sha256"] = hashlib.sha256(fetch_bytes(url)).hexdigest()
        out.append(entry)
    return out
