"""Source parsing, geometry distances, and conservative candidate screening."""

from collections import Counter
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

RAIL_TAGS = {"subway_entrance", "train_station_entrance"}
REVIEW_STATUSES = {
    "Unreviewed", "Existing entrance confirmed", "Existing geometry needs tagging",
    "New entrance needed", "Source location needs correction",
    "Geometry present; entrance position unverified",
}
# Stored status values are immutable ledger history; outputs use labels that do not
# overstate what a review established (an elevator is not an "entrance"; a conflict
# between a source label and its reference point does not establish which is wrong).
STATUS_LABELS = {
    "Existing entrance confirmed": "Existing access feature confirmed",
    "Source location needs correction": "Source reference conflict",
}
CANDIDATE_DECISIONS = {"accepted", "rejected", "unresolved"}
FEATURE_ID = re.compile(r"(node|way|relation)/[1-9][0-9]*")
EVIDENCE_PATH = re.compile(r"docs/evidence/[A-Za-z0-9._-]+\.json")


def status_label(status):
    return STATUS_LABELS.get(status, status)


def decisions_by_feature(review):
    return {d["feature_id"]: d for d in (review or {}).get("candidate_decisions", [])}


def accepted_feature(review):
    return next((d["feature_id"] for d in (review or {}).get("candidate_decisions", [])
                 if d["decision"] == "accepted"), None)


def parse_wmata(html, station, source_url, existing=()):
    """Extract named Station View records; reuse published IDs, never row numbers."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)', html)
    decoded = "\n".join(json.loads(chunk) for chunk in chunks)
    match = re.search(r'"stationViewEntrancesCMF"\s*:\s*', decoded)
    if not match:
        raise ValueError(f"{station}: Station View structure not found")
    entries = json.JSONDecoder().raw_decode(decoded[match.end():])[0]
    known_views = {(r["station"], r["station_view_url"]): r["id"] for r in existing
                   if r.get("station_view_url")}
    known_labels = {}
    for record in existing:
        known_labels.setdefault((record["station"], record["description"]), []).append(record["id"])
    reserved_ids = {known_views.get((station, entry.get("entranceViewUrl", ""))) for entry in entries}
    records, seen, assigned_ids = [], set(), set()
    for entry in entries:
        title = entry.get("entranceTitle", "")
        if not title.strip():
            continue  # WMATA has an empty Huntington placeholder.
        view = entry.get("entranceViewUrl", "")
        source_key = view or title
        if source_key in seen:
            raise ValueError(f"{station}: duplicate entrance source {source_key!r}")
        seen.add(source_key)
        key = (station, title)
        label_ids = known_labels.get(key, [])
        label_fallback = (label_ids[0] if len(label_ids) == 1 and label_ids[0] not in reserved_ids
                          and label_ids[0] not in assigned_ids else None)
        stable_id = (known_views.get((station, view)) or label_fallback or
                     "WMATA-" + hashlib.sha256((station + "\0" + source_key).encode()).hexdigest()[:12])
        if stable_id in assigned_ids:
            raise ValueError(f"{station}: source records resolve to duplicate ID {stable_id}")
        assigned_ids.add(stable_id)
        coordinate = re.search(r"!1d(-?[\d.]+)!2d(-?[\d.]+)", view)
        record = {
            "id": stable_id, "station": station, "description": title,
            "kind": "Elevator" if "elevat" in title.lower() else "Other entrance",
            "wheelchair_flag": "Yes" if entry.get("hasWheelchair") else "Not marked",
            "source_url": source_url, "station_view_url": view,
            "research_reference": None,
        }
        if coordinate:
            lat, lon = map(float, coordinate.groups())
            record["research_reference"] = {
                "latitude": lat, "longitude": lon,
                "source": "Google panorama URL embedded on WMATA website",
                "osm_edit_source": False,
            }
        records.append(record)
    if not records:
        raise ValueError(f"{station}: no named entrance records")
    return records


def parse_osm(xml):
    """Keep tagged features and their actual OSM geometries, not way centroids."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError(f"Invalid OSM XML: {error}") from error
    if root.tag != "osm":
        raise ValueError("Response is not an OSM map document")
    nodes = {n.attrib["id"]: [float(n.attrib["lon"]), float(n.attrib["lat"])]
             for n in root.findall("node")}
    features, stop_areas = [], []
    for element in root:
        tags = {t.attrib["k"]: t.attrib["v"] for t in element.findall("tag")}
        if element.tag == "relation" and tags.get("public_transport") == "stop_area":
            stop_areas.append({
                "id": int(element.attrib["id"]), "tags": tags,
                "members": [dict(m.attrib) for m in element.findall("member")],
            })
        if element.tag not in {"node", "way"}:
            continue
        if not (tags.get("railway") in RAIL_TAGS or
                tags.get("highway") == "elevator" or "entrance" in tags):
            continue
        if element.tag == "node":
            geometry = {"type": "Point", "coordinates": nodes[element.attrib["id"]]}
        else:
            refs = [n.attrib["ref"] for n in element.findall("nd")]
            if any(ref not in nodes for ref in refs):
                raise ValueError(f"Incomplete way geometry: {element.attrib['id']}")
            points = [nodes[ref] for ref in refs]
            if len(points) < 2:
                raise ValueError("Way has fewer than two nodes")
            area = tags.get("area") == "yes" or tags.get("indoor") in {"room", "area"}
            geometry = ({"type": "Polygon", "coordinates": [points]}
                        if area and points[0] == points[-1]
                        else {"type": "LineString", "coordinates": points})
        key = f"{element.tag}/{element.attrib['id']}"
        features.append({
            "type": "Feature", "id": key, "geometry": geometry,
            "properties": {
                "osm_type": element.tag, "osm_id": int(element.attrib["id"]),
                "url": "https://www.openstreetmap.org/" + key,
                "version": int(element.attrib["version"]),
                "timestamp": element.attrib.get("timestamp", ""), "tags": tags,
            },
        })
    return features, stop_areas


