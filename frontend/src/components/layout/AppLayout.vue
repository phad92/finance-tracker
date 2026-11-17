<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import TopNavbar from './TopNavbar.vue'
</script>

<template>
  <div class="min-h-screen bg-background text-slate-100 flex">
    <Sidebar />
    <div class="flex-1 ml-64 flex flex-col min-w-0">
      <TopNavbar />
      <main class="flex-1 p-8 overflow-y-auto">
        <slot />
      </main>
    </div>
  </div>
</template>

