<template>
	<div>
		<div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Team') }}</div>
		<div
			v-if="teams.data && teams.data.teams.length === 1"
			class="flex h-7 items-center rounded bg-surface-gray-2 px-2 text-base text-ink-gray-8"
			:title="__('New items go to your team automatically.')"
		>
			{{ teams.data.teams[0] }}
		</div>
		<select
			v-else
			:value="modelValue || ''"
			class="h-7 w-full rounded border-0 bg-surface-gray-2 px-2 py-0 text-base text-ink-gray-8 focus:ring-2 focus:ring-outline-gray-3"
			@change="onChange($event.target.value)"
		>
			<option value="">{{ __('Pick a team') }}</option>
			<option v-for="t in teams.data?.teams || []" :key="t" :value="t">{{ t }}</option>
		</select>
		<p class="mt-1 text-xs text-ink-gray-5">{{ __('Only this team (and Super Admins) will see it.') }}</p>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

// Team (LMS Department) that owns a course, batch or program.
const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue', 'change'])

const teams = createResource({
	url: 'lms.lms.content_scope.get_assignable_teams',
	auto: true,
	cache: 'lms-assignable-teams',
	onSuccess(data) {
		// New items: pre-fill the person's main team (or their only team).
		if (!props.modelValue && data?.default) onChange(data.default)
	},
})

function onChange(value) {
	emit('update:modelValue', value || null)
	emit('change', value || null)
}
</script>