def geometry_distance(lat, lon, geometry):
    """Meters to OSM geometry using a local projection, adequate for short screens.

    A way is measured to its nearest segment; a point inside an area is distance
    zero. This avoids false gaps caused by using centers of long elevator ways.
    """
    scale = 111195.0
    cosine = math.cos(math.radians(lat))
    def project(point):
        return ((point[0] - lon) * cosine * scale, (point[1] - lat) * scale)
    kind, coordinates = geometry["type"], geometry["coordinates"]
    if kind == "Point":
        return math.hypot(*project(coordinates))
    if kind not in {"LineString", "Polygon"}:
        raise ValueError(f"Unsupported geometry: {kind}")
    points = list(map(project, coordinates[0] if kind == "Polygon" else coordinates))
    if kind == "Polygon":
        inside = False
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if (y1 > 0) != (y2 > 0) and 0 < x1 + (x2 - x1) * (-y1) / (y2 - y1):
                inside = not inside
        if inside:
            return 0.0
    distances = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx, dy = x2 - x1, y2 - y1
        length_squared = dx * dx + dy * dy
        t = max(0.0, min(1.0, -(x1 * dx + y1 * dy) / length_squared)) if length_squared else 0
        distances.append(math.hypot(x1 + t * dx, y1 + t * dy))
    if not distances:
        raise ValueError("Geometry has no segments")
    return min(distances)


