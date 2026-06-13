<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  applyReviewAction,
  fetchReviewItems,
  type ReviewAction,
  type ReviewItem
} from "./api";

const currentReviewer = "alex";
const items = ref<ReviewItem[]>([]);
const selectedId = ref<string | null>(null);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const pendingAction = ref<{ action: ReviewAction; id: string } | null>(null);
const filter = ref<"all" | "mine">("all");
const showHelp = ref(false);

// Modal state
const modal = ref<{ action: ReviewAction; id: string } | null>(null);
const modalReason = ref("");

// Toast state
const toast = ref<{ text: string; accent: string } | null>(null);
let toastTimer: ReturnType<typeof setTimeout> | null = null;

const TERMINAL_STATUSES = new Set(["approved", "rejected", "escalated"]);

const RISK_META: Record<string, { bg: string; text: string; accent: string; label: string; order: number; group: string }> = {
  high:   { bg: "#FEE2E2", text: "#991B1B", accent: "#DC2626", label: "High",   order: 0, group: "High risk" },
  medium: { bg: "#FEF3C7", text: "#92400E", accent: "#D97706", label: "Medium", order: 1, group: "Medium risk" },
  low:    { bg: "#D1FAE5", text: "#065F46", accent: "#059669", label: "Low",    order: 2, group: "Low risk" },
};

const STATUS_META: Record<string, { bg: string; text: string; label: string }> = {
  unassigned: { bg: "#E5E7EB", text: "#374151", label: "Unassigned" },
  in_review:  { bg: "#DBEAFE", text: "#1E40AF", label: "In review" },
};

const SHORTCUTS = [
  { label: "Navigate items", key: "↑ ↓" },
  { label: "Claim selected", key: "C" },
  { label: "Approve", key: "A" },
  { label: "Reject", key: "R" },
  { label: "Escalate", key: "E" },
  { label: "Dismiss", key: "Esc" },
];

const MODAL_CONFIG: Record<string, { eyebrow: string; accent: string; title: string; body: string; confirm: string }> = {
  approve:  { eyebrow: "Approve",  accent: "#059669", title: "Approve this item?",          body: "This action is final and cannot be undone.",                                                           confirm: "Approve" },
  reject:   { eyebrow: "Reject",   accent: "#DC2626", title: "Reject this item?",           body: "This action is final and cannot be undone. You can add a reason for the record.",                       confirm: "Reject" },
  escalate: { eyebrow: "Escalate", accent: "#D97706", title: "Escalate to senior review?",   body: "This sends the item to the senior review queue and removes it from yours.",                             confirm: "Escalate" },
};

// Computed: visible items based on filter
const visibleItems = computed(() => {
  if (filter.value === "mine") {
    return items.value.filter(i => i.assigned_reviewer === currentReviewer);
  }
  return items.value;
});

// Computed: effective selected id
const effectiveId = computed(() => {
  const v = visibleItems.value;
  if (v.some(i => i.id === selectedId.value)) return selectedId.value;
  return v[0]?.id ?? null;
});

const selectedItem = computed(() =>
  items.value.find(i => i.id === effectiveId.value) ?? null
);

// Computed: groups for queue
const groups = computed(() => {
  const result: { label: string; dot: string; count: string; items: ReviewItem[] }[] = [];
  for (const key of ["high", "medium", "low"] as const) {
    const list = visibleItems.value.filter(i => i.risk_level === key);
    if (!list.length) continue;
    const r = RISK_META[key];
    result.push({
      label: r.group,
      dot: r.accent,
      count: list.length + (list.length === 1 ? " item" : " items"),
      items: list,
    });
  }
  return result;
});

// Computed: counts
const counts = computed(() => {
  const v = visibleItems.value;
  const unc = v.filter(i => i.status === "unassigned").length;
  const inr = v.length - unc;
  return {
    total: v.length + (v.length === 1 ? " item" : " items"),
    breakdown: unc + " unassigned · " + inr + " in review",
  };
});

