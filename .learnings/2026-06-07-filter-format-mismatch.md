# Filter format mismatch with MCP server

## Symptom
- CLI `query-records --filters-json '{"operator":"date_eq","operands":["fieldId","2026-06-03"]}'` returns 10 records with **wrong dates** (e.g. 2026-05-04, 2026-05-22) instead of 0 (when using 2099-01-01) or 277 (when using 2026-06-03).
- MCP server silently ignores the flat leaf filter, but does NOT error.

## Root cause
MCP `query_records.filters` schema requires **nested** form:
```json
{"operator": "and", "operands": [{"operator": "date_eq", "operands": ["fieldId", "2026-06-03"]}]}
```
But CLI's `build-filter` and the leaf filters in `filters.py` produce **flat** form:
```json
{"operator": "date_eq", "operands": ["fieldId", "2026-06-03"]}
```
MCP accepts the flat call but treats it as no-op (or schema-invalid → ignored).

## Verified by direct MCP call
- Flat format + 2099-01-01: returns 5+ records (filter ignored)
- Nested format + 2099-01-01: returns 0 records (filter applied)
- Nested format + 2026-06-03, limit 50, fieldIds=[gUTiOli]: returns 50 records, **0 mismatches** (all 评价时间 = 2026-06-03)

## Impact
- `query-records` filters: silently ignored
- `process-records-with-marker` filters: silently ignored
- `process-date-range-with-marker` filters: silently ignored (the day-split works, but base filter does nothing)
- `query_stats` and `query_records_stats` filters: same issue likely (untested, but same payload path)

## What worked around the bug
Calling MCP directly with nested format works. For end-user count of 2026-06-03 we used `query_stats` and got 277.

## Related side issues
- Server returns malformed JSON for some records (unterminated string at byte ~60188) — at least one review cell has bad escaping. `process-records-with-marker` crashes there.
- Resolved by passing `fieldIds=[...]` to limit the columns returned, avoiding the problematic cell.

## Fix directions (not yet applied)
1. CLI `filters.py`: change `eq_filter/ne_filter/date_eq_filter` to return nested form (operator-wrapped). Backwards-incompatible with any caller using flat form.
2. Or: change MCP payload builder to auto-wrap flat leaves in `{"operator":"and", "operands":[<leaf>]}`. Less intrusive.
3. `build-filter` and the new `input.filter`/`input.filters` reading from prior commits both already work — the real issue is the **shape**, not the key name.
