<script setup>
import { watch, ref } from 'vue'
import { usePpaStore } from '../stores/ppa'

const store = usePpaStore()
const visibleSuccess = ref('')
const visibleError = ref('')
let successTimer = null
let errorTimer = null

watch(() => store.message, (value) => {
  if (!value) return
  visibleSuccess.value = value
  clearTimeout(successTimer)
  successTimer = setTimeout(() => {
    visibleSuccess.value = ''
    store.message = ''
  }, 3500)
})

watch(() => store.error, (value) => {
  if (!value) return
  visibleError.value = value
  clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    visibleError.value = ''
    store.error = ''
  }, 5000)
})

function dismissSuccess() {
  visibleSuccess.value = ''
  store.message = ''
  clearTimeout(successTimer)
}

function dismissError() {
  visibleError.value = ''
  store.error = ''
  clearTimeout(errorTimer)
}
</script>

<template>
  <div class="toast-stack">
    <div v-if="visibleSuccess" class="toast-item alert alert-success shadow-sm mb-2" role="status">
      <span>{{ visibleSuccess }}</span>
      <button type="button" class="btn-close" @click="dismissSuccess"></button>
    </div>
    <div v-if="visibleError" class="toast-item alert alert-danger shadow-sm mb-2" role="alert">
      <span>{{ visibleError }}</span>
      <button type="button" class="btn-close" @click="dismissError"></button>
    </div>
  </div>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 1080;
  max-width: 360px;
}

.toast-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
</style>
