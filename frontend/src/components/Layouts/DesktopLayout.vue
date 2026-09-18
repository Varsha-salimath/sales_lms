<template>
	<!-- Infinity Learn shell: sidebar rail on the blue chrome, content in a floating white panel. -->
	<div class="il-app-chrome flex h-screen w-screen overflow-hidden">
		<AppSidebar />
		<div class="il-app-panel flex h-full min-w-0 flex-1 flex-col overflow-auto">
			<slot />
		</div>
	</div>
</template>
<script setup>
import AppSidebar from '@/components/Sidebar/AppSidebar.vue'
</script>
