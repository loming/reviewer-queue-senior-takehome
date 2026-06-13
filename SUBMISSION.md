# Submission

## Summary of changes

Fixed 5 backend workflow bugs that violated the required business rules, improved the frontend to show only valid actions per item status with visual risk indicators, and added 19 backend tests covering all workflow rules.

## Bugs fixed

1. **Active queue filter incomplete** (`backend/app/main.py:62`): Only excluded `approved` items. Fixed to exclude all terminal statuses (`approved`, `rejected`, `escalated`).

2. **Queue sorting wrong** (`backend/app/main.py:64-68`): Sorted only by `submitted_at` descending. Fixed to sort by risk_level (high > medium > low), then customer_tier (priority > standard), then submitted_at ascending (oldest first).

3. **Claim validation too loose** (`backend/app/main.py:78`): Allowed claiming `in_review` items (already owned by another reviewer). Fixed to require `status == "unassigned"`.

4. **Approve/reject/escalate validation too loose** (`backend/app/main.py:83-87`): Only blocked `approved` items. Allowed approving `unassigned` items or acting on `rejected`/`escalated` ones. Fixed to require `status == "in_review"`.

5. **Reviewer not recorded on terminal actions** (`backend/app/main.py:89`): Approve/reject/escalate did not set `assigned_reviewer`. Fixed to record the acting reviewer.

## Product/UX decisions

**Conditional action buttons** (highest-impact change): Replaced 4 always-visible buttons with a computed set based on item status. Unassigned items show only "Claim"; in-review items show "Approve", "Reject", "Escalate"; terminal items show "No actions available." This directly answers the reviewer's question: "what can I do with this item right now?"

**Risk-level badges**: Added colored badges (red/yellow/green) in the queue list so reviewers can visually scan for high-risk items without reading each entry.

**Status-colored pills**: The detail panel status pill now uses semantic colors (blue for in_review, green for approved, red for rejected, yellow for escalated).

**Better error messages**: Backend now returns specific error details (e.g., "Cannot approve an item with status 'unassigned'") and the frontend displays them instead of a generic message.

**Terminal item removal**: When a reviewer approves/rejects/escalates, the item is removed from the queue list and the next item is auto-selected, keeping the workflow flowing.

## Tests added

`backend/tests/test_workflow.py` — 19 tests using FastAPI's `TestClient` with an `autouse` reset fixture for test isolation:

- **Queue filtering** (4 tests): terminal items excluded, active items included
- **Queue sorting** (1 test): verifies exact ID order against the urgency spec
- **Claim rules** (4 tests): succeeds on unassigned, fails on in_review/approved/rejected
- **Approve/reject/escalate** (5 tests): succeeds on in_review, fails on unassigned/escalated
- **Terminal immutability** (2 tests): all 4 actions fail on approved and rejected items
- **Reviewer recording** (2 tests): assigned_reviewer set on claim and approve
- **Full workflow** (1 test): claim → approve → item disappears from active queue

## Known gaps

- No frontend tests (would add Vitest + Vue Test Utils for component behavior)
- No authentication — reviewer identity is hardcoded as `"alex"`
- In-memory data store resets on server restart; no database
- No real-time sync — if multiple reviewers use the tool, local state can drift
- No pagination or search for large queues
- No accessibility audit beyond semantic HTML and ARIA labels
- No confirmation dialog before terminal actions (approve/reject/escalate)

## Files changed and why

| File | Why |
|------|-----|
| `backend/app/main.py` | Fixed all 5 workflow bugs: queue filter, sorting, claim/action validation, reviewer recording |
| `backend/tests/test_workflow.py` | New file: 19 tests covering all business rules via HTTP |
| `backend/requirements.txt` | Added `httpx` dependency for `TestClient` |
| `frontend/src/App.vue` | Conditional buttons, risk badges, status pill, terminal removal, error display |
| `frontend/src/api.ts` | Parse backend error detail for user-facing messages |
| `frontend/src/styles.css` | Risk badge colors, status pill colors, terminal notice style |

## AI assistance used

Used Claude Code to analyze the codebase structure, identify the intentional bugs against the README spec, and assist with writing implementation code and tests. All changes were reviewed and verified manually — tests were run (`pytest -v`, 21/21 passing) and the app was tested in the browser to confirm workflow correctness and UX improvements.
