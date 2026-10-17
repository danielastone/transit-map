# Append-only research transactions

The existing source files are the adoption baseline, not reconstructed historical transactions. Never edit merged baseline files or merged transaction JSON. Add a new, lexically ordered JSON file to correct an earlier assertion. Work on a feature branch, open a PR, pass CI, then squash merge.

Each transaction has a unique `transaction_id`, nonempty `rationale`, `sources` (reviewable source URLs), and `operations`. Operations contain `table` (`entrances`, `stations`, `reviews`), `action` (`add`, `update`, `delete`), and `id`. Add/update include a complete `record`. Update/delete require `before_sha256`, computed with `transit_map.build.digest` on the current record. Keys are respectively `id`, `name`, and `entrance_id`. Transactions are applied by filename and operations by array order; each transaction must leave a valid database.

Example shape (illustrative, not a real observation):

```json
{"transaction_id":"YYYY-MM-DD-review-ID","rationale":"Explain the observation and uncertainty","sources":["https://example.org/evidence"],"operations":[{"table":"reviews","action":"add","id":"WMATA-ID","record":{"entrance_id":"WMATA-ID","reviewed_on":"YYYY-MM-DD","status":"Unreviewed","notes":"Describe evidence and remaining work"}}]}
```

Network fetches remain proposals in `build/`; they never rewrite the baseline or submit OSM edits. OSM snapshot replacement is deliberately unsupported by this first ledger version: a future versioned snapshot migration must preserve licensing, query completeness, and historical provenance.

Reviews require a nonempty textual `notes` field, an ISO `reviewed_on` date, and one of the statuses accepted by `transit_map.core.REVIEW_STATUSES`. All statuses appear in both the published worklist and CLI review queue; unreviewed records also remain visible. A shared automated candidate always creates a review reason, even if a desktop confirmation is recorded.

Station metadata updates are supported. Adding, deleting or renaming a station changes the membership shared by the inventory and frozen OSM query windows, so it requires a future explicit snapshot migration. Adding only a station fails inventory coverage; adding a station and entrance together fails OSM query coverage. Do not bypass those checks or change the baseline lock to force admission.

## Candidate decisions

A review may carry `candidate_decisions`: a nonempty list of objects with exactly `feature_id` (`node|way|relation/<id>`), `decision` (`accepted`, `rejected` or `unresolved`), a nonempty `reason`, and `evidence` (HTTPS URLs or existing `docs/evidence/*.json` paths). Each feature appears at most once per review; at most one decision is `accepted`, and an accepted feature must exist in the recorded OSM snapshot.

The decision, not the narrative status, closes a shared-candidate warning: only `accepted` or `rejected` on the record's screened candidate closes it. A confirmation status without an accepted decision is itself an open worklist reason. Status-based questions (geometry, elevator identity, source-reference conflicts) remain open regardless of decisions. `rejected` means "this feature is not this record's identity"; it never asserts that an entrance is missing.

Stored status values are immutable history. Outputs display labels: `Existing entrance confirmed` → "Existing access feature confirmed"; `Source location needs correction` → "Source reference conflict".