// Computed: allowed actions for selected item
const allowedActions = computed<ReviewAction[]>(() => {
  if (!selectedItem.value) return [];
  const status = selectedItem.value.status;
  if (status === "unassigned") return ["claim"];
  if (status === "in_review") return ["approve", "reject", "escalate"];
  return [];
});

// Helpers
function waitText(submittedAt: string): string {
  const now = Date.now();
  const then = new Date(submittedAt).getTime();
  const hours = Math.max(0, Math.floor((now - then) / 3600000));
  const d = Math.floor(hours / 24);
  const h = hours % 24;
  return (d > 0 ? d + "d " + h + "h" : h + "h") + " ago";
}

function waitColor(submittedAt: string): string {
  const hours = Math.max(0, Math.floor((Date.now() - new Date(submittedAt).getTime()) / 3600000));
  return hours > 48 ? "#DC2626" : hours > 24 ? "#D97706" : "#6B7280";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function initials(name: string): string {
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

// Actions
async function loadItems() {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    items.value = await fetchReviewItems();
    selectedId.value = effectiveId.value;
  } catch {
    errorMessage.value = "Something went wrong loading the queue.";
  } finally {
    isLoading.value = false;
  }
}

function openModal(action: ReviewAction, id: string) {
  modal.value = { action, id };
  modalReason.value = "";
}

function closeModal() {
  modal.value = null;
}

function confirmModal() {
  if (!modal.value) return;
  const { action, id } = modal.value;
  modal.value = null;
  startAction(action, id);
}

function showToast(text: string, accent: string) {
  toast.value = { text, accent };
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.value = null; }, 3200);
}

