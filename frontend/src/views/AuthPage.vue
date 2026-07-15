<template>
  <div class="auth-grid">
    <div class="intro-panel">
      <p class="text-uppercase small fw-semibold text-primary mb-2">Institute recruitment workspace</p>
      <h1 class="display-5 fw-bold">Manage companies, drives, applications, and placements in one place.</h1>
      <div class="row g-3">
        <div class="col-sm-4"><div class="metric-tile"><strong>Admin</strong><span>Approvals and reports</span></div></div>
        <div class="col-sm-4"><div class="metric-tile"><strong>Company</strong><span>Drives and applicants</span></div></div>
        <div class="col-sm-4"><div class="metric-tile"><strong>Student</strong><span>Search, apply, track</span></div></div>
      </div>
    </div>

    <div class="card shadow-sm">
      <div class="card-body p-4">
        <div class="btn-group w-100 mb-3" role="group">
          <button class="btn" :class="store.authMode === 'login' ? 'btn-dark' : 'btn-outline-dark'" @click="store.authMode = 'login'">Login</button>
          <button class="btn" :class="store.authMode === 'student' ? 'btn-dark' : 'btn-outline-dark'" @click="store.authMode = 'student'">Student</button>
          <button class="btn" :class="store.authMode === 'company' ? 'btn-dark' : 'btn-outline-dark'" @click="store.authMode = 'company'">Company</button>
        </div>

        <form v-if="store.authMode === 'login'" @submit.prevent="doLogin">
          <label class="form-label">Email</label>
          <input v-model="store.loginForm.email" class="form-control mb-3" type="email" required />
          <label class="form-label">Password</label>
          <input v-model="store.loginForm.password" class="form-control mb-3" type="password" required minlength="6" />
          <button class="btn btn-primary w-100" type="submit">Login</button>
        </form>

        <form v-else-if="store.authMode === 'student'" class="row g-3" @submit.prevent="registerStudent">
          <div class="col-md-6"><input v-model="store.studentForm.name" class="form-control" placeholder="Full name" required /></div>
          <div class="col-md-6"><input v-model="store.studentForm.email" class="form-control" type="email" placeholder="Email" required /></div>
          <div class="col-md-6"><input v-model="store.studentForm.password" class="form-control" type="password" placeholder="Password" required minlength="6" /></div>
          <div class="col-md-6"><input v-model="store.studentForm.phone" class="form-control" placeholder="Phone" /></div>
          <div class="col-md-6"><input v-model="store.studentForm.college" class="form-control" placeholder="College" /></div>
          <div class="col-md-6"><input v-model="store.studentForm.degree" class="form-control" placeholder="Degree" /></div>
          <div class="col-md-6"><input v-model="store.studentForm.branch" class="form-control" placeholder="Branch" /></div>
          <div class="col-md-3"><input v-model="store.studentForm.cgpa" class="form-control" type="number" min="0" max="10" step="0.01" placeholder="CGPA" /></div>
          <div class="col-md-3"><input v-model="store.studentForm.passing_year" class="form-control" type="number" min="1950" max="2100" placeholder="Year" /></div>
          <div class="col-12"><input v-model="store.studentForm.skills" class="form-control" placeholder="Skills" /></div>
          <div class="col-12"><button class="btn btn-primary w-100" type="submit">Create Student Account</button></div>
        </form>

        <form v-else class="row g-3" @submit.prevent="registerCompany">
          <div class="col-md-6"><input v-model="store.companyForm.name" class="form-control" placeholder="HR name" required /></div>
          <div class="col-md-6"><input v-model="store.companyForm.email" class="form-control" type="email" placeholder="Login email" required /></div>
          <div class="col-md-6"><input v-model="store.companyForm.password" class="form-control" type="password" placeholder="Password" required minlength="6" /></div>
          <div class="col-md-6"><input v-model="store.companyForm.company_name" class="form-control" placeholder="Company name" required /></div>
          <div class="col-md-6"><input v-model="store.companyForm.industry" class="form-control" placeholder="Industry" /></div>
          <div class="col-md-6"><input v-model="store.companyForm.location" class="form-control" placeholder="Location" /></div>
          <div class="col-md-6"><input v-model="store.companyForm.hr_contact" class="form-control" placeholder="HR contact" /></div>
          <div class="col-md-6"><input v-model="store.companyForm.contact_email" class="form-control" type="email" placeholder="Contact email" /></div>
          <div class="col-12"><textarea v-model="store.companyForm.description" class="form-control" rows="3" placeholder="Company description"></textarea></div>
          <div class="col-12"><button class="btn btn-primary w-100" type="submit">Register Company</button></div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePpaStore } from '../stores/ppa'

const store = usePpaStore()
const router = useRouter()

async function doLogin() {
  await store.login()
  if (store.user?.role) {
    await store.loadDashboard()
    router.push(`/${store.user.role}`)
  }
}

async function registerStudent() {
  await store.registerStudent()
  await store.loadDashboard()
  router.push('/student')
}

async function registerCompany() {
  await store.registerCompany()
  await store.loadDashboard()
  router.push('/company')
}

onMounted(() => {
  if (store.isLoggedIn && store.user?.role) {
    router.push(`/${store.user.role}`)
  }
})
</script>

<style scoped>
.auth-grid {
  width: min(1120px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  align-items: start;
  min-height: calc(100vh - 6rem);
  padding: 2rem 0;
}

@media (min-width: 992px) {
  .auth-grid {
    grid-template-columns: 1.1fr 0.9fr;
  }
}

.intro-panel {
  padding: 2rem;
  border-radius: 1rem;
  background: #ffffff;
  box-shadow: 0 0.75rem 1.5rem rgba(15, 23, 42, 0.08);
}

.metric-tile {
  border-radius: 1rem;
  background: #f8f9fa;
  padding: 1rem 1.15rem;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.35rem;
}

.metric-tile strong {
  display: block;
  font-size: 1rem;
}

.metric-tile span {
  color: #6c757d;
  font-size: 0.92rem;
}

.card.shadow-sm {
  overflow: visible;
}

.card-body {
  min-height: 480px;
}
</style>
