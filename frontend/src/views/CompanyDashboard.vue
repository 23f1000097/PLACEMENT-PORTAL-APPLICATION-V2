<template>
  <div>
    <div class="section-head">
      <div>
        <p class="text-uppercase small fw-semibold text-primary mb-1">Company dashboard</p>
        <h1 class="h3 mb-0">{{ store.data.profile?.company_name || store.user.name }}</h1>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="badge fs-6" :class="store.data.profile?.approved ? 'text-bg-success' : 'text-bg-warning'">{{ store.data.profile?.approved ? 'Approved' : 'Awaiting admin approval' }}</span>
        <button class="btn btn-outline-dark btn-sm" @click="store.exportCompanyApplications">Export CSV</button>
      </div>
    </div>

    <div v-if="!store.data.profile?.approved" class="alert alert-warning">Your company can update its profile now. Creating placement drives unlocks after admin approval.</div>

    <div class="row g-4">
      <div class="col-lg-5">
        <Panel title="Company Profile">
          <form class="row g-3" @submit.prevent="store.saveCompanyProfile">
            <div class="col-12"><input v-model="store.companyProfile.company_name" class="form-control" placeholder="Company name" required /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.industry" class="form-control" placeholder="Industry" /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.location" class="form-control" placeholder="Location" /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.hr_contact" class="form-control" placeholder="HR contact" /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.contact_email" class="form-control" type="email" placeholder="Contact email" /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.phone" class="form-control" placeholder="Phone" /></div>
            <div class="col-md-6"><input v-model="store.companyProfile.website" class="form-control" placeholder="Website" /></div>
            <div class="col-12"><textarea v-model="store.companyProfile.description" class="form-control" rows="4" placeholder="Description"></textarea></div>
            <div class="col-12"><button class="btn btn-primary" type="submit">Save Profile</button></div>
          </form>
        </Panel>
      </div>

      <div class="col-lg-7">
        <Panel title="Create Placement Drive">
          <form class="row g-3" @submit.prevent="store.createJob">
            <div class="col-md-6"><input v-model="store.jobForm.title" class="form-control" placeholder="Job title" required :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-6"><input v-model="store.jobForm.location" class="form-control" placeholder="Location" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-6"><input v-model="store.jobForm.salary" class="form-control" type="number" min="0" step="0.5" placeholder="Salary / package (LPA)" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-6"><input v-model="store.jobForm.last_date" class="form-control" type="date" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-4"><input v-model="store.jobForm.minimum_cgpa" class="form-control" type="number" min="0" max="10" step="0.1" placeholder="Min CGPA" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-4"><input v-model="store.jobForm.eligibility_branch" class="form-control" placeholder="Eligible branch" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-4"><input v-model="store.jobForm.eligibility_year" class="form-control" type="number" min="1950" max="2100" placeholder="Passing year" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-md-4"><input v-model="store.jobForm.vacancies" class="form-control" type="number" min="1" step="1" placeholder="Vacancies" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-12"><input v-model="store.jobForm.skills_required" class="form-control" placeholder="Skills required" :disabled="!store.data.profile?.approved" /></div>
            <div class="col-12"><textarea v-model="store.jobForm.description" class="form-control" rows="3" placeholder="Job description" required :disabled="!store.data.profile?.approved"></textarea></div>
            <div class="col-12"><button class="btn btn-primary" type="submit" :disabled="!store.data.profile?.approved">Submit for Approval</button></div>
          </form>
        </Panel>
      </div>

      <div class="col-12">
        <Panel title="Applications">
          <ApplicationTable
            :applications="store.data.applications"
            :canEdit="true"
            :drafts="store.statusDrafts"
            @init="store.initDraft"
            @save="store.updateApplicationStatus"
            @upload-offer-letter="store.uploadOfferLetter"
          />
        </Panel>
      </div>

      <div class="col-12">
        <Panel title="My Drives">
          <div class="job-grid">
            <article v-for="job in store.data.jobs" :key="job.id" class="job-card">
              <div class="d-flex justify-content-between gap-3">
                <h2 class="h5">{{ job.title }}</h2>
                <span class="badge align-self-start" :class="job.approved ? 'text-bg-success' : 'text-bg-warning'">{{ job.status }}</span>
              </div>
              <p class="text-secondary">{{ job.description }}</p>
              <div class="small text-secondary">CTC: {{ store.formatPackage(job.salary) }}</div>
              <div class="small text-secondary">Skills: {{ store.shortText(job.skills_required) }}</div>
              <div class="small text-secondary">Deadline: {{ store.shortText(job.last_date) }}</div>
              <button
                v-if="job.approved"
                class="btn btn-sm mt-2"
                :class="job.status === 'Deactivated' ? 'btn-outline-success' : 'btn-outline-danger'"
                @click="store.updateJobStatus(job.id, job.status === 'Deactivated' ? 'Active' : 'Deactivated')"
              >
                {{ job.status === 'Deactivated' ? 'Activate' : 'Deactivate' }}
              </button>
            </article>
          </div>
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

const store = usePpaStore()

onMounted(async () => {
  if (!store.isLoggedIn || store.user?.role !== 'company') return
  await store.loadCompany()
})
</script>
