<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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
const pendingAction = ref<ReviewAction | null>(null);

const selectedItem = computed(() =>
  items.value.find((item) => item.id === selectedId.value) ?? items.value[0] ?? null
);

const TERMINAL_STATUSES = new Set(["approved", "rejected", "escalated"]);

const allowedActions = computed<ReviewAction[]>(() => {
  if (!selectedItem.value) return [];
  const status = selectedItem.value.status;
  if (status === "unassigned") return ["claim"];
  if (status === "in_review") return ["approve", "reject", "escalate"];
  return [];
});

async function loadItems() {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    items.value = await fetchReviewItems();
    selectedId.value = selectedItem.value?.id ?? null;
  } catch (error) {
    errorMessage.value = "Something went wrong loading the queue.";
  } finally {
    isLoading.value = false;
  }
}

async function performAction(action: ReviewAction) {
  if (!selectedItem.value) return;

  pendingAction.value = action;
  errorMessage.value = null;

  try {
    const updated = await applyReviewAction(selectedItem.value.id, action, currentReviewer);
    if (TERMINAL_STATUSES.has(updated.status)) {
      items.value = items.value.filter((item) => item.id !== updated.id);
      selectedId.value = items.value[0]?.id ?? null;
    } else {
      items.value = items.value.map((item) => (item.id === updated.id ? updated : item));
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "That action could not be completed.";
  } finally {
    pendingAction.value = null;
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

onMounted(loadItems);
</script>

<template>
  <main class="page-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Reviewer workspace</p>
        <h1>Active queue</h1>
      </div>
      <div class="reviewer">Signed in as {{ currentReviewer }}</div>
    </header>

    <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>
    <p v-if="isLoading" class="loading">Loading review items...</p>

    <section v-else class="workspace">
      <aside class="queue-list" aria-label="Review queue">
        <button
          v-for="item in items"
          :key="item.id"
          class="queue-item"
          :class="{ selected: item.id === selectedItem?.id }"
          type="button"
          @click="selectedId = item.id"
        >
          <span class="queue-title">{{ item.title }}</span>
          <span class="queue-meta">
            <span :class="['risk-badge', `risk-${item.risk_level}`]">{{ item.risk_level }}</span>
            risk · {{ item.customer_tier }}
          </span>
          <span class="queue-meta">{{ item.status }} · {{ item.assigned_reviewer ?? "unassigned" }}</span>
        </button>
      </aside>

      <section v-if="selectedItem" class="detail-panel">
        <div class="detail-header">
          <div>
            <p class="eyebrow">{{ selectedItem.id }}</p>
            <h2>{{ selectedItem.title }}</h2>
          </div>
          <span :class="['status-pill', `status-${selectedItem.status}`]">{{ selectedItem.status }}</span>
        </div>

        <dl class="facts">
          <div>
            <dt>Submitted</dt>
            <dd>{{ formatDate(selectedItem.submitted_at) }}</dd>
          </div>
          <div>
            <dt>Risk</dt>
            <dd>{{ selectedItem.risk_level }}</dd>
          </div>
          <div>
            <dt>Customer</dt>
            <dd>{{ selectedItem.customer_tier }}</dd>
          </div>
          <div>
            <dt>Assignee</dt>
            <dd>{{ selectedItem.assigned_reviewer ?? "None" }}</dd>
          </div>
        </dl>

        <p class="summary">{{ selectedItem.summary }}</p>
        <p class="notes">{{ selectedItem.notes_count }} notes on this item</p>

        <div v-if="allowedActions.length > 0" class="actions" aria-label="Workflow actions">
          <button
            v-for="action in allowedActions"
            :key="action"
            type="button"
            :disabled="Boolean(pendingAction)"
            @click="performAction(action)"
          >
            {{ action.charAt(0).toUpperCase() + action.slice(1) }}
          </button>
        </div>
        <p v-else class="terminal-notice">No actions available — this item is {{ selectedItem.status }}.</p>
      </section>
    </section>
  </main>
</template>
