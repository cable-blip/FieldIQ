# FieldIQ Canonical Delivery CSV Contract

**Contract version:** `fieldiq.delivery-csv.v1`  
**Milestone status:** Functional validation only. The validator does not store,
clean, enrich, infer, or train from submitted data.

## Purpose

This is the first ingestion boundary for delivery-level cricket data. It makes
the source dataset traceable and rejects data that cannot safely support later
feature engineering. It is not a claim that every cricket provider exposes all
of these fields; an adapter or export must provide the required canonical
columns before validation.

## Dataset metadata

Metadata is supplied with the validation request rather than repeated on every
delivery row:

| Field | Requirement | Meaning |
| --- | --- | --- |
| `source_name` | Required | Name of the originating provider, export, or internal source. |
| `dataset_version` | Required | Source-defined version or immutable import label. |
| `schema_version` | Required; current value is `fieldiq.delivery-csv.v1` | FieldIQ contract being validated. |

The validation response records this metadata together with `valid` or
`invalid` status and a quality summary. This milestone does not treat a supplied
source name as proof of provenance; provenance verification is a later concern.

## File requirements

- UTF-8 encoded CSV, including UTF-8 with BOM.
- A single header row with exact canonical column names.
- At least one delivery row.
- Comma delimiter.
- Submit to `POST /api/v1/datasets/validate` as `Content-Type: text/csv`.
- The validator never writes the submitted data to disk or a database.

## Required delivery columns

| Column | Type and constraints | Meaning |
| --- | --- | --- |
| `match_id` | Non-empty string | Source-stable match identifier. |
| `innings` | Integer, at least 1 | Innings identifier as supplied by the source. |
| `delivery_number` | Integer, at least 1 | Sequential delivery identifier within the match and innings. It is not assumed to be a legal-ball count. |
| `batter_name` | Non-empty string | Batter facing the delivery, as supplied. |
| `bowler_name` | Non-empty string | Bowler delivering the ball, as supplied. |
| `runs_batter` | Integer, at least 0 | Runs credited to the batter. |
| `runs_extras` | Integer, at least 0 | All non-batter runs, including any penalty runs represented by the source. |
| `runs_total` | Integer, at least 0 | Total runs from the delivery; must equal `runs_batter + runs_extras`. |
| `is_wicket` | `true` or `false` | Whether the source records a wicket on the delivery. |

`match_id + innings + delivery_number` must be unique. The validator does not
renumber duplicates or choose a preferred duplicate row.

## Optional fields and data availability

The following are useful later, but are deliberately **not** required by this
first contract: match format, teams, venue, match date, non-striker, dismissal
details, delivery line/length, speed, movement, pitch/shot coordinates, field
placements, and fielder outcomes.

Their absence must remain explicit. No default values, inferred positions, or
synthetic tracking measurements are created during ingestion.

## Validation outcome

Every validation report contains:

- dataset metadata (`source_name`, `dataset_version`, `schema_version`)
- `validation_status`: `valid` or `invalid`
- quality counts: total, valid, invalid rows, and valid-row rate
- optional-field availability: whether each recognised optional column exists,
  how many delivery rows contain a value, and the resulting value-coverage rate
- a list of issues, each with an error code and, when applicable, CSV row and field

An invalid result is a diagnostic report, not a partially accepted dataset. No
dataset persistence or model connection occurs in this milestone.

## Availability and coverage profile

The validation response reports coverage for each recognised optional field. A
field is reported as present only when the CSV includes its exact column name;
its coverage rate is the number of non-empty values divided by the number of
delivery rows. A missing column therefore has zero coverage. The profile does
not derive a value from another column, impute blanks, or certify data accuracy.

This supports an explicit hand-off to later feature engineering: a model may use
only fields that have been independently assessed as appropriate and sufficiently
covered for its stated purpose.

## Source-column mapping preflight

Real providers frequently use different column names. Before any adapter
converts rows, submit its header list and an explicit mapping to
`POST /api/v1/datasets/column-mappings/validate`.

The mapping is a JSON object whose keys are FieldIQ canonical names and whose
values are exact source-header names. For example, a source header named
`striker` may be explicitly mapped to FieldIQ's `batter_name`; the service does
not make that assumption by itself.

```json
{
  "source_headers": ["game", "striker", "bowler"],
  "column_mapping": {
    "match_id": "game",
    "batter_name": "striker",
    "bowler_name": "bowler"
  }
}
```

For a valid complete mapping, all required canonical fields listed above must
also be mapped. Optional canonical fields may be mapped only when their source
header exists. The preflight rejects unknown canonical names, missing required
mappings, blank/duplicate source headers, nonexistent mapped headers, and
mapping the same source header to more than one FieldIQ field.

It returns the supplied mapping, unmapped source headers, and explicit issues.
It does not interpret the source headers, modify CSV data, or persist a mapping;
those need a reviewed source adapter in a later milestone.

## Example fixture

```csv
match_id,innings,delivery_number,batter_name,bowler_name,runs_batter,runs_extras,runs_total,is_wicket
fixture-match-001,1,1,batter_a,bowler_a,0,0,0,false
```

The fixture is only a schema example; it is not real match data.
