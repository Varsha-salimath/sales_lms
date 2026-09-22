<template>
	<div class="max-w-xl py-6">
		<h2 class="mb-1 text-base font-semibold text-ink-gray-9">{{ __('Account & ID history') }}</h2>
		<p class="mb-4 text-sm text-ink-gray-6">
			{{ __('Login email and employee code, and every change made to them.') }}
		</p>
		<IdentityPanel v-if="profile?.data?.name" :user="profile.data.name" />
	</div>
</template>

<script setup>
import IdentityPanel from '@/components/IdentityPanel.vue'

defineProps({ profile: { type: Object, required: true } })
</script>
