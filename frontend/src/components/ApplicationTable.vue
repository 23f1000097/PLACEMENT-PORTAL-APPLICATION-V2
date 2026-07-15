<template>
  <div class="table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>Student</th>
          <th>Drive</th>
          <th>Status</th>
          <th>Interview</th>
          <th>Feedback</th>
          <th>Offer Letter</th>
          <th v-if="canEdit"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="application in applications" :key="application.id">
          <td><strong>{{ application.student_name }}</strong></td>
          <td>{{ application.job_title }}<br><span class="text-secondary">{{ application.company_name }}</span></td>
          <td>
            <template v-if="canEdit">
              <select v-model="draft(application).status" class="form-select form-select-sm status-select">
                <option>Applied</option>
                <option>Shortlisted</option>
                <option>Interview</option>
                <option>Selected</option>
                <option>Rejected</option>
                <option>Placed</option>
              </select>
            </template>
            <span v-else class="badge text-bg-info">{{ application.status }}</span>
          </td>
          <td>
            <template v-if="canEdit">
              <label v-if="draft(application).status === 'Interview'" class="form-label small mb-1 text-primary fw-semibold">Schedule interview</label>
              <input v-model="draft(application).interview_at" class="form-control form-control-sm" type="datetime-local" />
            </template>
            <span v-else>{{ format(application.interview_at) }}</span>
          </td>
          <td>
            <input v-if="canEdit" v-model="draft(application).feedback" class="form-control form-control-sm" placeholder="Feedback" />
            <span v-else>{{ application.feedback || 'Not shared' }}</span>
          </td>
          <td>
            <template v-if="canEdit">
              <input
                class="form-control form-control-sm mb-1"
                type="file"
                accept=".pdf,.doc,.docx"
                @change="onOfferLetterChange(application, $event)"
              />
              <button
                class="btn btn-sm btn-outline-secondary"
                :disabled="!offerLetterFiles[application.id]"
                @click="$emit('upload-offer-letter', application.id, offerLetterFiles[application.id])"
              >
                Upload
              </button>
            </template>
            <template v-else>
              <button
                v-if="application.offer_letter"
                class="btn btn-sm btn-outline-success"
                @click="$emit('download-offer-letter', application.id)"
              >
                Download
              </button>
              <span v-else class="text-secondary">Not available</span>
            </template>
          </td>
          <td v-if="canEdit" class="text-end">
            <button class="btn btn-sm btn-outline-primary" @click="$emit('save', application.id)">Save</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!applications.length" class="text-secondary">No applications found.</div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, reactive } from 'vue'

const props = defineProps({
  applications: { type: Array, required: true },
  canEdit: { type: Boolean, default: false },
  drafts: { type: Object, required: true },
})

const emit = defineEmits(['init', 'save', 'upload-offer-letter', 'download-offer-letter'])

const offerLetterFiles = reactive({})

function format(value) {
  return value ? new Date(value).toLocaleString() : 'Not set'
}

function draft(application) {
  emit('init', application)
  return props.drafts[application.id]
}

function onOfferLetterChange(application, event) {
  offerLetterFiles[application.id] = event.target.files?.[0] || null
}
</script>