def audit(inventory, osm, reviews=()):
    """Return research candidates. Absence is never a confirmed missing entrance."""
    windows = {w["station"]: w for w in osm.get("query_windows", [])}
    reviewed = {r["entrance_id"]: r for r in reviews}
    rows, counts = [], Counter()
    for record in inventory:
        reference = record.get("research_reference")
        row = {"entrance_id": record["id"], "station": record["station"],
               "description": record["description"], "candidates": {},
               "osm_upload_ready": False, "review": reviewed.get(record["id"])}
        window = windows.get(record["station"])
        if window is None or window.get("status") != "ok":
            row["screen"] = "Retrieval unavailable; unchecked"
        elif not reference:
            row["screen"] = "Reference location unavailable; unchecked"
        else:
            lat, lon = reference["latitude"], reference["longitude"]
            # Features outside this successfully fetched window cannot establish coverage.
            south, west, north, east = window["bounds"]
            nearest = {}
            for feature in osm["features"]:
                geo = feature["geometry"]
                points = ([geo["coordinates"]] if geo["type"] == "Point" else
                          geo["coordinates"][0] if geo["type"] == "Polygon" else geo["coordinates"])
                if (max(p[0] for p in points) < west or min(p[0] for p in points) > east or
                    max(p[1] for p in points) < south or min(p[1] for p in points) > north):
                    continue
                tags = feature["properties"]["tags"]
                categories = []
                if tags.get("railway") in RAIL_TAGS:
                    categories.append("rail")
                if tags.get("highway") == "elevator":
                    categories.append("elevator")
                if "entrance" in tags:
                    categories.append("other")
                if not categories:
                    continue
                distance = geometry_distance(lat, lon, geo)
                for category in categories:
                    item = (distance, feature["id"], feature)
                    if category not in nearest or item[:2] < nearest[category][:2]:
                        nearest[category] = item
            row["candidates"] = {k: {"id": f["id"], "url": f["properties"]["url"],
                                              "distance_m": round(d, 1), "tags": f["properties"]["tags"]}
                                 for k, (d, _, f) in nearest.items()}
            def within(category, limit):
                return category in nearest and nearest[category][0] <= limit
            pick = None
            if record["kind"] == "Elevator" and within("elevator", 30):
                row["screen"], pick = "Nearby elevator candidate", "elevator"
            elif within("rail", 30):
                row["screen"] = ("Entrance mapped; elevator detail unresolved"
                                 if record["kind"] == "Elevator" else "Nearby mapped rail entrance")
                pick = "rail"
            elif within("rail", 75):
                row["screen"], pick = "Rail entrance farther from reference", "rail"
            elif within("elevator", 30):
                row["screen"], pick = "Elevator geometry nearby; entrance tag unresolved", "elevator"
            elif within("other", 30):
                row["screen"], pick = "Other entrance geometry nearby", "other"
            else:
                row["screen"] = "Review: no rail entrance tag within 75 m"
            if pick:
                row["candidate_id"] = nearest[pick][1]
                counts[row["candidate_id"]] += 1
        rows.append(row)
    for row in rows:
        row["candidate_reuse_count"] = counts.get(row.get("candidate_id"), 0)
        decision = decisions_by_feature(row["review"]).get(row.get("candidate_id"))
        row["candidate_decision"] = decision["decision"] if decision else None
        row["accepted_feature_id"] = accepted_feature(row["review"])
        row["review_outcome"] = review_outcome(row)
    raw = dict(Counter(r["screen"] for r in rows))
    return {"research_only": True, "osm_upload_ready": False,
            "distance_method": "nearest OSM geometry, local equirectangular projection",
            "screen_counts": raw,
            "summaries": {
                "raw_screening": {
                    "meaning": ("Unmodified automated proximity screens, retained for "
                                "reproducibility. Desktop reviews do not change these counts; "
                                "a screened candidate may since have been rejected."),
                    "counts": raw},
                "review_adjusted": review_adjusted_summary(rows)},
            "records": rows}


REVIEW_OUTCOMES = (
    "Accepted identity",
    "Screened candidate rejected; identity unresolved",
    "Reviewed; identity unresolved",
    "Unreviewed",
)


