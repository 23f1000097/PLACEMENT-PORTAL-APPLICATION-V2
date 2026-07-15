<template>
  <div class="row g-4 mb-4">
    <div class="col-lg-6">
      <Panel title="Placement Trend (last 6 months)">
        <canvas ref="trendCanvas" height="220"></canvas>
      </Panel>
    </div>
    <div class="col-lg-6">
      <Panel title="Application Funnel">
        <canvas ref="funnelCanvas" height="220"></canvas>
      </Panel>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, defineProps } from 'vue'
import Chart from 'chart.js/auto'
import Panel from './Panel.vue'

const props = defineProps({
  trend: { type: Object, default: () => ({ labels: [], counts: [] }) },
  funnel: { type: Object, default: () => ({ labels: [], counts: [] }) },
})

const trendCanvas = ref(null)
const funnelCanvas = ref(null)
let trendChart = null
let funnelChart = null

function renderCharts() {
  if (trendChart) {
    trendChart.destroy()
    trendChart = null
  }
  if (funnelChart) {
    funnelChart.destroy()
    funnelChart = null
  }

  if (trendCanvas.value) {
    trendChart = new Chart(trendCanvas.value, {
      type: 'line',
      data: {
        labels: props.trend.labels,
        datasets: [{
          label: 'Placements',
          data: props.trend.counts,
          borderColor: '#0d6efd',
          backgroundColor: 'rgba(13,110,253,0.15)',
          fill: true,
          tension: 0.3,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    })
  }

  if (funnelCanvas.value) {
    funnelChart = new Chart(funnelCanvas.value, {
      type: 'bar',
      data: {
        labels: props.funnel.labels,
        datasets: [{
          label: 'Applications',
          data: props.funnel.counts,
          backgroundColor: ['#6c757d', '#0dcaf0', '#ffc107', '#198754', '#20c997'],
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    })
  }
}

onMounted(renderCharts)
watch(() => [props.trend, props.funnel], renderCharts, { deep: true })
onBeforeUnmount(() => {
  if (trendChart) trendChart.destroy()
  if (funnelChart) funnelChart.destroy()
})
</script>
