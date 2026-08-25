# Backend API Contract

This note is the freeze point for backend and frontend work. Cursor and
Antigravity may implement in parallel only against the schemas below. If a
schema must change, update this note first.

Ownership:

- Cursor: `backend/`, `tests/`, this note, `Docs/FieldIQ/03_Data/`
- Antigravity: `frontend/`
- Neither owner may invent cricket records, player names, venues, speeds, or
  match outcomes. Schema fixtures must be labelled as fixtures.

---

## Tactical Analysis Request

`POST /api/v1/analysis`

The endpoint validates match context for a future tactical-analysis request.

Until a validated dataset and tactical model are connected, it returns:

- `status: unavailable`
- `data_driven: false`
- an explicit reason
- the accepted, validated request

It must not return a field recommendation at this stage.

---

## Dataset CSV Validation

`POST /api/v1/datasets/validate`

This endpoint validates an uploaded-in-request CSV against the FieldIQ canonical
delivery contract. It does not persist the file, train a model, or manufacture
missing cricket information.

Request requirements:

- `Content-Type: text/csv`
- `source_name` query parameter
- `dataset_version` query parameter
- optional `schema_version` query parameter; defaults to `fieldiq.delivery-csv.v1`

The response always describes the supplied source, dataset version, schema
version, validation status, row-quality summary, and row/field-level issues.
Malformed CSV data receives a `200` report with `validation_status: invalid` so
the caller can display every validation issue. An unsupported media type returns
`415`. See [[CSV Dataset Contract]] for the canonical column definitions.

The response also includes `optional_field_availability`. This is an observed
coverage profile (column presence and non-empty value counts/rates), not inferred
cricket intelligence and not a claim that a populated value is accurate.

---

## Source Column Mapping Preflight

Frozen for DATA-004. See [[CSV Dataset Contract]] for required and optional
canonical field names.

### Endpoint

`POST /api/v1/datasets/column-mappings/validate`

- `Content-Type: application/json`
- Mapping metadata only. The service does not read CSV rows, infer that two
  differently named columns mean the same thing, transform data, or persist a
  mapping.

### Request body

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

| Field | Type | Rules |
| --- | --- | --- |
| `source_headers` | array of strings | Required. At least one header. Values are exact source column names. |
| `column_mapping` | object of string to string | Required. At least one entry. Keys are FieldIQ canonical field names. Values are exact source header names from `source_headers`. |

Empty `source_headers` or empty `column_mapping` is a request-schema failure,
not a mapping report.

The example above is incomplete against required canonical fields; a valid
complete mapping must include every required field listed in [[CSV Dataset
Contract]].

### Success response

HTTP `200`. Invalid mappings still return `200` with `mapping_status: invalid`
so the UI can show every issue.

```json
{
  "mapping_status": "valid",
  "mapped_columns": {
    "match_id": "game",
    "batter_name": "striker",
    "bowler_name": "bowler"
  },
  "unmapped_source_columns": [],
  "issues": []
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `mapping_status` | `"valid"` or `"invalid"` | `valid` only when `issues` is empty. |
| `mapped_columns` | object | Echo of the submitted `column_mapping`. |
| `unmapped_source_columns` | array of strings | Source headers that are not used as a mapping value. Sorted. |
| `issues` | array | Mapping problems. Empty when valid. |

Each issue:

```json
{
  "canonical_field": "batter_name",
  "source_field": "striker",
  "code": "mapped_source_column_missing",
  "message": "Mapped source column is not listed in source_headers."
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `canonical_field` | string or null | FieldIQ field when the issue is about a canonical name. |
| `source_field` | string or null | Source header when the issue is about a source name. |
| `code` | string | Machine-readable code from the table below. |
| `message` | string | Human-readable explanation. |

### Mapping issue codes

| Code | When |
| --- | --- |
| `blank_source_header` | A source header is empty or whitespace. |
| `duplicate_source_header` | The same source header appears more than once in `source_headers`. |
| `unknown_canonical_field` | A mapping key is not a required or optional FieldIQ delivery field. |
| `missing_required_mapping` | A required canonical field has no mapping entry. |
| `source_column_mapped_multiple_times` | One source header is mapped to more than one canonical field. |
| `blank_mapping_target` | A mapping value is empty or whitespace. |
| `mapped_source_column_missing` | A mapping value is not present in `source_headers`. |

Optional canonical fields may be omitted. Omitted optional fields are
unavailable; they are not inferred.

### Request-schema errors

HTTP `422` when the JSON body fails Pydantic/FastAPI validation (missing fields,
wrong types, empty `source_headers`, empty `column_mapping`). FastAPI shape:

```json
{
  "detail": [
    {
      "type": "too_short",
      "loc": ["body", "source_headers"],
      "msg": "List should have at least 1 item after validation, not 0",
      "input": []
    }
  ]
}
```

The frontend must not treat `422` as a mapping report. Show it as a request
error. Do not invent a substitute mapping result.

### Frontend display requirements

The UI must show:

- valid or invalid mapping status from `mapping_status`
- mapped fields from `mapped_columns`
- unmapped source columns from `unmapped_source_columns`
- missing required mappings (`missing_required_mapping`)
- duplicate source columns (`duplicate_source_header`)
- unknown canonical fields (`unknown_canonical_field`)
- required fields distinguished from optional fields
- unmapped optional fields as unavailable

### DATA-004 acceptance

- Backend tests for this endpoint pass.
- Frontend tests against this request and response pass.
- No files outside each owner's paths change without agreement.
- No real cricket records are created for fixtures.
