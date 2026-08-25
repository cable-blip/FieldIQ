# Backend API Contract

## Tactical Analysis Request

`POST /api/v1/analysis`

The endpoint validates match context for a future tactical-analysis request.

Until a validated dataset and tactical model are connected, it returns:

- `status: unavailable`
- `data_driven: false`
- an explicit reason
- the accepted, validated request

It must not return a field recommendation at this stage.

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

## Source Column Mapping Preflight

`POST /api/v1/datasets/column-mappings/validate`

This JSON endpoint validates a source-specific mapping before a source CSV is
transformed. The request contains `source_headers` and a `column_mapping` of
FieldIQ canonical field name to exact source header. Every required canonical
field must be mapped, each mapped source header must exist exactly once, and a
source header cannot supply two canonical fields.

The endpoint validates mapping metadata only. It does not read CSV rows, infer
semantic equivalence, transform data, or persist a mapping. See [[CSV Dataset
Contract]] for the mapping workflow and permitted canonical names.
