<script setup>
import { usePpaStore } from './stores/ppa'
import { useRouter } from 'vue-router'
import Toast from './components/Toast.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'

const store = usePpaStore()
const router = useRouter()

function logout() {
  store.logout()
  router.push('/')
}

function refreshPage() {
  router.go(0)
}
</script>

<template>
  <div class="app-shell">
    <nav class="navbar navbar-expand-lg bg-white border-bottom sticky-top">
      <div class="container-fluid px-3 px-lg-4">
        <router-link class="navbar-brand fw-bold" to="/">Placement Portal</router-link>

        <div class="d-flex align-items-center gap-2">
          <span class="badge text-bg-light border">{{ store.user?.role?.toUpperCase() || 'GUEST' }}</span>
          <button v-if="store.isLoggedIn" class="btn btn-outline-secondary btn-sm" @click="refreshPage">Refresh</button>
          <button v-if="store.isLoggedIn" class="btn btn-dark btn-sm" @click="logout">Logout</button>
        </div>
      </div>
    </nav>

    <main class="container-fluid px-3 px-lg-4 py-4">
      <div v-if="store.loading" class="progress mb-3" role="progressbar" aria-label="Loading">
        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
      </div>

      <router-view />
    </main>

    <Toast />
    <ConfirmDialog />
  </div>
</template>

<style>
body {
  background: #f5f7fb;
  color: #172033;
}

.app-shell {
  min-height: 100vh;
}

.navbar-brand {
  text-decoration: none;
}
</style>
