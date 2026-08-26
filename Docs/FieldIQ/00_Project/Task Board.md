# FieldIQ Task Board

## Ready



## In Progress



## Backend Review

## Frontend Review

## Integration Review

## Completed

- [[DATA-004 - Frontend Dataset Mapping UI]]
- [[UI-001 - 3D Cricket Field Prototype]]
- [[INTEG-002 - Deterministic Matchup Engine and 3D Field Integration]]
- [[DATA-005 - Real Dataset Loading and Player Lists]]

## Blocked

## Rules

1. Every task must have a unique task ID.
2. Every task must link to its contract.
3. Cursor and Antigravity must not modify each other's ownership areas.
4. Missing data must remain unavailable.
5. No agent may invent cricket data.
6. No commit or push happens before human approval.

## Coordination

Obsidian task note
→ Cursor reads backend assignment; Antigravity reads frontend assignment
→ Cursor implements API; Antigravity implements UI against the frozen contract
→ Each owner runs their tests
→ Human reviews both diffs
→ Human approves commits and merge

If the API must change, update [[Backend API Contract]] before the frontend
changes. If the UI needs a missing response field, record it on the task note
instead of silently changing the backend.

## Current git state (2026-08-25)

`main` is clean. DATA-004 backend, frontend, and merge commits are already on
`main`. Do not recreate `task/DATA-004-backend` or `task/DATA-004-frontend`
worktrees unless a follow-up task is opened.
