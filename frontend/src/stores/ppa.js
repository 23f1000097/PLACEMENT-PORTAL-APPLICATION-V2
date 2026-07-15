import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { apiRequest } from '../services/api'

function cleanPayload(source) {
  return Object.fromEntries(
    Object.entries(source).filter(([, value]) => value !== '' && value !== null)
  )
}

export const usePpaStore = defineStore('ppa', () => {
  const token = ref(localStorage.getItem('ppa_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('ppa_user') || 'null'))
  const loading = ref(false)
  const message = ref('')
  const error = ref('')
  const authMode = ref('login')
  const loginForm = reactive({ email: 'admin@placement.com', password: 'admin123' })
  const studentForm = reactive({
    name: '', email: '', password: '', college: '', phone: '', degree: '',
    branch: '', cgpa: '', passing_year: '', skills: '', specialization: '', experience: '',
  })
  const companyForm = reactive({
    name: '', email: '', password: '', company_name: '', industry: '',
    hr_contact: '', contact_email: '', phone: '', website: '', location: '', description: '',
  })
  const data = reactive({
    stats: {}, users: [], companies: [], jobs: [], students: [], applications: [],
    placements: [], profile: null, drives: [],
    analytics: { trend: { labels: [], counts: [] }, funnel: { labels: [], counts: [] } },
  })
  const filters = reactive({ q: '', status: '', approved: '' })
  const studentProfile = reactive({
    name: '', college: '', phone: '', degree: '', branch: '', specialization: '',
    cgpa: '', passing_year: '', skills: '', experience: '',
  })
  const companyProfile = reactive({
    company_name: '', industry: '', hr_contact: '', contact_email: '', phone: '',
    website: '', location: '', description: '',
  })
  const jobForm = reactive({
    title: '', description: '', location: '', job_type: 'Full Time', salary: '',
    skills_required: '', benefits: '', minimum_cgpa: '', eligibility_branch: '',
    eligibility_year: '', vacancies: '', last_date: '',
  })
  const placementForm = reactive({
    student_id: '', company_name: '', job_title: '', package: '', joining_date: '',
  })
  const statusDrafts = reactive({})
  const resumeFile = ref(null)
  const confirmState = reactive({ open: false, message: '' })
  let confirmResolver = null

  const isLoggedIn = computed(() => Boolean(token.value && user.value))
  const roleLabel = computed(() => (user.value?.role ? user.value.role.toUpperCase() : 'GUEST'))

  function getHeaders() {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  async function request(path, options = {}) {
    return apiRequest(path, options)
  }

  async function run(action, successText = '') {
    loading.value = true
    error.value = ''
    message.value = ''
    try {
      const response = await action()
      if (successText) {
        message.value = successText
      }
      return response
    } catch (err) {
      const data = err.response?.data
      const baseMessage = data?.message || err.message || 'Something went wrong'
      const reasons = Array.isArray(data?.reasons) ? data.reasons : []
      error.value = reasons.length ? `${baseMessage}: ${reasons.join('; ')}` : baseMessage
      throw err
    } finally {
      loading.value = false
    }
  }

  function saveSession(payload) {
    token.value = payload.access_token
    user.value = payload.user
    localStorage.setItem('ppa_token', token.value)
    localStorage.setItem('ppa_user', JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('ppa_token')
    localStorage.removeItem('ppa_user')
  }

  function fill(target, source = {}) {
    Object.keys(target).forEach((key) => {
      target[key] = source[key] ?? ''
    })
  }

  function confirmAction(message) {
    confirmState.message = message
    confirmState.open = true
    return new Promise((resolve) => {
      confirmResolver = resolve
    })
  }

  function resolveConfirm(result) {
    confirmState.open = false
    if (confirmResolver) {
      confirmResolver(result)
      confirmResolver = null
    }
  }

  function initDraft(application) {
    if (!statusDrafts[application.id]) {
      statusDrafts[application.id] = {
        status: application.status,
        feedback: application.feedback || '',
        interview_at: application.interview_at ? application.interview_at.slice(0, 16) : '',
        offer_letter: application.offer_letter || '',
      }
    }
    return statusDrafts[application.id]
  }

  function formatDate(value) {
    if (!value) return 'Not set'
    return new Date(value).toLocaleString()
  }

  function formatPackage(value, fallback = 'Package not set') {
    if (value === null || value === undefined || value === '') return fallback
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) return String(value)
    return `${numeric.toFixed(2)} LPA`
  }

  function shortText(value, fallback = 'Not provided') {
    return value || fallback
  }

  async function login() {
    const response = await run(() => request('/auth/login', { method: 'POST', data: cleanPayload(loginForm) }))
    saveSession(response.data)
    return response
  }

  async function registerStudent() {
    const response = await run(
      () => request('/auth/register/student', { method: 'POST', data: cleanPayload(studentForm) }),
      'Student account created',
    )
    saveSession(response.data)
    return response
  }

  async function registerCompany() {
    const response = await run(
      () => request('/auth/register/company', { method: 'POST', data: cleanPayload(companyForm) }),
      'Company registered. Awaiting admin approval.',
    )
    saveSession(response.data)
    return response
  }

  async function loadDashboard() {
    if (!isLoggedIn.value) return
    if (user.value.role === 'admin') await loadAdmin()
    if (user.value.role === 'company') await loadCompany()
    if (user.value.role === 'student') await loadStudent()
  }

  async function loadAdmin() {
    await run(async () => {
      const [dashboard, users, companies, jobs, students, applications, placements] = await Promise.all([
        request('/admin/dashboard'),
        request(`/admin/users?q=${encodeURIComponent(filters.q)}`),
        request(`/admin/companies?q=${encodeURIComponent(filters.q)}&approved=${filters.approved}`),
        request(`/admin/jobs?q=${encodeURIComponent(filters.q)}&approved=${filters.approved}`),
        request(`/admin/students?q=${encodeURIComponent(filters.q)}`),
        request(`/admin/applications?status=${encodeURIComponent(filters.status)}`),
        request('/admin/placements'),
      ])
      data.stats = dashboard.data.stats
      data.analytics = dashboard.data.analytics || data.analytics
      data.users = users.data.users
      data.companies = companies.data.companies
      data.jobs = jobs.data.jobs
      data.students = students.data.students
      data.applications = applications.data.applications
      data.placements = placements.data.placements
    })
  }

  async function loadCompany() {
    await run(async () => {
      const [me, profile] = await Promise.all([
        request('/auth/me'),
        request('/company/profile'),
      ])
      data.profile = me.data.profile
      fill(companyProfile, profile.data.company)
      if (profile.data.company.approved) {
        const [dashboard, applications, placements] = await Promise.all([
          request('/company/dashboard'),
          request('/application/'),
          request('/placement/'),
        ])
        data.stats = dashboard.data.stats
        data.jobs = dashboard.data.jobs
        data.applications = applications.data.applications
        data.placements = placements.data.placements
      }
    })
  }

  async function loadStudent() {
    await run(async () => {
      // Load the dashboard first and apply it on its own so the drives always
      // render even if the profile request below fails for any reason.
      const dashboard = await request('/student/dashboard')
      data.profile = dashboard.data.student
      data.drives = dashboard.data.approved_drives || []
      data.applications = dashboard.data.applications || []
      data.placements = dashboard.data.placements || []

      try {
        const profile = await request('/student/profile')
        fill(studentProfile, { name: user.value.name, ...profile.data.student })
      } catch (err) {
        // Profile is secondary to the drives list — don't let it blank the page.
        console.error('Failed to load student profile', err)
      }
    })
  }

  async function searchDrives() {
    await run(async () => {
      const response = await request(`/student/drives?q=${encodeURIComponent(filters.q)}`)
      data.drives = response.data.drives
    })
  }

  async function updateUserStatus(userId, isActive) {
    await run(
      () => request(`/admin/users/${userId}/status`, { method: 'PATCH', data: { is_active: isActive } }),
      'User status updated',
    )
    await loadAdmin()
  }

  async function approveCompany(companyId, approved) {
    await run(
      () => request(`/admin/companies/${companyId}/approve`, { method: 'PATCH', data: { approved } }),
      'Company approval updated',
    )
    await loadAdmin()
  }

  async function approveJob(jobId, approved) {
    await run(
      () => request(`/admin/jobs/${jobId}/approve`, { method: 'PATCH', data: { approved } }),
      'Drive approval updated',
    )
    await loadAdmin()
  }

  async function deleteCompany(companyId) {
    await run(
      () => request(`/admin/companies/${companyId}`, { method: 'DELETE' }),
      'Company removed',
    )
    await loadAdmin()
  }

  async function deleteJob(jobId) {
    await run(
      () => request(`/admin/jobs/${jobId}`, { method: 'DELETE' }),
      'Placement drive removed',
    )
    await loadAdmin()
  }

  async function saveStudentProfile() {
    const payload = new FormData()
    Object.entries(cleanPayload(studentProfile)).forEach(([key, value]) => payload.append(key, value))
    if (resumeFile.value) payload.append('resume', resumeFile.value)
    await run(
      () => request('/student/profile', { method: 'PATCH', data: payload }),
      'Profile updated',
    )
    resumeFile.value = null
    await loadStudent()
  }

  async function saveCompanyProfile() {
    await run(
      () => request('/company/profile', { method: 'PATCH', data: cleanPayload(companyProfile) }),
      'Company profile updated',
    )
    await loadCompany()
  }

  async function createJob() {
    await run(
      () => request('/company/jobs', { method: 'POST', data: cleanPayload(jobForm) }),
      'Placement drive submitted for approval',
    )
    fill(jobForm, { job_type: 'Full Time' })
    await loadCompany()
  }

  async function applyToDrive(jobId) {
    await run(
      () => request(`/student/drives/${jobId}/apply`, { method: 'POST' }),
      'Application submitted. You will receive an email confirmation shortly.',
    )
    await loadStudent()
  }

  const EMAILED_STATUSES = new Set(['Interview', 'Shortlisted', 'Selected', 'Rejected', 'Placed'])

  async function updateApplicationStatus(applicationId) {
    const draft = statusDrafts[applicationId] || {}
    const successText = EMAILED_STATUSES.has(draft.status)
      ? 'Application status updated — student notified via email'
      : 'Application status updated'
    await run(
      () => request(`/application/${applicationId}/status`, { method: 'PATCH', data: cleanPayload(draft) }),
      successText,
    )
    await loadDashboard()
  }

  async function updateJobStatus(jobId, status) {
    await run(
      () => request(`/company/jobs/${jobId}`, { method: 'PATCH', data: { status } }),
      status === 'Active' ? 'Placement drive activated' : 'Placement drive deactivated',
    )
    await loadCompany()
  }

  function triggerBlobDownload(blob, filename) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename || 'export.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  async function pollExportTask(statusPath, taskId) {
    const maxAttempts = 30
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await request(`${statusPath}/${taskId}`)
      if (response.data.state === 'SUCCESS') return response.data
      if (response.data.state === 'FAILURE') throw new Error(response.data.error || 'Export failed')
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    throw new Error('Export timed out. Please try again.')
  }

  async function runExport(startPath) {
    return run(async () => {
      const started = await request(startPath, { method: 'POST' })
      const taskId = started.data.task_id
      const status = await pollExportTask(startPath, taskId)
      const fileResponse = await request(`${startPath}/${taskId}?download=true`, { responseType: 'blob' })
      triggerBlobDownload(new Blob([fileResponse.data]), status.filename)
      message.value = `CSV export downloaded: ${status.filename}`
    })
  }

  async function exportApplications() {
    return runExport('/student/applications/export')
  }

  async function exportCompanyApplications() {
    return runExport('/company/applications/export')
  }

  async function uploadOfferLetter(applicationId, file) {
    if (!file) return
    const payload = new FormData()
    payload.append('offer_letter', file)
    await run(
      () => request(`/company/applications/${applicationId}/offer-letter`, { method: 'POST', data: payload }),
      'Offer letter uploaded',
    )
    await loadDashboard()
  }

  async function downloadOfferLetter(applicationId) {
    await run(async () => {
      const response = await request(`/student/applications/${applicationId}/offer-letter`, { responseType: 'blob' })
      triggerBlobDownload(new Blob([response.data]), `offer_letter_${applicationId}`)
    })
  }

  async function generateMonthlyReport(type) {
    const path = type === 'pdf' ? '/admin/reports/monthly/pdf' : '/admin/reports/monthly'
    const method = type === 'pdf' ? 'POST' : 'GET'
    const response = await run(() => request(path, { method }), 'Monthly report generated')
    if (type === 'pdf') {
      message.value = `Monthly PDF generated: ${response.data.filename}`
    } else {
      message.value = 'Monthly HTML report generated by the API'
    }
    return response
  }

  return {
    token,
    user,
    loading,
    message,
    error,
    authMode,
    loginForm,
    studentForm,
    companyForm,
    data,
    filters,
    studentProfile,
    companyProfile,
    jobForm,
    placementForm,
    statusDrafts,
    resumeFile,
    confirmState,
    confirmAction,
    resolveConfirm,
    isLoggedIn,
    roleLabel,
    login,
    registerStudent,
    registerCompany,
    logout,
    loadDashboard,
    loadAdmin,
    loadCompany,
    loadStudent,
    searchDrives,
    updateUserStatus,
    approveCompany,
    approveJob,
    deleteCompany,
    deleteJob,
    saveStudentProfile,
    saveCompanyProfile,
    createJob,
    applyToDrive,
    updateApplicationStatus,
    updateJobStatus,
    exportApplications,
    exportCompanyApplications,
    uploadOfferLetter,
    downloadOfferLetter,
    generateMonthlyReport,
    initDraft,
    formatDate,
    formatPackage,
    shortText,
    fill,
    cleanPayload,
  }
})
