# Submission

## Summary of changes

This document explains how I approached the assignment, the decisions I made along the way, the gaps I am aware of, and how I used AI tools to support the work. My aim throughout was to understand the program properly before changing it, to keep a human review step at each stage rather than accepting AI output blindly, and to make improvements that genuinely served the end user.

Fixed 5 backend workflow bugs that violated the required business rules, redesigned the frontend with a risk-grouped queue, confirmation modals, search and filtering, a processed-items view, and added 21 backend tests covering all workflow rules.

## Process

1. I asked Claude Code to study the README.md and analyse the program, then explain it to me. It clearly described the architecture, identified the bugs and issues in the program, and flagged the problem with test coverage.

2. I asked it to document these issues and produce an implementation plan. I reviewed the proposed plan to confirm I agreed with the intended changes, and then asked it to proceed.

3. I checked that the work was progressing as planned — reviewing the code at a high level, as well as the UI and UX — to confirm it was being implemented correctly.

4. With time remaining, I asked it to suggest functions and UX elements that could be improved in the program.

5. I asked it to write a proper system specification that a designer could use to create a better UI and UX.

6. I provided that specification to Claude Design (claude.ai/design) to produce a new layout.

7. I instructed Claude Code to implement the new design.

8. I reviewed what remained to be done and asked for further improvements. These matched what I already had in mind: allowing the reviewer to see the total number of jobs, surfacing waiting-time information, and providing a better search and filter function so the reviewer could double-check items once they were complete.

My key decisions were to lead with analysis before implementation, to review and approve the AI's plan before any code was written, and to keep checking the output at each stage rather than trusting it end to end. I used AI tools in distinct, complementary roles: Claude Code for analysis, planning, implementation, and improvement suggestions, and Claude Design for translating a written specification into a new layout. The improvements I prioritised — job totals, waiting-time visibility, and stronger search and filtering — were driven by what the reviewer would actually need.

## Bugs fixed

1. **Active queue filter incomplete** (`backend/app/main.py:62`): Only excluded `approved` items. Fixed to exclude all terminal statuses (`approved`, `rejected`, `escalated`).

2. **Queue sorting wrong** (`backend/app/main.py:64-68`): Sorted only by `submitted_at` descending. Fixed to sort by risk_level (high > medium > low), then customer_tier (priority > standard), then submitted_at ascending (oldest first).

3. **Claim validation too loose** (`backend/app/main.py:78`): Allowed claiming `in_review` items (already owned by another reviewer). Fixed to require `status == "unassigned"`.

4. **Approve/reject/escalate validation too loose** (`backend/app/main.py:83-87`): Only blocked `approved` items. Allowed approving `unassigned` items or acting on `rejected`/`escalated` ones. Fixed to require `status == "in_review"`.

5. **Reviewer not recorded on terminal actions** (`backend/app/main.py:89`): Approve/reject/escalate did not set `assigned_reviewer`. Fixed to record the acting reviewer.

## Product/UX decisions

**Conditional action buttons** (highest-impact change): Replaced 4 always-visible buttons with a computed set based on item status. Unassigned items show only "Claim"; in-review items show "Approve", "Reject", "Escalate"; terminal items show "No actions available." This directly answers the reviewer's question: "what can I do with this item right now?"

**Risk-grouped queue with urgency strip**: Items are grouped by risk level (high/medium/low) with sticky headers and a color-coded urgency strip in the detail panel showing risk, customer tier, and wait time at a glance.

**Confirmation modals**: Terminal actions (approve/reject/escalate) require confirmation through a modal dialog, with the item title displayed prominently so the reviewer can verify they are acting on the correct item.

**Queue summary bar**: Shows "3 high-risk, 5 unassigned, 2 waiting >24h" at the top of the queue, giving reviewers instant situational awareness without scanning every card.

**Wait-time indicators**: Each card shows how long an item has been waiting with color escalation — gray under 24h, amber 24-48h, red over 48h — so reviewers can spot stale items immediately.

**Search and filtering**: Text search by title or ID, plus dropdown filters for risk level and customer tier. All filters compose together, with a "Clear filters" link when no items match.

**Processed items tab**: A "Processed" tab shows approved, rejected, and escalated items grouped by status, so reviewers can double-check completed work. Items move from Active to Processed automatically after terminal actions.

**Keyboard shortcuts**: Arrow keys navigate, C claims, A/R/E open action modals, Esc dismisses, / focuses search.

**Better error messages**: Backend now returns specific error details (e.g., "Cannot approve an item with status 'unassigned'") and the frontend displays them instead of a generic message.

## Tests added

`backend/tests/test_workflow.py` — 21 tests using FastAPI's `TestClient` with an `autouse` reset fixture for test isolation:

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
- No accessibility audit beyond semantic HTML and ARIA labels

## Files changed and why

| File | Why |
|------|-----|
| `backend/app/main.py` | Fixed all 5 workflow bugs: queue filter, sorting, claim/action validation, reviewer recording |
| `backend/tests/test_workflow.py` | New file: 21 tests covering all business rules via HTTP |
| `backend/requirements.txt` | Added `httpx` dependency for `TestClient` |
| `frontend/src/App.vue` | Full UI rewrite: risk-grouped queue, confirmation modals, search/filtering, processed items tab, keyboard shortcuts, summary bar |
| `frontend/src/api.ts` | Parse backend error detail; added `activeOnly` parameter to fetch all items |
| `frontend/src/styles.css` | Complete design system: urgency strip, action buttons, modal, toast, search bar, filter controls, responsive layout |
| `data/review_items.json` | Added 10 new seed items with varied statuses, risk levels, and tiers for thorough testing |
| `DESIGN_SPEC.md` | Design system specification used as input for Claude Design |

## AI assistance used

Used Claude Code for analysis, planning, and implementation, and Claude Design (claude.ai/design) for translating a written specification into a new layout. All changes were reviewed and verified manually — tests were run (`pytest -v`, 21/21 passing) and the app was tested in the browser to confirm workflow correctness and UX improvements. The full process is described in the Process section above.
