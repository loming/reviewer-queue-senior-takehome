# Reviewer Queue — Design System Spec

## 1. Product Context

### What is this?

An internal operations tool for a fintech company. A small team of reviewers (3–8 people) uses this daily to triage compliance and financial review items — wire transfers, identity mismatches, payout changes, document re-submissions, etc.

The stakes are real: a missed high-risk item could mean regulatory exposure. A slow queue means customers wait.

### Who uses it?

**Primary user: Operations Reviewer**
- Works through 30–80 items per day
- Needs to make fast, confident decisions
- Cares about: "What should I work on next? What do I need to know? What can I do?"
- Switches between this tool, internal docs, and customer records
- Uses a desktop browser (1280px+ viewport) during business hours

**Secondary user: Team Lead / Manager**
- Checks queue health and throughput
- Wants to see: backlog size, who owns what, how long items have been waiting
- Not a target for this phase, but design should not block this future use

### Core workflow

```
Queue scan → Pick item → Read context → Decide → Act → Next item
```

The entire UX should optimize for this loop. Every screen element either helps the reviewer **find the right item**, **understand it**, or **act on it**. Anything else is noise.

---

## 2. Information Architecture

### Data model (per item)

| Field | Type | UX role |
|-------|------|---------|
| `id` | string (e.g. "RV-1024") | Reference anchor |
| `title` | string | Primary identifier in queue |
| `submitted_at` | ISO datetime | Age indicator, urgency signal |
| `risk_level` | `low` / `medium` / `high` | Strongest urgency signal |
| `customer_tier` | `standard` / `priority` | Secondary urgency signal |
| `status` | `unassigned` / `in_review` / `approved` / `rejected` / `escalated` | Determines available actions |
| `assigned_reviewer` | string or null | Ownership indicator |
| `notes_count` | integer | Complexity/history hint |
| `summary` | string | Decision context |

### Status state machine

```
unassigned ──claim──▶ in_review ──approve──▶ approved (terminal)
                                 ──reject───▶ rejected (terminal)
                                 ──escalate─▶ escalated (terminal)
```

- `unassigned`: available to claim. Show "Claim" action.
- `in_review`: owned by a reviewer. Show "Approve", "Reject", "Escalate" actions.
- `approved` / `rejected` / `escalated`: terminal. No actions. These items are excluded from the active queue.

### Queue sort order (business rule)

Items are ordered by urgency, not recency:

1. `risk_level`: high → medium → low
2. `customer_tier`: priority → standard
3. `submitted_at`: oldest first (longest-waiting items surface)

This means the top of the queue is always the most urgent, longest-waiting item. The designer should treat queue position as a proxy for urgency — **top = act now**.

---

## 3. Current State & Problems

### What exists today

A two-panel layout:
- **Left (360px):** scrollable list of queue items, each showing title, risk level text, customer tier, status, and assigned reviewer
- **Right (flex):** detail panel for the selected item — ID, title, status pill, submitted date, risk, customer tier, assignee, summary, notes count, and action buttons

### UX problems to solve

| # | Problem | Impact | Severity |
|---|---------|--------|----------|
| P1 | **Queue items are visually flat** — every item looks the same weight regardless of risk or urgency | Reviewer can't scan for what matters | High |
| P2 | **No age/wait-time indicator** — reviewer sees a date but can't quickly gauge "how long has this been waiting?" | Stale items get overlooked | High |
| P3 | **No queue summary/counts** — no way to see at a glance how many items need attention, or the breakdown by status | Team lead and reviewer both lack situational awareness | Medium |
| P4 | **Detail panel lacks information hierarchy** — summary, risk, customer tier, and notes count are given equal visual weight | Reviewer has to read everything to find what matters | Medium |
| P5 | **Actions have no visual weight differentiation** — "Approve" and "Reject" are styled identically; no confirmation on destructive/terminal actions | Risk of accidental terminal action | High |
| P6 | **No empty state** — if the queue is cleared, the reviewer sees a blank panel | Unclear whether the app is broken or the queue is actually empty | Low |
| P7 | **No success feedback** — after an action, the item silently disappears or updates with no confirmation | Reviewer isn't sure the action took effect | Medium |
| P8 | **Mobile layout stacks without adaptation** — queue and detail just stack vertically, no mobile-specific interaction pattern | Unusable on small screens (low priority — desktop-primary tool) | Low |
| P9 | **No keyboard navigation** — power reviewers can't arrow through items or use shortcuts to act | Slower throughput for experienced users | Medium |
| P10 | **"Notes on this item" is passive text** — notes count is displayed but there's no way to view or add notes | Reviewer has incomplete context | Medium |

