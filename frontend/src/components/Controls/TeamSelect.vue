<template>
	<div>
		<div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Teams') }}</div>
		<div class="flex flex-wrap gap-1.5">
			<button
				v-for="t in teams.data?.teams || []"
				:key="t"
				type="button"
				class="team-chip"
				:class="{ 'is-on': selected.includes(t) }"
				:aria-pressed="selected.includes(t)"
				@click="toggle(t)"
			>
				<Check v-if="selected.includes(t)" class="h-3.5 w-3.5" />
				{{ t }}
			</button>
			<!-- Teams already on the record that this person can't manage: shown, not editable. -->
			<span v-for="t in locked" :key="t" class="team-chip is-on is-locked" :title="__('Only an admin of this team can remove it.')">
				<Lock class="h-3 w-3" />{{ t }}
			</span>
		</div>
		<p class="mt-1 text-xs text-ink-gray-5">
			{{ selected.length || locked.length ? __('Everyone in these teams (and Super Admins) will see it.') : __('No team: shared with all teams.') }}
		</p>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import { Check, Lock } from 'lucide-vue-next'

// Teams (LMS Department) that own a course, batch or program. v-model is the `teams` child table:
// an array of { team } rows (plain strings are accepted too).
const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	// Only new records start with the editor's own team; an existing record with no teams is
	// deliberately shared with everyone.
	applyDefault: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const current = computed(() => (props.modelValue || []).map((r) => (typeof r === 'string' ? r : r?.team)).filter(Boolean))
const assignable = computed(() => teams.data?.teams || [])
const selected = computed(() => current.value.filter((t) => assignable.value.includes(t)))
const locked = computed(() => (teams.data ? current.value.filter((t) => !assignable.value.includes(t)) : []))

const teams = createResource({
	url: 'lms.lms.content_scope.get_assignable_teams',
	auto: true,
	cache: 'lms-assignable-teams',
	onSuccess(data) {
		// New items start with the person's main team (or their only team). On an edit form an
		// empty list means "shared with every team" and must be left alone.
		if (props.applyDefault && !current.value.length && data?.default) set([data.default])
	},
})

function set(list) {
	const rows = [...new Set(list)].map((team) => ({ team }))
	emit('update:modelValue', rows)
	emit('change', rows)
}

function toggle(team) {
	const next = current.value.includes(team) ? current.value.filter((t) => t !== team) : [...current.value, team]
	set(next)
}
</script>

<style scoped>
.team-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	height: 28px;
	padding: 0 12px;
	border-radius: 999px;
	font-size: 13px;
	border: 1px solid #e6e7e8;
	background: #fff;
	color: #080e14;
}
.team-chip.is-on {
	background: #e6f2ff;
	border-color: #99caff;
	color: #0062cc;
	font-weight: 500;
}
.team-chip.is-locked {
	cursor: default;
	background: #f2f2f2;
	border-color: #e6e7e8;
	color: #52565c;
}
</style>
