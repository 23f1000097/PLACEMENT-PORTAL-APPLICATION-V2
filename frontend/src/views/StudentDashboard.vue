<template>
  <div>
    <div class="section-head">
      <div>
        <p class="text-uppercase small fw-semibold text-primary mb-1">Student dashboard</p>
        <h1 class="h3 mb-0">Welcome, {{ store.user.name }}</h1>
      </div>
      <div class="d-flex gap-2 flex-wrap">
        <input v-model="store.filters.q" class="form-control" placeholder="Search drives" />
        <button class="btn btn-primary" @click="store.searchDrives">Search</button>
        <button class="btn btn-outline-dark" @click="store.exportApplications">Export CSV</button>
      </div>
    </div>

    <div class="row g-4">
      <div class="col-lg-4">
        <Panel title="Profile">
         

          <form class="row g-3" @submit.prevent="store.saveStudentProfile">
            <div class="col-12">
              <label class="form-label">Full name</label>
              <input v-model="store.studentProfile.name" class="form-control" placeholder="Your first and last name" required />
            </div>
            <div class="col-md-6">
              <label class="form-label">College</label>
              <input v-model="store.studentProfile.college" class="form-control" placeholder="Institute name" />
            </div>
            <div class="col-md-6">
              <label class="form-label">Phone</label>
              <input v-model="store.studentProfile.phone" class="form-control" placeholder="Contact number" />
            </div>
            <div class="col-md-6">
              <label class="form-label">Degree</label>
              <input v-model="store.studentProfile.degree" class="form-control" placeholder="e.g. B.Tech, B.Sc, M.Tech" />
            </div>
            <div class="col-md-6">
              <label class="form-label">Branch / Specialization</label>
              <input v-model="store.studentProfile.branch" class="form-control" placeholder="e.g. Computer Science, DS" />
            </div>
            <div class="col-md-6">
              <label class="form-label">CGPA</label>
              <input v-model="store.studentProfile.cgpa" class="form-control" type="number" min="0" max="10" step="0.01" placeholder="Cumulative grade (e.g. 7.50)" />
              <div class="form-text">Used to determine eligibility for drives.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label">Expected passing year</label>
              <input v-model="store.studentProfile.passing_year" class="form-control" type="number" min="1950" max="2100" placeholder="e.g. 2026" />
              <div class="form-text">Year you expect to graduate.</div>
            </div>
            <div class="col-12">
              <label class="form-label">Skills</label>
              <input v-model="store.studentProfile.skills" class="form-control" placeholder="List your technologies and strengths" />
            </div>
            <div class="col-12">
              <label class="form-label">Experience</label>
              <textarea v-model="store.studentProfile.experience" class="form-control" rows="3" placeholder="Internships, projects, or work experience"></textarea>
              <div class="form-text">Describe relevant projects or internships.</div>
            </div>
            <div class="col-12">
              <label class="form-label">Resume upload</label>
              <input class="form-control" type="file" accept=".pdf,.doc,.docx" @change="onFileChange" />
            </div>
            <div class="col-12"><button class="btn btn-primary" type="submit">Save Profile</button></div>
          </form>
        </Panel>
      </div>

      <div class="col-lg-8">
        <Panel title="Approved Placement Drives">
          <div v-if="!store.data.drives.length" class="text-secondary">No approved placement drives are available right now. Click Refresh to check again.</div>
          <div class="job-grid">
            <article v-for="drive in store.data.drives" :key="drive.id" class="job-card">
              <div class="d-flex justify-content-between gap-3">
                <div>
                  <h2 class="h5">{{ drive.title }}</h2>
                  <p class="mb-1 text-secondary">{{ drive.company_name }} · {{ store.shortText(drive.location) }}</p>
                </div>
                <span v-if="'eligible' in drive" class="badge align-self-start" :class="drive.eligible ? 'text-bg-success' : 'text-bg-danger'">{{ drive.eligible ? 'Eligible' : 'Not eligible' }}</span>
              </div>
              <p>{{ drive.description }}</p>
              <div class="small text-secondary">CTC: {{ store.formatPackage(drive.salary) }}</div>
              <div class="small text-secondary">Skills: {{ store.shortText(drive.skills_required) }}</div>
              <div class="small text-secondary">Minimum CGPA: {{ store.shortText(drive.minimum_cgpa, 'Any') }} · Branch: {{ store.shortText(drive.eligibility_branch, 'Any') }}</div>
              <div class="small text-secondary">Deadline: {{ store.shortText(drive.last_date) }}</div>
              <button class="btn btn-sm btn-primary mt-3" @click="applyDrive(drive.id)">Apply</button>
            </article>
          </div>
        </Panel>
      </div>

      <div class="col-lg-8">
        <Panel title="My Applications">
          <ApplicationTable
            :applications="store.data.applications"
            :canEdit="false"
            :drafts="store.statusDrafts"
            @init="store.initDraft"
            @download-offer-letter="store.downloadOfferLetter"
          />
        </Panel>
      </div>

      <div class="col-lg-4">
        <Panel title="Placement History">
          <div v-if="!store.data.placements.length" class="text-secondary">No placements recorded yet.</div>
          <div v-for="placement in store.data.placements" :key="placement.id" class="history-item">
            <strong>{{ placement.job_title }}</strong>
            <span>{{ placement.company_name }}</span>
            <small>{{ store.formatPackage(placement.package) }} · {{ store.formatDate(placement.placed_at) }}</small>
          </div>
        </Panel>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { usePpaStore } from '../stores/ppa'
import Panel from '../components/Panel.vue'
import ApplicationTable from '../components/ApplicationTable.vue'

const store = usePpaStore()
let refreshTimer = null

function onFileChange(event) {
  store.resumeFile = event.target.files?.[0] || null
}

async function applyDrive(jobId) {
  const confirmed = await store.confirmAction('Do you want to submit your application for this job?')
  if (!confirmed) {
    return
  }
  await store.applyToDrive(jobId)
}

onMounted(async () => {
  if (!store.isLoggedIn || store.user?.role !== 'student') return
  await store.loadStudent()
  refreshTimer = setInterval(() => store.loadStudent(), 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
