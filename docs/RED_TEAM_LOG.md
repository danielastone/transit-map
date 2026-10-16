# Incremental red-team log

## Pass 1 — baseline ceff5f4 (2026-10-16)

External review reproduced 242 source records / 98 stations / 714 OSM features / 14 desktop reviews, 20 passing tests and 342 generated pages. It identified a Reston directional contradiction, possible cross-side candidate reuse, query-window sensitivity, and transaction/publication inconsistencies. The geographic allegations remain unresolved; none is promoted into a corrected research observation by this pass.

## Step 2 — transaction probes and queue corrections (2026-10-16)

Each probe used a separate temporary copy of the unchanged baseline and a synthetic transaction. Test data never entered the canonical ledger.

| Probe | Expected behavior | Observed at ceff5f4 | Disposition |
| --- | --- | --- | --- |
| Add a valid `New entrance needed` review | Review visible in tasks and CLI queue | Materialization succeeds; both outputs omit it | Confirmed defect; fixed by shared, complete worklist |
| Add a review with no `notes` | Validation rejects unusable review | Materialization succeeds; publication raises `KeyError: notes` | Confirmed defect; reject absent, blank, or nontext notes during validation |
| Add station plus entrance | Explicitly enforce snapshot coverage | `ValueError: OSM query coverage mismatch` | Membership extension remains unsupported pending snapshot migration; documented |
| Update existing station source URL with correct before hash | Materialize and publish | Both succeed | Refutes the broader claim that no station transaction can pass |

Regression coverage applies every allowed review status through a transaction and checks both HTML tasks and CLI output. It also checks missing/blank/nontext notes, station metadata updates, station membership rejection, all-record visibility, and a confirmed review whose automated candidate is shared.

Both task outputs now list all 242 source records. The baseline has 31 records with shared automated candidates, and all 31 receive an explicit identity-review reason regardless of distance or desktop status. There are 237 records with open review reasons and five desktop-confirmed records without open reasons. These are workflow states, not findings that entrances are missing. Automated screen labels/counts and baseline source/review assertions are unchanged.

### Remaining work

- **F1 unresolved:** use WMATA access maps and OSM geometry to investigate Reston north/south identities, then Herndon. Live OSM alone does not establish which source/review is wrong.
- **F2 partially addressed:** all records and reuse conflicts are now exposed. Cross-side identity validation itself has not been performed.
- **F3 unresolved:** assess query-window sensitivity separately; zero tagged features in a small window does not establish physical absence.
- **F4 bounded:** publication omissions and missing-notes acceptance fixed. Station membership changes still require a versioned OSM snapshot migration; metadata updates work.

Executable regressions: `tests/test_red_team.py`. Reproduce with `python -m unittest discover -s tests -v`, then `python -m transit_map validate`, `python -m transit_map audit`, `python -m transit_map review-queue` and `python -m transit_map.build`.