async function startAction(action: ReviewAction, id: string) {
  if (pendingAction.value) return;
  pendingAction.value = { action, id };
  errorMessage.value = null;

  try {
    const updated = await applyReviewAction(id, action, currentReviewer);
    if (TERMINAL_STATUSES.has(updated.status)) {
      const idx = visibleItems.value.findIndex(i => i.id === id);
      items.value = items.value.filter(i => i.id !== updated.id);
      const newVisible = filter.value === "mine"
        ? items.value.filter(i => i.assigned_reviewer === currentReviewer)
        : items.value;
      const next = newVisible[Math.min(idx, newVisible.length - 1)];
      selectedId.value = next?.id ?? null;
      const past: Record<string, string> = { approve: "approved", reject: "rejected", escalate: "escalated" };
      showToast(id + " " + past[action], action === "approve" ? "#059669" : action === "reject" ? "#DC2626" : "#D97706");
    } else {
      items.value = items.value.map(i => i.id === updated.id ? updated : i);
      showToast(id + " claimed", "#2563EB");
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "That action could not be completed.";
  } finally {
    pendingAction.value = null;
  }
}

function handleAction(action: ReviewAction) {
  if (!selectedItem.value) return;
  if (action === "claim") {
    startAction(action, selectedItem.value.id);
  } else {
    openModal(action, selectedItem.value.id);
  }
}

// Keyboard shortcuts
function onKeyDown(e: KeyboardEvent) {
  if (modal.value) {
    if (e.key === "Escape") closeModal();
    return;
  }
  const t = e.target as HTMLElement;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;

  const v = visibleItems.value;
  if (!v.length) return;
  const eff = effectiveId.value;
  const idx = Math.max(0, v.findIndex(i => i.id === eff));

  if (e.key === "ArrowDown") { e.preventDefault(); selectedId.value = v[Math.min(idx + 1, v.length - 1)].id; return; }
  if (e.key === "ArrowUp") { e.preventDefault(); selectedId.value = v[Math.max(idx - 1, 0)].id; return; }

  const cur = v.find(i => i.id === eff);
  if (!cur) return;
  const k = e.key.toLowerCase();
  if (k === "c" && cur.status === "unassigned") startAction("claim", cur.id);
  if (cur.status === "in_review") {
    if (k === "a") openModal("approve", cur.id);
    if (k === "r") openModal("reject", cur.id);
    if (k === "e") openModal("escalate", cur.id);
  }
  if (e.key === "Escape") showHelp.value = false;
}

onMounted(() => {
  loadItems();
  document.addEventListener("keydown", onKeyDown);
});
onUnmounted(() => {
  document.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <div class="app-shell">
    <!-- Header -->
    <header class="topbar">
      <div class="topbar-brand">
        <div class="topbar-logo">R</div>
        <div style="display:flex;align-items:baseline;gap:7px;">
          <span class="topbar-name">Reviewer</span>
          <span class="topbar-name-sub">Queue</span>
        </div>
      </div>
      <div class="topbar-right">
        <div class="help-wrap">
          <button class="help-btn" aria-label="Keyboard shortcuts" @click="showHelp = !showHelp">?</button>
          <div v-if="showHelp" class="help-panel">
            <div class="help-panel-title">Keyboard shortcuts</div>
            <div v-for="s in SHORTCUTS" :key="s.key" class="help-row">
              <span class="help-row-label">{{ s.label }}</span>
              <span class="help-row-key">{{ s.key }}</span>
            </div>
          </div>
        </div>
        <div class="topbar-divider"></div>
        <div class="topbar-user">
          <span class="topbar-user-name">{{ currentReviewer }}</span>
          <div class="topbar-avatar">{{ initials(currentReviewer) }}</div>
        </div>
      </div>
    </header>

    <p v-if="isLoading" style="padding:20px;text-align:center;color:#6B7280;">Loading review items...</p>

    <main v-else class="workspace">
      <!-- Queue panel -->
      <section class="queue-panel" aria-label="Review queue">
        <div class="queue-header">
          <div class="queue-counts">
            <span class="queue-total">{{ counts.total }}</span>
            <span class="queue-breakdown">{{ counts.breakdown }}</span>
          </div>
          <div class="filter-tabs">
            <button class="filter-tab" :class="{ active: filter === 'all' }" @click="filter = 'all'">All active</button>
            <button class="filter-tab" :class="{ active: filter === 'mine' }" @click="filter = 'mine'">My items</button>
          </div>
        </div>

        <div class="queue-scroll" role="listbox" aria-label="Queue items">
          <div v-for="group in groups" :key="group.label">
            <div class="queue-group-header">
              <span class="queue-group-dot" :style="{ background: group.dot }"></span>
              <span class="queue-group-label">{{ group.label }}</span>
              <span class="queue-group-count">{{ group.count }}</span>
            </div>
            <div class="queue-group-items">
              <div
                v-for="item in group.items"
                :key="item.id"
                role="option"
                tabindex="0"
                class="queue-card"
                :class="{ selected: item.id === effectiveId }"
                :style="{ '--accent': RISK_META[item.risk_level].accent }"
                @click="selectedId = item.id; showHelp = false"
              >
                <div class="queue-card-top">
                  <span class="queue-card-id">{{ item.id }}</span>
                  <span class="queue-card-wait" :style="{ color: waitColor(item.submitted_at) }">{{ waitText(item.submitted_at) }}</span>
                </div>
                <div class="queue-card-badges">
                  <span class="risk-badge" :style="{ background: RISK_META[item.risk_level].bg, color: RISK_META[item.risk_level].text }">
                    <span class="risk-dot" :style="{ background: RISK_META[item.risk_level].accent }"></span>
                    {{ RISK_META[item.risk_level].label }}
                  </span>
                  <span v-if="item.customer_tier === 'priority'" class="tier-badge">Priority</span>
                </div>
                <div class="queue-card-title">{{ item.title }}</div>
                <div class="queue-card-bottom">
                  <span class="status-pill" :style="{ background: STATUS_META[item.status]?.bg ?? '#E5E7EB', color: STATUS_META[item.status]?.text ?? '#374151' }">
                    {{ STATUS_META[item.status]?.label ?? item.status }}
                  </span>
                  <span v-if="item.assigned_reviewer" class="assignee-info">
                    <span class="assignee-name">{{ item.assigned_reviewer }}</span>
                    <span class="assignee-avatar" :style="{ background: item.assigned_reviewer === currentReviewer ? '#2563EB' : '#6B7280' }">{{ initials(item.assigned_reviewer) }}</span>
                  </span>
                  <span v-else class="assignee-info">
                    <span class="unclaimed-label">Unclaimed</span>
                    <span class="unclaimed-circle"></span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Detail panel -->
      <section class="detail-panel" aria-label="Item detail">
        <template v-if="selectedItem">
          <div class="detail-scroll">
            <div class="detail-content">
              <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

              <div class="detail-top">
                <span class="detail-id">{{ selectedItem.id }}</span>
                <span class="detail-status" :style="{ background: STATUS_META[selectedItem.status]?.bg ?? '#E5E7EB', color: STATUS_META[selectedItem.status]?.text ?? '#374151' }">
                  {{ STATUS_META[selectedItem.status]?.label ?? selectedItem.status }}
                </span>
              </div>
              <h1 class="detail-title">{{ selectedItem.title }}</h1>

              <!-- Urgency strip -->
              <div class="urgency-strip" :style="{
                '--accent': RISK_META[selectedItem.risk_level].accent,
                '--urgency-bg': RISK_META[selectedItem.risk_level].bg,
                '--urgency-border': RISK_META[selectedItem.risk_level].accent + '40',
              }">
                <div class="urgency-cell">
                  <div class="urgency-label">Risk</div>
                  <span class="urgency-value urgency-value-risk" :style="{ color: RISK_META[selectedItem.risk_level].text }">
                    <span class="urgency-risk-dot" :style="{ background: RISK_META[selectedItem.risk_level].accent }"></span>
                    {{ RISK_META[selectedItem.risk_level].label }}
                  </span>
                </div>
                <div class="urgency-divider" :style="{ background: RISK_META[selectedItem.risk_level].accent + '40' }"></div>
                <div class="urgency-cell">
                  <div class="urgency-label">Customer</div>
                  <span class="urgency-value" :style="{ color: selectedItem.customer_tier === 'priority' ? '#4338CA' : '#374151' }">
                    {{ selectedItem.customer_tier === 'priority' ? 'Priority' : 'Standard' }}
                  </span>
                </div>
                <div class="urgency-divider" :style="{ background: RISK_META[selectedItem.risk_level].accent + '40' }"></div>
                <div class="urgency-cell">
                  <div class="urgency-label">Waiting</div>
                  <span class="urgency-value" :style="{ color: waitColor(selectedItem.submitted_at) }">
                    {{ waitText(selectedItem.submitted_at) }}
                  </span>
                </div>
              </div>

              <!-- Summary -->
              <div class="summary-label">Summary</div>
              <div class="summary-box">{{ selectedItem.summary }}</div>

              <!-- Metadata grid -->
              <div class="meta-grid">
                <div class="meta-cell">
                  <div class="meta-label">Submitted</div>
                  <div class="meta-value">{{ formatDate(selectedItem.submitted_at) }}</div>
                </div>
                <div class="meta-cell">
                  <div class="meta-label">Assignee</div>
                  <div class="meta-value" :class="{ 'meta-value-muted': !selectedItem.assigned_reviewer }">
                    {{ selectedItem.assigned_reviewer ?? 'Unassigned' }}
                  </div>
                </div>
                <div class="meta-cell">
                  <div class="meta-label">Reference</div>
                  <div class="meta-value meta-value-mono">{{ selectedItem.id }}</div>
                </div>
              </div>

              <!-- Notes -->
              <button class="notes-btn" @click="showToast('Notes panel — coming soon', '#6B7280')">
                <span class="notes-icon"></span>
                <span class="notes-label">{{ selectedItem.notes_count }} {{ selectedItem.notes_count === 1 ? 'note' : 'notes' }} on this item</span>
                <span class="notes-arrow">View &rarr;</span>
              </button>
            </div>
          </div>

          <!-- Action footer -->
          <div class="action-footer">
            <div class="action-footer-inner" :class="{ pending: !!pendingAction }">
              <!-- Claim -->
              <template v-if="allowedActions.includes('claim')">
                <button class="btn-claim" :aria-label="'Claim ' + selectedItem.id" @click="handleAction('claim')">
                  <span v-if="pendingAction?.action === 'claim'" class="spinner"></span>
                  {{ pendingAction?.action === 'claim' ? 'Claiming…' : 'Claim item' }}
                </button>
              </template>
              <!-- Approve/Reject/Escalate -->
              <template v-if="allowedActions.includes('approve')">
                <div class="action-row">
                  <button class="btn-approve" :aria-label="'Approve ' + selectedItem.id" @click="handleAction('approve')">
                    {{ pendingAction?.action === 'approve' ? 'Approving…' : 'Approve' }}
                  </button>
                  <button class="btn-reject" :aria-label="'Reject ' + selectedItem.id" @click="handleAction('reject')">
                    {{ pendingAction?.action === 'reject' ? 'Rejecting…' : 'Reject' }}
                  </button>
                  <button class="btn-escalate" :aria-label="'Escalate ' + selectedItem.id" @click="handleAction('escalate')">
                    {{ pendingAction?.action === 'escalate' ? 'Escalating…' : 'Escalate' }}
                  </button>
                  <span style="flex:1;"></span>
                  <span v-if="pendingAction" class="pending-indicator">
                    <span class="spinner-dark"></span>
                    Working&hellip;
                  </span>
                </div>
              </template>
              <!-- Terminal / no actions -->
              <template v-if="allowedActions.length === 0">
                <p style="color:#6B7280;font-style:italic;margin:0;">No actions available &mdash; this item is {{ selectedItem.status }}.</p>
              </template>
            </div>
          </div>
        </template>

        <!-- Empty state -->
        <div v-else class="empty-state">
          <div class="empty-icon">
            <div class="empty-check"></div>
          </div>
          <template v-if="items.length === 0">
            <div class="empty-title">All caught up</div>
            <div class="empty-sub">No items need review right now. Nice work.</div>
          </template>
          <template v-else>
            <div class="empty-title">Nothing assigned to you</div>
            <div class="empty-sub">Switch to "All active" to see the full queue.</div>
          </template>
        </div>
      </section>
    </main>

    <!-- Confirmation modal -->
    <div v-if="modal" class="modal-overlay" @click="closeModal">
      <div class="modal-dialog" @click.stop>
        <div class="modal-eyebrow">
          <span class="modal-eyebrow-dot" :style="{ background: MODAL_CONFIG[modal.action].accent }"></span>
          <span class="modal-eyebrow-text" :style="{ color: MODAL_CONFIG[modal.action].accent }">{{ MODAL_CONFIG[modal.action].eyebrow }}</span>
        </div>
        <h2 class="modal-title">{{ MODAL_CONFIG[modal.action].title }}</h2>
        <p class="modal-body">{{ MODAL_CONFIG[modal.action].body }}</p>
        <div class="modal-ref">{{ modal.id }} &middot; {{ items.find(i => i.id === modal!.id)?.title }}</div>
        <div v-if="modal.action === 'reject'" style="margin-bottom:18px;">
          <label class="modal-reason-label">Reason <span class="modal-reason-optional">(optional)</span></label>
          <textarea v-model="modalReason" class="modal-textarea" placeholder="Add a note for the record&hellip;"></textarea>
        </div>
        <div class="modal-actions">
          <button class="modal-cancel" @click="closeModal">Cancel</button>
          <button class="modal-confirm" :style="{ background: MODAL_CONFIG[modal.action].accent }" @click="confirmModal">{{ MODAL_CONFIG[modal.action].confirm }}</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast" role="status">
      <span class="toast-icon" :style="{ background: toast.accent }">
        <span class="toast-check"></span>
      </span>
      <span class="toast-text">{{ toast.text }}</span>
      <span class="toast-divider"></span>
      <span class="toast-undo" title="Undo coming soon">Undo</span>
    </div>
  </div>
</template>
