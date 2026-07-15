<script setup>
import { usePpaStore } from '../stores/ppa'

const store = usePpaStore()

function confirm() {
  store.resolveConfirm(true)
}

function cancel() {
  store.resolveConfirm(false)
}
</script>

<template>
  <div v-if="store.confirmState.open" class="confirm-backdrop" @click.self="cancel">
    <div class="confirm-dialog card shadow">
      <div class="card-body">
        <p class="mb-4">{{ store.confirmState.message }}</p>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary btn-sm" @click="cancel">Cancel</button>
          <button type="button" class="btn btn-danger btn-sm" @click="confirm">Confirm</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1090;
}

.confirm-dialog {
  width: min(90vw, 420px);
}
</style>
