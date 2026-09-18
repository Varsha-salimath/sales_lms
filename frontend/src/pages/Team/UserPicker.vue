<template>
	<div class="relative">
		<label class="up-field">
			<Search class="h-4 w-4 shrink-0 text-[color:var(--il-neutral-60)]" />
			<input
				v-model="term"
				:placeholder="placeholder"
				@focus="open = true"
				@input="onInput"
				@keydown.esc="open = false"
			/>
		</label>
		<ul v-if="open && (results.length || loading)" class="up-list">
			<li v-if="loading && !results.length" class="px-3 py-2 text-sm text-[color:var(--il-muted)]">{{ __('Searching…') }}</li>
			<li v-for="u in results" :key="u.name">
				<button type="button" class="up-item" @mousedown.prevent="pick(u)">
					<span class="up-avatar">{{ initials(u.full_name || u.name) }}</span>
					<span class="min-w-0 flex-1 text-left">
						<span class="block truncate text-sm font-medium text-[color:var(--il-ink)]">{{ u.full_name || u.name }}</span>
						<span class="block truncate text-xs text-[color:var(--il-muted)]">{{ u.name }}</span>
					</span>
					<span v-if="markMembers && u.is_member" class="text-[11px] text-[color:var(--il-muted)]">{{ __('in a team') }}</span>
				</button>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { call } from 'frappe-ui'
import { Search } from 'lucide-vue-next'

// Search enabled users by name or email and pick one.
defineProps({
	placeholder: { type: String, default: 'Search by name or email' },
	markMembers: { type: Boolean, default: false },
})
const emit = defineEmits(['pick'])

const term = ref('')
const results = ref([])
const open = ref(false)
const loading = ref(false)
let timer = null

function onInput() {
	open.value = true
	clearTimeout(timer)
	timer = setTimeout(search, 200)
}

async function search() {
	loading.value = true
	try {
		results.value = await call('lms.lms.team_access.search_users', { txt: term.value })
	} finally {
		loading.value = false
	}
}

function pick(u) {
	emit('pick', u)
	term.value = ''
	results.value = []
	open.value = false
}

function initials(name) {
	return String(name)
		.split(/[\s.@]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}
</script>

<style scoped>
.up-field {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	height: 2.6rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0 0.8rem;
	background: #fff;
}

.up-field:focus-within {
	border-color: var(--il-primary-50);
	box-shadow: 0 0 0 3px rgba(2, 123, 255, 0.12);
}

.up-field input {
	flex: 1;
	min-width: 0;
	border: 0;
	padding: 0;
	background: transparent;
	box-shadow: none;
	font-size: 0.875rem;
}

.up-list {
	position: absolute;
	z-index: 30;
	left: 0;
	right: 0;
	top: calc(100% + 4px);
	max-height: 16rem;
	overflow-y: auto;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0.25rem;
	background: #fff;
	box-shadow: 0 8px 24px rgba(0, 37, 76, 0.14);
}

.up-item {
	display: flex;
	width: 100%;
	align-items: center;
	gap: 0.6rem;
	border-radius: 8px;
	padding: 0.45rem 0.6rem;
}

.up-item:hover {
	background: #f4f9ff;
}

.up-avatar {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 1.9rem;
	height: 1.9rem;
	border-radius: 999px;
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-size: 0.7rem;
	font-weight: 600;
}
</style>
