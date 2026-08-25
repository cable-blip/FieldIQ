# Active Task

task_id: DATA-003
status: ready
objective: Add dataset mapping preflight
priority: high

## Shared contract

Read:
- [[CSV Dataset Contract]]
- [[Backend API Contract]]
- [[System Architecture]]

## Cursor assignment

Owner: Cursor

Implement:
- Backend schemas
- FastAPI endpoint
- Validation logic
- Unit and integration tests

Allowed paths:
- backend/
- tests/

## Antigravity assignment

Owner: Antigravity

Implement:
- Dataset upload interface
- Mapping form
- Validation-result display
- Error and quality states

Allowed paths:
- frontend/

## Acceptance criteria

- Backend tests pass.
- Frontend uses the documented API contract.
- No invented cricket data.
- Missing fields remain visibly unavailable.
- Both sides work against the same endpoint contract.

## Completion checklist

- [ ] Cursor implementation complete
- [ ] Antigravity implementation complete
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Integration verified
- [ ] Human review complete