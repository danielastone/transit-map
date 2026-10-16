# Append-only research transactions

The existing source files are the adoption baseline, not reconstructed historical transactions. Never edit merged baseline files or merged transaction JSON. Add a new, lexically ordered JSON file to correct an earlier assertion. Work on a feature branch, open a PR, pass CI, then squash merge.

Each transaction has a unique `transaction_id`, nonempty `rationale`, `sources` (reviewable source URLs), and `operations`. Operations contain `table` (`entrances`, `stations`, `reviews`), `action` (`add`, `update`, `delete`), and `id`. Add/update include a complete `record`. Update/delete require `before_sha256`, computed with `transit_map.build.digest` on the current record. Keys are respectively `id`, `name`, and `entrance_id`. Transactions are applied by filename and operations by array order; each transaction must leave a valid database.

Example shape (illustrative, not a real observation):

```json
{"transaction_id":"YYYY-MM-DD-review-ID","rationale":"Explain the observation and uncertainty","sources":["https://example.org/evidence"],"operations":[{"table":"reviews","action":"add","id":"WMATA-ID","record":{"entrance_id":"WMATA-ID","reviewed_on":"YYYY-MM-DD","status":"Unreviewed","notes":"Describe evidence and remaining work"}}]}
```

Network fetches remain proposals in `build/`; they never rewrite the baseline or submit OSM edits. OSM snapshot replacement is deliberately unsupported by this first ledger version: a future versioned snapshot migration must preserve licensing, query completeness, and historical provenance.