def review_outcome(row):
    """One adjudicated outcome per source record; never a physical-entrance count."""
    if not row["review"]:
        return "Unreviewed"
    if row["accepted_feature_id"]:
        return "Accepted identity"
    if row["candidate_decision"] == "rejected":
        return "Screened candidate rejected; identity unresolved"
    return "Reviewed; identity unresolved"


def review_adjusted_summary(rows):
    outcomes = Counter(r["review_outcome"] for r in rows)
    decisions = Counter(d["decision"] for r in rows
                        for d in (r["review"] or {}).get("candidate_decisions", []))
    return {
        "meaning": ("Source-record outcomes after desktop review: accepted identities, "
                    "rejected screened candidates, unresolved cases and unreviewed records. "
                    "These count WMATA source records, not unique physical entrances. "
                    "A rejected candidate is research history, excluded from accepted "
                    "totals, and does not imply that an entrance is missing."),
        "counts": {k: outcomes.get(k, 0) for k in REVIEW_OUTCOMES},
        "accepted_identity_records": outcomes.get("Accepted identity", 0),
        "rejected_screened_candidates": sum(r["candidate_decision"] == "rejected" for r in rows),
        "candidate_decisions": {k: decisions.get(k, 0) for k in sorted(CANDIDATE_DECISIONS)},
        "accepted_identity_differs_from_screen": sum(
            1 for r in rows if r["accepted_feature_id"] and r.get("candidate_id") and
            r["accepted_feature_id"] != r["candidate_id"]),
        "accepted_identity_without_screened_candidate": sum(
            1 for r in rows if r["accepted_feature_id"] and not r.get("candidate_id")),
        "review_status_labels": dict(Counter(status_label(r["review"]["status"])
                                             for r in rows if r["review"])),
    }


def review_worklist(inventory, osm, reviews):
    """Expose all records; proximity never clears the need for an identity review."""
    by_id = {r["entrance_id"]: r for r in reviews}
    work = []
    for screen in audit(inventory, osm, reviews)["records"]:
        review = by_id.get(screen["entrance_id"])
        status = review["status"] if review else "Unreviewed"
        reasons = []
        if status != "Existing entrance confirmed":
            reasons.append("Initial desktop review required" if status == "Unreviewed"
                           else "Open review status: " + status_label(status))
        elif not screen["accepted_feature_id"]:
            # A narrative confirmation alone does not record which feature was accepted.
            reasons.append("Confirmation lacks an accepted candidate decision")
        if screen["candidate_reuse_count"] > 1 and screen["candidate_decision"] not in {"accepted", "rejected"}:
            # Only an explicit decision on this record's screened candidate closes the
            # shared-candidate question; status-based questions above stay open.
            reasons.append("Shared automated candidate: record an accepted or rejected decision")
        work.append(dict(screen, review_status=status, review_label=status_label(status),
                         review_required=bool(reasons), review_reasons=reasons,
                         review_notes=review["notes"] if review else "",
                         candidate_decisions=(review or {}).get("candidate_decisions", [])))
    return sorted(work, key=lambda r: (not r["review_required"], r["entrance_id"]))


