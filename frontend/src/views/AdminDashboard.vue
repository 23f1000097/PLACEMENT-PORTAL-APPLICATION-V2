<template>
  <div>
    <div class="section-head">
      <div>
        <p class="text-uppercase small fw-semibold text-primary mb-1">Admin dashboard</p>
        <h1 class="h3 mb-0">Institute placement control center</h1>
      </div>
      <div class="d-flex gap-2 flex-wrap">
        <input v-model="store.filters.q" class="form-control" placeholder="Search students, companies, drives" />
        <select v-model="store.filters.approved" class="form-select">
          <option value="">All approvals</option>
          <option value="true">Approved</option>
          <option value="false">Pending/Rejected</option>
        </select>
        <button class="btn btn-primary" @click="store.loadAdmin">Search</button>
        <button class="btn btn-outline-dark" @click="store.generateMonthlyReport('html')">HTML Report</button>
        <button class="btn btn-outline-dark" @click="store.generateMonthlyReport('pdf')">PDF Report</button>
      </div>
    </div>

    <div class="stats-grid mb-4">
      <div v-for="(value, key) in store.data.stats" :key="key" class="metric-tile">
        <strong>{{ value }}</strong>
        <span>{{ key.replaceAll('_', ' ') }}</span>
      </div>
    </div>

    <DashboardCharts :trend="store.data.analytics.trend" :funnel="store.data.analytics.funnel" />

    <div class="row g-4">
      <div class="col-xl-6">
        <Panel title="Companies">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr><th>Company</th><th>Industry</th><th>Status</th><th></th></tr></thead>
              <tbody>
                <tr v-for="company in store.data.companies" :key="company.id">
                  <td><strong>{{ company.company_name }}</strong><br /><span class="text-secondary">{{ company.location }}</span></td>
                  <td>{{ store.shortText(company.industry) }}</td>
                  <td><span class="badge" :class="company.approved ? 'text-bg-success' : 'text-bg-warning'">{{ company.approved ? 'Approved' : 'Pending' }}</span></td>
                  <td class="text-end">
                    <template v-if="company.approved !== true">
                    <button class="btn btn-sm btn-outline-success me-1" @click="store.approveCompany(company.id, true)">Approve</button>
                    <button class="btn btn-sm btn-outline-danger me-1" @click="store.approveCompany(company.id, false)">Reject</button>
                  </template>
                    <button class="btn btn-sm" :class="company.is_active ? 'btn-outline-danger' : 'btn-outline-success'" @click="store.updateUserStatus(company.user_id, !company.is_active)">
                      {{ company.is_active ? 'Deactivate' : 'Activate' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div class="col-xl-6">
        <Panel title="Placement Drives">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr><th>Drive</th><th>Eligibility</th><th>Status</th><th></th></tr></thead>
              <tbody>
                <tr v-for="job in store.data.jobs" :key="job.id">
                  <td><strong>{{ job.title }}</strong><br /><span class="text-secondary">{{ job.company_name }}</span></td>
                  <td>{{ store.shortText(job.eligibility_branch, 'Any branch') }} / {{ store.shortText(job.minimum_cgpa, 'Any CGPA') }}</td>
                  <td><span class="badge" :class="job.approved ? 'text-bg-success' : 'text-bg-warning'">{{ job.status }}</span></td>
                  <td class="text-end">
                    <template v-if="job.status === 'Pending' || job.approved !== true">
                      <button class="btn btn-sm btn-outline-success me-1" @click="store.approveJob(job.id, true)">Approve</button>
                      <button class="btn btn-sm btn-outline-danger me-1" @click="store.approveJob(job.id, false)">Reject</button>
                    </template>
                    <button class="btn btn-sm btn-outline-dark" @click="confirmDeleteJob(job)">Remove</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div class="col-xl-6">
        <Panel title="Students">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr><th>Name</th><th>Branch</th><th>CGPA</th><th></th></tr></thead>
              <tbody>
                <tr v-for="student in store.data.students" :key="student.id">
                  <td><strong>{{ student.name }}</strong><br /><span class="text-secondary">{{ student.email }}</span></td>
                  <td>{{ store.shortText(student.branch) }}</td>
                  <td>{{ store.shortText(student.cgpa) }}</td>
                  <td class="text-end">
                    <button class="btn btn-sm" :class="student.is_active ? 'btn-outline-danger' : 'btn-outline-success'" @click="store.updateUserStatus(student.user_id, !student.is_active)">
                      {{ student.is_active ? 'Deactivate' : 'Activate' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div class="col-xl-6">
        <Panel title="Applications">
          <ApplicationTable :applications="store.data.applications" :canEdit="true" :drafts="store.statusDrafts" @init="store.initDraft" @save="store.updateApplicationStatus" />
        </Panel>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { usePpaStore } from '../stores/ppa'
import Panel from '../components/Panel.vue'
import ApplicationTable from '../components/ApplicationTable.vue'
import DashboardCharts from '../components/DashboardCharts.vue'

const store = usePpaStore()

async function confirmDeleteJob(job) {
  const confirmed = await store.confirmAction(`Remove the placement drive "${job.title}"? This also removes its applications.`)
  if (confirmed) {
    store.deleteJob(job.id)
  }
}

onMounted(async () => {
  if (!store.isLoggedIn || store.user?.role !== 'admin') return
  await store.loadAdmin()
})
</script>
