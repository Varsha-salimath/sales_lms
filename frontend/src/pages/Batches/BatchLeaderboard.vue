<template>
	<div>
		<header
			class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="breadcrumbs" />
		</header>
		<div class="p-5 pb-10 max-w-4xl mx-auto">
			<BatchLeaderboardPanel :batch-name="batchName" />
		</div>
	</div>
</template>

<script setup>
import { Breadcrumbs, createResource, usePageMeta } from 'frappe-ui'
import { computed } from 'vue'
import { sessionStore } from '@/stores/session'
import BatchLeaderboardPanel from '@/pages/Batches/components/BatchLeaderboardPanel.vue'

const props = defineProps({
	batchName: {
		type: String,
		required: true,
	},
})

const { brand } = sessionStore()

const batch = createResource({
	url: 'lms.lms.utils.get_batch_details',
	params: { batch: props.batchName },
	auto: true,
})

const breadcrumbs = computed(() => [
	{ label: __('Batches'), route: { name: 'Batches' } },
	{
		label: batch.data?.title || props.batchName,
		route: { name: 'BatchDetail', params: { batchName: props.batchName } },
	},
	{ label: __('Leaderboard') },
])

usePageMeta(() => ({
	title: __('Leaderboard'),
	icon: brand.favicon,
}))
</script>