---

## 4. Design Requirements

### 4.1 Queue List (Left Panel)

**Goal:** Let the reviewer scan 10–30 items and instantly spot what needs attention.

**Queue item card — required elements:**
- Title (primary text, bold)
- Risk level badge with color coding:
  - `high`: red background — this is the fire alarm
  - `medium`: amber/yellow background
  - `low`: green or neutral background
- Customer tier indicator: `priority` should be visually distinct (icon, label, or badge). `standard` can be unmarked.
- Status: shown as a colored pill or tag
- Assigned reviewer: if assigned, show avatar or initials. If unassigned, show an "unclaimed" indicator.
- Wait time: relative time since submission (e.g., "2d 4h ago"), not raw datetime. Color or icon should escalate visually as age increases (e.g., > 24h = warning, > 48h = danger).

**Queue item visual hierarchy (most prominent → least):**
1. Risk level badge (color draws the eye first)
2. Title
3. Wait time
4. Status + assignee
5. Customer tier

**Grouping (optional but recommended):**
Consider visual group separators by risk level ("High Risk", "Medium Risk", "Low Risk" section headers) since the queue is already sorted this way. This gives the reviewer spatial anchors when scrolling.

**Queue header:**
- Show count: "9 items" or segmented "4 unassigned · 5 in review"
- Optional: filter/toggle to show "My items" vs "All active"

**Selected state:**
- Clear left-border accent or background change
- Smooth transition, not a jarring repaint

**Empty state:**
- When queue is empty: illustration or icon + "All caught up — no items need review"
- Tone: calm, positive. This is a good state.

### 4.2 Detail Panel (Right Panel)

**Goal:** Give the reviewer everything they need to decide, then make acting frictionless.

**Information hierarchy (top to bottom):**

1. **Header row:** Item ID (muted), Title (large, bold), Status pill (colored)
2. **Urgency strip:** A horizontal bar or card showing risk level + customer tier + wait time in a single scannable row. This is the "should I care?" zone. Consider using a colored left border or background tint that matches the risk level.
3. **Summary:** The most important text block. Should be visually prominent — larger font or distinct background. This is what the reviewer reads to make a decision.
4. **Metadata grid:** Submitted date, assignee, notes count. Secondary importance — useful but not decision-driving.
5. **Notes section:** Currently just a count. Future: expandable list of notes with timestamps and authors. For now, display the count with an icon and label that implies clickability ("3 notes" with a chat icon).
6. **Actions:** Pinned to the bottom of the panel or in a sticky footer so they're always visible without scrolling.

**Action buttons — design rules:**

| Action | Visual treatment | Behavior |
|--------|-----------------|----------|
| Claim | Primary button (filled, blue/brand color) | Immediate — no confirmation needed |
| Approve | Success button (filled, green) | Show confirmation dialog: "Approve [title]? This cannot be undone." |
| Reject | Danger button (outlined, red) | Show confirmation dialog with required reason field (future: reason is stored) |
| Escalate | Warning button (outlined, amber) | Show confirmation dialog: "Escalate to senior review?" |

**Why confirmation on terminal actions:** Approve/reject/escalate are irreversible. A mis-click on "Reject" when you meant "Approve" is a real ops risk. Claim is reversible (the item can be unclaimed in a future version), so no confirmation needed.

