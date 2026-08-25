---
task_id: DATA-004
status: completed
backend_owner: Cursor
frontend_owner: Antigravity
---

# DATA-004 - Frontend Dataset Mapping UI

## Objective

Create a frontend interface for reviewing and submitting explicit source-column
mappings into the FieldIQ canonical delivery CSV contract.

## Read first

- [[CSV Dataset Contract]]
- [[Backend API Contract]]
- [[System Architecture]]

Also read:

- `C:\Projects\cricket-tactical-intelligence\AGENTS.md`

## Backend owner

Cursor owns:

- backend API
- request and response schemas
- mapping validation
- backend tests
- API documentation

Allowed paths:

```text
backend/
tests/
Docs/FieldIQ/01_Architecture/
Docs/FieldIQ/03_Data/
```

## Frontend owner

Antigravity owns:

- mapping form
- source-header display
- required-field indicators
- validation errors
- availability states
- frontend tests
- API integration

Allowed paths:

```text
frontend/
```

## API contract

Endpoint:

`POST /api/v1/datasets/column-mappings/validate`

The frontend must send:

```json
{
  "source_headers": [],
  "column_mapping": {}
}
```

That is the request shape. Empty arrays or objects are request-schema errors
(`422`). A mapping report requires at least one source header and at least one
mapping entry. Full field rules are frozen in [[Backend API Contract]].

The frontend must display:

- valid or invalid mapping status
- mapped fields
- unmapped source columns
- missing required mappings
- duplicate source columns
- unknown canonical fields

## Data rules

- Do not create real cricket records.
- Do not invent player names, venues, speeds, or match data.
- Use clearly labelled schema fixtures only.
- Missing fields must be displayed as unavailable.
- Do not silently infer that two differently named columns mean the same thing.

## Acceptance criteria

- Cursor backend tests pass.
- Antigravity frontend tests pass.
- The frontend uses the documented API.
- Invalid mappings are visible to the user.
- Optional fields are clearly distinguished from required fields.
- No files outside the assigned ownership paths are changed without agreement.

## Status history

- 2026-08-25: Task created
- 2026-08-25: Baseline commit `19d8b3f` — CSV validation and source mapping preflight
- 2026-08-25: Frontend commit `2d85235` — dataset mapping UI
- 2026-08-25: Merged to `main` (`60ffdb4`); status set to completed
