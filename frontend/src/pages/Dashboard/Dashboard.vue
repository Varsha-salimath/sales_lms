<template>
	<div
		v-if="!user.data"
		class="grid min-h-[40vh] place-items-center text-sm text-[color:var(--genius-muted)]"
	>
		{{ __('Loading dashboard…') }}
	</div>
	<SalesOnboardingHome v-else />
</template>
<script setup>
import SalesOnboardingHome from '@/pages/Sales/SalesOnboardingHome.vue'
</script>
