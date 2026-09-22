<template>
	<nav
		class="flex flex-wrap gap-1 rounded-lg border bg-surface-gray-1 p-1"
		aria-label="Analytics sections"
	>
		<button
			v-for="item in items"
			:key="item.id"
			type="button"
			class="rounded-md px-3 py-2 text-sm font-medium transition-colors"
			:class="
				modelValue === item.id
					? 'bg-surface-white text-ink-gray-9 shadow-sm'
					: 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
			"
			@click="$emit('update:modelValue', item.id)"
		>
			{{ item.label }}
		</button>
	</nav>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	modelValue: {
		type: String,
		required: true,
	},
	showOperations: {
		type: Boolean,
		default: false,
	},
})

defineEmits(['update:modelValue'])

const items = computed(() => {
	const list = [
		{ id: 'overview', label: __('Overview') },
		...(props.showOperations
			? [{ id: 'operations', label: __('Operations') }]
			: []),
		{ id: 'progress', label: __('Learner Progress') },
		{ id: 'certification', label: __('Certification') },
		{ id: 'feedback', label: __('Feedback') },
	]
	return list
})
</script>