**Action button states:**
- Default: styled per table above
- Hover: slightly elevated or darkened
- Loading/pending: show spinner, disable all buttons, mute text to "Approving..."
- Success: brief green flash or checkmark animation before the item transitions out
- Error: red inline message below the buttons with the specific error text from the backend

### 4.3 Feedback & Transitions

**After a successful action:**
- **Claim:** Item updates in-place in the queue list (status changes, assignee appears). Detail panel refreshes. Subtle success indicator (green checkmark toast or inline flash) that auto-dismisses in 2 seconds.
- **Approve/Reject/Escalate:** Item animates out of the queue list (slide-left or fade-out, 200ms). The next item auto-selects. A toast notification confirms: "RV-1024 approved" with an undo option (stretch goal — backend doesn't support undo yet, but the UI pattern should anticipate it).

**After an error:**
- Inline error banner below the action buttons (not a generic page-level banner). Includes the specific error message from the backend. Dismisses on next action attempt.

**Loading states:**
- Initial load: skeleton cards in the queue list (not a generic "Loading..." text)
- Action pending: button shows spinner, rest of UI remains interactive (reviewer can read other items while waiting)

### 4.4 Header & Navigation

**Top bar:**
- App name/logo: "Reviewer Queue" or product brand
- Signed-in reviewer: name + avatar/initials, right-aligned
- Optional: notification badge if new items have arrived since last load

**No navigation menu needed** — this is a single-view tool. If future views are added (history, settings, team dashboard), add a minimal left sidebar or top tab bar at that point.

### 4.5 Color System

Use semantic colors consistently across the app:

| Token | Usage | Suggested value |
|-------|-------|-----------------|
| `--risk-high` | High risk badge bg | `#FEE2E2` |
| `--risk-high-text` | High risk badge text | `#991B1B` |
| `--risk-medium` | Medium risk badge bg | `#FEF3C7` |
| `--risk-medium-text` | Medium risk badge text | `#92400E` |
| `--risk-low` | Low risk badge bg | `#D1FAE5` |
| `--risk-low-text` | Low risk badge text | `#065F46` |
| `--status-unassigned` | Unassigned pill bg | `#E5E7EB` |
| `--status-in-review` | In-review pill bg | `#DBEAFE` |
| `--status-in-review-text` | In-review pill text | `#1E40AF` |
| `--status-approved` | Approved pill bg | `#D1FAE5` |
| `--status-approved-text` | Approved pill text | `#065F46` |
| `--status-rejected` | Rejected pill bg | `#FEE2E2` |
| `--status-rejected-text` | Rejected pill text | `#991B1B` |
| `--status-escalated` | Escalated pill bg | `#FEF3C7` |
| `--status-escalated-text` | Escalated pill text | `#92400E` |
| `--surface` | Card/panel background | `#FFFFFF` |
| `--surface-secondary` | Page background | `#F9FAFB` |
| `--border` | Default borders | `#E5E7EB` |
| `--text-primary` | Primary text | `#111827` |
| `--text-secondary` | Secondary/muted text | `#6B7280` |
| `--brand` | Primary action color | `#2563EB` |
| `--success` | Approve/success | `#059669` |
| `--danger` | Reject/error | `#DC2626` |
| `--warning` | Escalate/caution | `#D97706` |

### 4.6 Typography

- Font: Inter (already in use) — good choice for data-dense UI
- Queue item title: 14px, 600 weight
- Queue item meta: 12px, 400 weight
- Detail title: 22px, 700 weight
- Detail summary: 15px, 400 weight, 1.6 line height
- Labels/eyebrows: 11px, 700 weight, uppercase, letter-spacing 0.05em
- Monospace for IDs: "RV-1024" should feel like a reference code — use `font-variant-numeric: tabular-nums` or a mono font

### 4.7 Spacing & Layout

- Queue panel width: 340–380px (fixed)
- Detail panel: fluid, min 480px
- Card padding: 16px
- Section spacing: 24px
- Max content width: 1200px, centered
- Border radius: 8px for cards, 4px for badges, 999px for pills

---

## 5. Interaction Patterns

### 5.1 Keyboard shortcuts (stretch goal)

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate queue items |
| `Enter` | Select focused item |
| `C` | Claim selected item |
| `A` | Approve (opens confirmation) |
| `R` | Reject (opens confirmation) |
| `E` | Escalate (opens confirmation) |
| `Esc` | Dismiss dialog/error |

Show a small "?" icon in the header that reveals a shortcut cheat sheet on hover or click.

### 5.2 Confirmation dialogs

For terminal actions (approve/reject/escalate):
- Modal overlay with backdrop blur
- Clear action title: "Approve this item?"
- Item title repeated for context
- Two buttons: "Cancel" (secondary) and "Confirm [Action]" (styled per action type)
- For reject: include an optional "Reason" text field (for future use — can be stored as a note)
- Escape or backdrop click dismisses

### 5.3 Toast notifications

- Position: bottom-right or top-right
- Auto-dismiss after 3 seconds
- Format: "[Action icon] RV-1024 [action past tense]" (e.g., "RV-1024 approved")
- Include "Undo" link (disabled until backend supports it — show as grayed out with tooltip "Undo coming soon")

---

## 6. Responsive Behavior

### Desktop (>1024px)
Two-panel layout as described. Queue list + detail panel side by side.

### Tablet (768–1024px)
- Narrow the queue panel to 280px
- Collapse metadata grid to single column

### Mobile (<768px)
- Single-panel mode: queue list is the default view
- Tapping an item navigates to a full-screen detail view
- Back button returns to queue
- Action buttons become a sticky bottom bar

---

## 7. Accessibility Requirements

- All interactive elements must be keyboard-focusable with visible focus rings
- Risk badges and status pills must not rely on color alone — include text labels
- Action buttons must have `aria-label` attributes that include the item context (e.g., `aria-label="Approve RV-1024: Wire transfer limit increase"`)
- Error messages must be announced by screen readers (`role="alert"`)
- Queue list should use `role="listbox"` with `role="option"` for items
- Confirmation dialogs must trap focus and return focus to the trigger button on dismiss
- Color contrast: all text/background combinations must meet WCAG AA (4.5:1 for normal text, 3:1 for large text)
- Toast notifications must not be the only feedback channel — the UI state change itself must be sufficient

---

## 8. Future Considerations (Do Not Build Now)

These should inform design decisions (don't paint yourself into a corner) but are **not in scope**:

- **Notes panel:** Expandable section showing note history with timestamps and authors. The `notes_count` field is a placeholder for this.
- **Reviewer assignment:** Ability to assign items to specific reviewers instead of self-claim only.
- **Bulk actions:** Select multiple items and approve/reject/escalate in batch.
- **History view:** A "Completed" tab showing terminal items with filters by date, reviewer, and action.
- **Real-time updates:** WebSocket-driven live queue updates when another reviewer claims or resolves an item.
- **SLA indicators:** Visual timer showing "must be resolved within X hours" per item, based on risk level and customer tier.
- **Team dashboard:** Aggregate view showing items per reviewer, average resolution time, backlog trends.

---

## 9. Deliverables Expected from Designer

1. **Queue item card** — component design for all states (unassigned, in_review, selected, hover)
2. **Detail panel** — layout with information hierarchy for unassigned and in_review items
3. **Action button set** — styles for claim, approve, reject, escalate in all states (default, hover, loading, disabled)
4. **Confirmation dialog** — for terminal actions
5. **Toast notification** — success and error variants
6. **Empty state** — queue cleared illustration
7. **Loading state** — skeleton screen for queue list
8. **Color and spacing tokens** — finalized from the suggestions in Section 4.5–4.7
9. **Responsive breakpoints** — tablet and mobile adaptations of queue and detail views

Pixel-perfect mockups are not needed. Component-level designs with clear spacing, color, and typography specs are sufficient for engineering to implement.
