<template>
  <section class="card shadow-sm h-100">
    <div class="card-header bg-white"><h2 class="h5 mb-0">{{ title }}</h2></div>
    <div class="card-body"><slot /></div>
  </section>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
})
</script>
