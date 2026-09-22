<template>
	<div v-if="userResource.data?.learner_preview" class="lp-banner">
		<Eye class="h-4 w-4 flex-none" />
		<span class="flex-1">{{ __('Learner view: you see the LMS exactly as a learner does (locks, viva, Hello ILians).') }}</span>
		<button class="lp-exit" :disabled="busy" @click="exit">{{ __('Exit learner view') }}</button>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { call } from 'frappe-ui'
import { Eye } from 'lucide-vue-next'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()
const busy = ref(false)

async function exit() {
	busy.value = true
	await call('lms.lms.access.set_learner_preview', { on: 0 })
	window.location.reload()
}
</script>

<style scoped>
.lp-banner {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 8px 16px;
	font-size: 13px;
	font-weight: 500;
	color: #00254c;
	background: #fcde5a;
}
.lp-exit {
	height: 28px;
	padding: 0 14px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	color: #fff;
	background: #00254c;
	flex: none;
}
</style>