def validate(inventory, stations, osm, reviews):
    """Reject broken IDs, partial query coverage, and invalid source coordinates."""
    ids = [r["id"] for r in inventory]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate entrance IDs")
    station_names = {s["name"] for s in stations}
    if {r["station"] for r in inventory} != station_names:
        raise ValueError("Inventory/station coverage mismatch")
    keys = [(r["station"], r.get("station_view_url") or r["description"]) for r in inventory]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate station/source keys")
    normalized_labels = Counter((r["station"], r["description"].strip()) for r in inventory)
    for r in inventory:
        if not r["description"].strip():
            raise ValueError("Empty entrance placeholder")
        ref = r.get("research_reference")
        if ref:
            lat, lon = ref["latitude"], ref["longitude"]
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Invalid reference coordinates")
            if ref.get("osm_edit_source") is not False:
                raise ValueError("Panorama reference must be explicitly research-only")
    review_ids = [r["entrance_id"] for r in reviews]
    if len(review_ids) != len(set(review_ids)) or not set(review_ids) <= set(ids):
        raise ValueError("Duplicate or unknown review ID")
    if any(r["status"] not in REVIEW_STATUSES for r in reviews):
        raise ValueError("Unknown review status")
    from datetime import date
    for review in reviews:
        if not isinstance(review.get("notes"), str) or not review["notes"].strip():
            raise ValueError("Review requires nonempty notes")
        try:
            date.fromisoformat(review.get("reviewed_on", ""))
        except (TypeError, ValueError):
            raise ValueError("Review requires ISO reviewed_on date") from None
        validate_candidate_decisions(review, osm)
    feature_ids = [f["id"] for f in osm["features"]]
    if len(feature_ids) != len(set(feature_ids)):
        raise ValueError("Duplicate OSM feature IDs")
    windows = osm.get("query_windows", [])
    if len(windows) != len(stations) or {w["station"] for w in windows} != station_names:
        raise ValueError("OSM query coverage mismatch")
    if any(w.get("status") != "ok" for w in windows):
        raise ValueError("OSM snapshot contains failed query windows")
    for f in osm["features"]:
        if f["id"] != f"{f['properties']['osm_type']}/{f['properties']['osm_id']}":
            raise ValueError("OSM identity mismatch")
        geometry_distance(0, 0, f["geometry"])
    return {"stations": len(stations), "entrances": len(inventory),
            "osm_features": len(feature_ids), "desktop_reviews": len(reviews),
            "review_counts": dict(Counter(r["status"] for r in reviews)),
            "ambiguous_source_labels": sum(count > 1 for count in normalized_labels.values())}


def validate_candidate_decisions(review, osm):
    """Decisions name one OSM feature each, give a reason, and cite reviewable evidence."""
    if "candidate_decisions" not in review:
        return
    decisions = review["candidate_decisions"]
    rid = review["entrance_id"]
    if not isinstance(decisions, list) or not decisions:
        raise ValueError(f"{rid}: candidate_decisions must be a nonempty list when present")
    features = {f["id"] for f in osm["features"]}
    seen = set()
    for d in decisions:
        if not isinstance(d, dict) or set(d) != {"feature_id", "decision", "reason", "evidence"}:
            raise ValueError(f"{rid}: decision needs exactly feature_id, decision, reason, evidence")
        if not isinstance(d["feature_id"], str) or not FEATURE_ID.fullmatch(d["feature_id"]):
            raise ValueError(f"{rid}: invalid decision feature_id")
        if d["feature_id"] in seen:
            raise ValueError(f"{rid}: duplicate decision for {d['feature_id']}")
        seen.add(d["feature_id"])
        if not isinstance(d["decision"], str) or d["decision"] not in CANDIDATE_DECISIONS:
            raise ValueError(f"{rid}: unknown candidate decision")
        if not isinstance(d["reason"], str) or not d["reason"].strip():
            raise ValueError(f"{rid}: decision requires a reason")
        def valid_evidence(item):
            if not isinstance(item, str):
                return False
            if EVIDENCE_PATH.fullmatch(item):
                return True
            try:
                parsed = urlsplit(item)
                return parsed.scheme == "https" and bool(parsed.hostname)
            except ValueError:
                return False
        evidence = d["evidence"]
        if (not isinstance(evidence, list) or not evidence or
                any(not valid_evidence(e) for e in evidence)):
            raise ValueError(f"{rid}: decision evidence must be HTTPS URLs or docs/evidence JSON paths")
        if d["decision"] == "accepted" and d["feature_id"] not in features:
            # An accepted identity must be reproducible from the recorded snapshot.
            raise ValueError(f"{rid}: accepted feature {d['feature_id']} is not in the OSM snapshot")
    if sum(d["decision"] == "accepted" for d in decisions) > 1:
        raise ValueError(f"{rid}: at most one accepted identity per source record")
