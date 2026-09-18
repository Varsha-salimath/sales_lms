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
defineProps({
	modelValue: {
		type: String,
		required: true,
	},
})

defineEmits(['update:modelValue'])

const items = [
	{ id: 'overview', label: __('Overview') },
	{ id: 'progress', label: __('Learner Progress') },
	{ id: 'certification', label: __('Certification') },
	{ id: 'feedback', label: __('Feedback') },
]
</script>
