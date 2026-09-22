<template>
	<div class="il-page min-h-full pb-12">
		<header class="flex flex-wrap items-end justify-between gap-3 pt-5 pb-4">
			<div>
				<h1 class="il-page-title">{{ __('Team & access') }}</h1>
				<p class="mt-1 text-sm text-[color:var(--il-muted)]">{{ scopeLine }}</p>
			</div>
			<button class="il-btn il-btn-primary" :disabled="!data" @click="openMember()">
				<UserPlus class="h-4 w-4" />
				{{ __('Add person') }}
			</button>
		</header>

		<div v-if="res.loading && !data" class="space-y-4">
			<div class="h-24 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="h-72 animate-pulse rounded-3xl bg-[#e6e7e8]" />
		</div>
		<div v-else-if="res.error" class="il-card p-8 text-center text-sm text-[color:var(--il-error-50)]">
			{{ res.error.messages?.[0] || __('Could not load team access.') }}
		</div>

		<template v-else-if="data">
			<!-- Teams -->
			<section class="ta-teams no-scrollbar">
				<button type="button" class="ta-team" :class="{ 'is-active': !team }" @click="team = null">
					<span class="text-sm font-medium">{{ __('All teams') }}</span>
					<span class="ta-count">{{ data.members.length }}</span>
				</button>
				<button
					v-for="d in visibleTeams"
					:key="d.name"
					type="button"
					class="ta-team"
					:class="{ 'is-active': team === d.name }"
					:title="d.description"
					@click="team = team === d.name ? null : d.name"
				>
					<span class="text-sm font-medium">{{ d.name }}</span>
					<span class="ta-count">{{ d.count }}</span>
				</button>
			</section>

			<!-- Tabs -->
			<div class="ta-tabs">
				<button v-for="t in tabs" :key="t.key" :class="{ 'is-active': tab === t.key }" @click="tab = t.key">
					{{ t.label }}
					<span v-if="t.badge" class="ta-badge">{{ t.badge }}</span>
				</button>
			</div>

			<!-- People -->
			<section v-if="tab === 'people'" class="il-card overflow-hidden">
				<div class="flex flex-wrap items-center gap-3 border-b border-[color:var(--il-neutral-95)] px-4 py-3">
					<label class="ta-search">
						<Search class="h-4 w-4 text-[color:var(--il-neutral-60)]" />
						<input v-model="search" :placeholder="__('Search people')" />
					</label>
					<label class="flex items-center gap-2 text-sm text-[color:var(--il-muted)]">
						<input v-model="onlyUnassigned" type="checkbox" class="rounded" />
						{{ __('No manager yet') }}
					</label>
				</div>

				<ul>
					<template v-if="!team && !search && !onlyUnassigned">
					<li v-for="s in data.super_admins" :key="`sa-${s.user}`" class="ta-row">
						<span class="ta-avatar is-super">{{ initials(s.full_name || s.user) }}</span>
						<div class="min-w-0 flex-1">
							<div class="truncate font-medium text-[color:var(--il-ink)]">{{ s.full_name || s.user }}</div>
							<div class="truncate text-xs text-[color:var(--il-muted)]">{{ s.user }}</div>
						</div>
						<span class="ta-role is-super">{{ __('Super Admin') }}</span>
						<span class="ta-teams-cell text-xs text-[color:var(--il-muted)]">{{ __('All teams') }}</span>
						<span class="ta-mgr-cell" />
						<span class="w-9" />
					</li>
					</template>

					<li v-for="m in people" :key="m.user" class="ta-row" :class="{ 'is-inactive': m.status === 'Inactive' }">
						<span class="ta-avatar">{{ initials(m.full_name || m.user) }}</span>
						<div class="min-w-0 flex-1">
							<div class="truncate font-medium text-[color:var(--il-ink)]">
								{{ m.full_name || m.user }}
								<span v-if="m.status === 'Inactive'" class="ms-1 text-xs font-normal text-[color:var(--il-muted)]">· {{ __('Deactivated') }}</span>
							</div>
							<div class="truncate text-xs text-[color:var(--il-muted)]">
								{{ m.user }}<template v-if="m.employee_code"> · {{ m.employee_code }}</template>
							</div>
						</div>
						<span class="ta-role" :class="`is-${m.access_role.toLowerCase()}`">{{ roleLabel(m.access_role) }}</span>
						<div class="ta-teams-cell">
							<span v-for="d in m.departments" :key="d.department" class="ta-chip" :class="{ 'is-primary': d.is_primary }">{{ d.department }}</span>
							<span v-if="!m.departments.length" class="text-xs text-[color:var(--il-warning-50)]">{{ __('No team') }}</span>
						</div>
						<div class="ta-mgr-cell text-xs">
							<div v-for="l in m.managers" :key="l.name" class="truncate">
								<span class="text-[color:var(--il-ink)]">{{ l.manager_name || l.manager }}</span>
								<span class="text-[color:var(--il-muted)]"> · {{ shortType(l.line_type) }}</span>
							</div>
							<span v-if="!m.managers.length" class="text-[color:var(--il-muted)]">{{ __('No manager') }}</span>
						</div>
						<button v-if="m.can_edit" type="button" class="ta-edit" :aria-label="__('Edit')" @click="openMember(m)">
							<Pencil class="h-4 w-4" />
						</button>
						<span v-else class="w-9" />
					</li>
					<li v-if="!people.length" class="px-4 py-10 text-center text-sm text-[color:var(--il-muted)]">
						{{ search || team || onlyUnassigned ? __('Nobody matches.') : __('No one here yet. Use “Add person”.') }}
					</li>
				</ul>
			</section>

			<!-- Reporting lines -->
			<section v-if="tab === 'lines'" class="il-card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--il-neutral-95)] px-4 py-3">
					<p class="text-sm text-[color:var(--il-muted)]">{{ __('Ending a line removes the manager’s view straight away. Training data is kept.') }}</p>
					<button class="il-btn il-btn-light !h-9 !px-4 text-sm" @click="openLine()"><Plus class="h-4 w-4" /> {{ __('Add line') }}</button>
				</div>
				<ul>
					<li v-for="l in lines" :key="l.name" class="ta-row">
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm">
								<span class="font-medium text-[color:var(--il-ink)]">{{ l.member_name || l.member }}</span>
								<span class="text-[color:var(--il-muted)]"> {{ __('reports to') }} </span>
								<span class="font-medium text-[color:var(--il-ink)]">{{ l.manager_name || l.manager }}</span>
							</div>
							<div class="text-xs text-[color:var(--il-muted)]">{{ l.line_type }} · {{ __('since') }} {{ fmtDate(l.from_date) }}</div>
						</div>
						<button type="button" class="ta-link-danger" @click="endLine(l)">{{ __('End') }}</button>
					</li>
					<li v-if="!lines.length" class="px-4 py-10 text-center text-sm text-[color:var(--il-muted)]">{{ __('No active reporting lines.') }}</li>
				</ul>
			</section>

			<!-- Extra team views (Super Admin) -->
			<section v-if="tab === 'views'" class="il-card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--il-neutral-95)] px-4 py-3">
					<p class="text-sm text-[color:var(--il-muted)]">{{ __('Let someone see a whole team they are not part of, e.g. a trainer who needs to see Retail Sales.') }}</p>
					<button class="il-btn il-btn-light !h-9 !px-4 text-sm" @click="openGrant()"><Plus class="h-4 w-4" /> {{ __('Add view') }}</button>
				</div>
				<ul>
					<li v-for="g in data.grants" :key="g.name" class="ta-row">
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm">
								<span class="font-medium text-[color:var(--il-ink)]">{{ g.user_name || g.user }}</span>
								<span class="text-[color:var(--il-muted)]"> {{ g.can_manage ? __('sees and manages') : __('sees') }} </span>
								<span class="font-medium text-[color:var(--il-ink)]">{{ g.scope_type === 'Department' ? g.department : g.scope_type }}</span>
							</div>
							<div v-if="g.reason" class="truncate text-xs text-[color:var(--il-muted)]">{{ g.reason }}</div>
						</div>
						<button type="button" class="ta-link-danger" @click="revokeGrant(g)">{{ __('Remove') }}</button>
					</li>
					<li v-if="!data.grants.length" class="px-4 py-10 text-center text-sm text-[color:var(--il-muted)]">{{ __('No extra views.') }}</li>
				</ul>
			</section>

			<!-- Roles explained -->
			<section class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<div v-for="r in roleHelp" :key="r.role" class="ta-help">
					<span class="ta-role" :class="`is-${r.role.toLowerCase()}`">{{ roleLabel(r.role) }}</span>
					<p class="mt-2 text-xs leading-5 text-[color:var(--il-muted)]">{{ r.text }}</p>
				</div>
			</section>
		</template>

		<!-- Add / edit person -->
		<Sheet v-model="memberSheet" :title="form.isNew ? __('Add person') : form.full_name || form.user" :subtitle="form.isNew ? '' : form.user">
			<div class="space-y-5">
				<div v-if="form.isNew">
					<div class="ta-seg">
						<button type="button" :class="{ 'is-on': form.mode === 'existing' }" @click="form.mode = 'existing'">{{ __('Existing account') }}</button>
						<button type="button" :class="{ 'is-on': form.mode === 'new' }" @click="form.mode = 'new'">{{ __('New account') }}</button>
					</div>

					<template v-if="form.mode === 'existing'">
						<div class="ta-label mt-4">{{ __('Person') }}</div>
						<div v-if="form.user" class="ta-picked">
							<span class="ta-avatar">{{ initials(form.full_name || form.user) }}</span>
							<div class="min-w-0 flex-1">
								<div class="truncate text-sm font-medium">{{ form.full_name || form.user }}</div>
								<div class="truncate text-xs text-[color:var(--il-muted)]">{{ form.user }}</div>
							</div>
							<button type="button" class="text-xs font-medium text-[color:var(--il-primary-40)]" @click="form.user = ''">{{ __('Change') }}</button>
						</div>
						<UserPicker v-else mark-members @pick="pickNew" />
					</template>

					<div v-else class="mt-4 grid gap-3 sm:grid-cols-2">
						<label class="block sm:col-span-2">
							<span class="ta-label">{{ __('Work email') }}</span>
							<input v-model.trim="form.email" type="email" class="ta-select w-full" placeholder="name@infinitylearn.com" />
						</label>
						<label class="block">
							<span class="ta-label">{{ __('First name') }}</span>
							<input v-model.trim="form.first_name" class="ta-select w-full" />
						</label>
						<label class="block">
							<span class="ta-label">{{ __('Last name') }}</span>
							<input v-model.trim="form.last_name" class="ta-select w-full" />
						</label>
						<label class="block sm:col-span-2">
							<span class="ta-label">{{ __('Employee code (optional)') }}</span>
							<input v-model.trim="form.employee_code" class="ta-select w-full" :placeholder="__('Leave empty for a TEMP code; set the real one later')" />
						</label>
						<p class="text-xs text-[color:var(--il-muted)] sm:col-span-2">{{ __('They get a welcome email with a link to set their password.') }}</p>
					</div>
				</div>

				<div>
					<div class="ta-label">{{ __('Access') }}</div>
					<div class="grid gap-2 sm:grid-cols-2">
						<label v-for="r in roleHelp" :key="r.role" class="ta-option" :class="{ 'is-on': form.access_role === r.role, 'is-off': !data?.roles.includes(r.role) }">
							<input v-model="form.access_role" type="radio" :value="r.role" :disabled="!data?.roles.includes(r.role)" class="sr-only" />
							<span class="text-sm font-medium text-[color:var(--il-ink)]">{{ roleLabel(r.role) }}</span>
							<span class="text-xs leading-4 text-[color:var(--il-muted)]">{{ data?.roles.includes(r.role) ? r.text : __('Only a Super Admin can give this.') }}</span>
						</label>
					</div>
				</div>

				<div>
					<div class="ta-label">{{ assignableTeams.length === 1 ? __('Team') : __('Teams') }}</div>
					<div v-if="assignableTeams.length === 1" class="ta-picked text-sm font-medium">{{ assignableTeams[0].name }}</div>
					<div v-else class="flex flex-wrap gap-2">
						<button
							v-for="d in assignableTeams"
							:key="d.name"
							type="button"
							class="ta-pick-team"
							:class="{ 'is-on': form.departments.includes(d.name) }"
							@click="toggleTeam(d.name)"
						>
							<Check v-if="form.departments.includes(d.name)" class="h-3.5 w-3.5" />
							{{ d.name }}
						</button>
					</div>
					<div v-if="form.departments.length > 1" class="mt-3 flex flex-wrap items-center gap-2 text-xs text-[color:var(--il-muted)]">
						{{ __('Main team') }}:
						<select v-model="form.primary" class="ta-select">
							<option v-for="d in form.departments" :key="d" :value="d">{{ d }}</option>
						</select>
					</div>
				</div>

				<div v-if="!form.isNew">
					<div class="ta-label">{{ __('Account & ID') }}</div>
					<IdentityPanel :user="form.user" @changed="identityChanged" />
				</div>

				<div v-if="!form.isNew">
					<div class="ta-label">{{ __('Reports to') }}</div>
					<ul class="space-y-2">
						<li v-for="l in form.managers" :key="l.name" class="ta-picked">
							<div class="min-w-0 flex-1">
								<div class="truncate text-sm font-medium">{{ l.manager_name || l.manager }}</div>
								<div class="text-xs text-[color:var(--il-muted)]">{{ l.line_type }} · {{ __('since') }} {{ fmtDate(l.from_date) }}</div>
							</div>
							<button type="button" class="ta-link-danger" @click="endLine(l)">{{ __('End') }}</button>
						</li>
					</ul>
					<button type="button" class="mt-2 text-sm font-medium text-[color:var(--il-primary-40)]" @click="openLine(form.user)">
						+ {{ __('Add a manager') }}
					</button>
				</div>
			</div>
			<template #footer>
				<button class="il-btn il-btn-light" @click="memberSheet = false">{{ __('Cancel') }}</button>
				<button class="il-btn il-btn-primary" :disabled="saving || !canSaveMember" @click="saveMember">
					{{ saving ? __('Saving…') : form.isNew && form.mode === 'new' ? __('Create account') : __('Save') }}
				</button>
			</template>
		</Sheet>

		<!-- Add reporting line -->
		<Sheet v-model="lineSheet" :title="__('Add reporting line')">
			<div class="space-y-4">
				<div>
					<div class="ta-label">{{ __('Person') }}</div>
					<div v-if="line.member" class="ta-picked">
						<div class="min-w-0 flex-1 truncate text-sm font-medium">{{ line.member_name || line.member }}</div>
						<button v-if="!line.fixed" type="button" class="text-xs font-medium text-[color:var(--il-primary-40)]" @click="line.member = ''">{{ __('Change') }}</button>
					</div>
					<UserPicker v-else @pick="(u) => Object.assign(line, { member: u.name, member_name: u.full_name })" />
				</div>
				<div>
					<div class="ta-label">{{ __('Reports to') }}</div>
					<div v-if="line.manager" class="ta-picked">
						<div class="min-w-0 flex-1 truncate text-sm font-medium">{{ line.manager_name || line.manager }}</div>
						<button type="button" class="text-xs font-medium text-[color:var(--il-primary-40)]" @click="line.manager = ''">{{ __('Change') }}</button>
					</div>
					<UserPicker v-else @pick="(u) => Object.assign(line, { manager: u.name, manager_name: u.full_name })" />
				</div>
				<div class="grid gap-3 sm:grid-cols-2">
					<label class="block">
						<span class="ta-label">{{ __('Type') }}</span>
						<select v-model="line.line_type" class="ta-select w-full">
							<option v-for="t in data?.line_types || []" :key="t" :value="t">{{ t }}</option>
						</select>
					</label>
					<label class="block">
						<span class="ta-label">{{ __('From') }}</span>
						<input v-model="line.from_date" type="date" class="ta-select w-full" />
					</label>
				</div>
				<p class="text-xs text-[color:var(--il-muted)]">{{ __('Someone can report to two people at once, e.g. a Training Manager and a Performance Manager.') }}</p>
			</div>
			<template #footer>
				<button class="il-btn il-btn-light" @click="lineSheet = false">{{ __('Cancel') }}</button>
				<button class="il-btn il-btn-primary" :disabled="saving || !line.member || !line.manager" @click="saveLine">{{ saving ? __('Saving…') : __('Add') }}</button>
			</template>
		</Sheet>

		<!-- Add extra view -->
		<Sheet v-model="grantSheet" :title="__('Add team view')">
			<div class="space-y-4">
				<div>
					<div class="ta-label">{{ __('Person') }}</div>
					<div v-if="grant.user" class="ta-picked">
						<div class="min-w-0 flex-1 truncate text-sm font-medium">{{ grant.user_name || grant.user }}</div>
						<button type="button" class="text-xs font-medium text-[color:var(--il-primary-40)]" @click="grant.user = ''">{{ __('Change') }}</button>
					</div>
					<UserPicker v-else @pick="(u) => Object.assign(grant, { user: u.name, user_name: u.full_name })" />
				</div>
				<label class="block">
					<span class="ta-label">{{ __('Team they can see') }}</span>
					<select v-model="grant.department" class="ta-select w-full">
						<option v-for="d in data?.departments || []" :key="d.name" :value="d.name">{{ d.name }}</option>
					</select>
				</label>
				<label class="flex items-center gap-2 text-sm">
					<input v-model="grant.can_manage" type="checkbox" class="rounded" />
					{{ __('Can also manage them (assign training)') }}
				</label>
				<label class="block">
					<span class="ta-label">{{ __('Why (optional)') }}</span>
					<input v-model="grant.reason" class="ta-select w-full" :placeholder="__('e.g. trains the Retail Sales batch')" />
				</label>
			</div>
			<template #footer>
				<button class="il-btn il-btn-light" @click="grantSheet = false">{{ __('Cancel') }}</button>
				<button class="il-btn il-btn-primary" :disabled="saving || !grant.user || !grant.department" @click="saveGrant">{{ saving ? __('Saving…') : __('Add') }}</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { call, createResource, toast } from 'frappe-ui'
import { Check, Pencil, Plus, Search, UserPlus } from 'lucide-vue-next'
import Sheet from './Sheet.vue'
import UserPicker from './UserPicker.vue'
import IdentityPanel from '@/components/IdentityPanel.vue'

const res = createResource({ url: 'lms.lms.team_access.get_team_access', auto: true })

// After an email change the person's ID is the new email: keep editing them, refresh the list.
function identityChanged(result) {
	if (result?.user && result.user !== form.user) form.user = result.user
	res.reload()
}
const data = computed(() => res.data)

const tab = ref('people')
const team = ref(null)
const search = ref('')
const onlyUnassigned = ref(false)
const saving = ref(false)

const tabs = computed(() => [
	{ key: 'people', label: __('People'), badge: null },
	{ key: 'lines', label: __('Reporting lines'), badge: null },
	...(data.value?.me.is_super_admin ? [{ key: 'views', label: __('Extra team views'), badge: null }] : []),
])

const scopeLine = computed(() => {
	const me = data.value?.me
	if (!me) return __('Who is in which team, what they can do, and who they report to.')
	if (me.is_super_admin || !me.teams) return __('You are a Super Admin: you manage every team.')
	return `${__('You manage')}: ${me.teams.join(', ')}`
})

const visibleTeams = computed(() => (data.value?.departments || []).filter((d) => d.count || d.can_assign))
const assignableTeams = computed(() => (data.value?.departments || []).filter((d) => d.can_assign))

const people = computed(() => {
	const term = search.value.trim().toLowerCase()
	return (data.value?.members || []).filter(
		(m) =>
			(!team.value || m.departments.some((d) => d.department === team.value)) &&
			(!onlyUnassigned.value || !m.managers.length) &&
			(!term || `${m.full_name} ${m.user}`.toLowerCase().includes(term))
	)
})

const lines = computed(() => {
	const members = new Set(people.value.map((m) => m.user))
	return (data.value?.lines || []).filter((l) => !team.value || members.has(l.member))
})

const roleHelp = [
	{ role: 'User', text: __('Takes courses and CRT. Sees only their own progress.') },
	{ role: 'Instructor', text: __('Teaches and evaluates. Sees the learners they train.') },
	{ role: 'Manager', text: __('Sees their reports’ progress and assigns refreshers from their team.') },
	{ role: 'Admin', text: __('Runs a whole team: adds people, sets managers, sees all team reports.') },
]
const roleLabel = (r) => ({ User: __('Learner'), Instructor: __('Instructor'), Manager: __('Manager'), Admin: __('Team admin') })[r] || r
const shortType = (t) => ({ 'Training Manager': 'TM', 'Performance Manager': 'PM', 'Line Manager': 'L1' })[t] || t

function initials(name) {
	return String(name || '?')
		.split(/[\s.@]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0].toUpperCase())
		.join('')
}

function fmtDate(v) {
	if (!v) return '—'
	const d = new Date(v)
	return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function errorText(e) {
	return e?.messages?.[0] || e?.message || __('Something went wrong.')
}

// ---- Person --------------------------------------------------------------------------------

const memberSheet = ref(false)
const form = reactive({
	isNew: true,
	mode: 'existing',
	user: '',
	full_name: '',
	email: '',
	employee_code: '',
	first_name: '',
	last_name: '',
	access_role: 'User',
	departments: [],
	primary: '',
	managers: [],
})

const canSaveMember = computed(() => {
	if (!form.departments.length) return false
	if (form.isNew && form.mode === 'new') return /.+@.+\..+/.test(form.email) && Boolean(form.first_name)
	return Boolean(form.user)
})

// An admin with one team always adds into it; with several, the current filter is the default.
const defaultTeams = () => {
	if (assignableTeams.value.length === 1) return [assignableTeams.value[0].name]
	return team.value && assignableTeams.value.some((t) => t.name === team.value) ? [team.value] : []
}

function openMember(m) {
	Object.assign(form, {
		isNew: !m,
		mode: 'existing',
		user: m?.user || '',
		full_name: m?.full_name || '',
		email: '',
		first_name: '',
		last_name: '',
		employee_code: '',
		access_role: m?.access_role || 'User',
		departments: m ? m.departments.filter((d) => assignableTeams.value.some((t) => t.name === d.department)).map((d) => d.department) : defaultTeams(),
		primary: m?.departments.find((d) => d.is_primary)?.department || '',
		managers: m?.managers || [],
	})
	memberSheet.value = true
}

function pickNew(u) {
	const existing = data.value.members.find((m) => m.user === u.name)
	if (existing) return openMember(existing)
	Object.assign(form, { user: u.name, full_name: u.full_name })
}

function toggleTeam(name) {
	const i = form.departments.indexOf(name)
	if (i >= 0) form.departments.splice(i, 1)
	else form.departments.push(name)
	if (!form.departments.includes(form.primary)) form.primary = form.departments[0] || ''
}

async function saveMember() {
	saving.value = true
	try {
		const common = { access_role: form.access_role, departments: form.departments, primary: form.primary || form.departments[0] }
		if (form.isNew && form.mode === 'new') {
			await call('lms.lms.team_access.create_account', {
				...common,
				email: form.email,
				first_name: form.first_name,
				last_name: form.last_name,
				employee_code: form.employee_code || null,
			})
			toast.success(__('Account created. Welcome email sent.'))
		} else {
			await call('lms.lms.team_access.save_member', { ...common, user: form.user })
			toast.success(__('Saved'))
		}
		memberSheet.value = false
		await res.reload()
	} catch (e) {
		toast.error(errorText(e))
	} finally {
		saving.value = false
	}
}

// ---- Reporting lines -------------------------------------------------------------------------

const lineSheet = ref(false)
const line = reactive({ member: '', member_name: '', manager: '', manager_name: '', line_type: 'Training Manager', from_date: '', fixed: false })

function openLine(member) {
	const m = member && data.value.members.find((x) => x.user === member)
	Object.assign(line, {
		member: member || '',
		member_name: m?.full_name || '',
		manager: '',
		manager_name: '',
		line_type: 'Training Manager',
		from_date: new Date().toISOString().slice(0, 10),
		fixed: Boolean(member),
	})
	lineSheet.value = true
}

async function saveLine() {
	saving.value = true
	try {
		await call('lms.lms.team_access.add_reporting_line', {
			member: line.member,
			manager: line.manager,
			line_type: line.line_type,
			from_date: line.from_date,
		})
		toast.success(__('Reporting line added'))
		lineSheet.value = false
		await res.reload()
		syncOpenMember()
	} catch (e) {
		toast.error(errorText(e))
	} finally {
		saving.value = false
	}
}

async function endLine(l) {
	const who = l.member_name || l.member
	const mgr = l.manager_name || l.manager
	if (!window.confirm(`${__('End this line?')} ${mgr} ${__('will stop seeing')} ${who}.`)) return
	try {
		await call('lms.lms.team_access.end_line', { name: l.name })
		toast.success(__('Line ended'))
		await res.reload()
		syncOpenMember()
	} catch (e) {
		toast.error(errorText(e))
	}
}

function syncOpenMember() {
	if (!memberSheet.value || form.isNew) return
	form.managers = data.value.members.find((m) => m.user === form.user)?.managers || []
}

// ---- Extra views -----------------------------------------------------------------------------

const grantSheet = ref(false)
const grant = reactive({ user: '', user_name: '', department: '', can_manage: false, reason: '' })

function openGrant() {
	Object.assign(grant, { user: '', user_name: '', department: team.value || '', can_manage: false, reason: '' })
	grantSheet.value = true
}

async function saveGrant() {
	saving.value = true
	try {
		await call('lms.lms.team_access.add_view_grant', {
			user: grant.user,
			department: grant.department,
			can_manage: grant.can_manage ? 1 : 0,
			reason: grant.reason,
		})
		toast.success(__('View added'))
		grantSheet.value = false
		await res.reload()
	} catch (e) {
		toast.error(errorText(e))
	} finally {
		saving.value = false
	}
}

async function revokeGrant(g) {
	if (!window.confirm(__('Remove this view?'))) return
	try {
		await call('lms.lms.team_access.revoke_view_grant', { name: g.name })
		await res.reload()
	} catch (e) {
		toast.error(errorText(e))
	}
}
</script>

<style scoped>
.ta-teams {
	display: flex;
	gap: 0.6rem;
	overflow-x: auto;
	padding-bottom: 0.25rem;
}

.ta-team {
	display: inline-flex;
	flex-shrink: 0;
	align-items: center;
	gap: 0.5rem;
	height: 2.5rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	padding: 0 0.5rem 0 1rem;
	background: #fff;
	color: var(--il-ink);
}

.ta-team.is-active {
	border-color: #00254c;
	background: #00254c;
	color: #fff;
}

.ta-count {
	display: grid;
	min-width: 1.6rem;
	height: 1.6rem;
	place-items: center;
	border-radius: 999px;
	padding: 0 0.4rem;
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-size: 0.75rem;
	font-weight: 600;
}

.ta-team.is-active .ta-count {
	background: rgba(255, 255, 255, 0.18);
	color: #fff;
}

.ta-tabs {
	display: flex;
	gap: 1.5rem;
	margin: 1.25rem 0 0.75rem;
	border-bottom: 1px solid var(--il-neutral-90);
}

.ta-tabs button {
	margin-bottom: -1px;
	border-bottom: 2px solid transparent;
	padding: 0.5rem 0;
	color: var(--il-muted);
	font-size: 0.9375rem;
	font-weight: 500;
}

.ta-tabs button.is-active {
	border-color: var(--il-primary-50);
	color: var(--il-primary-40);
}

.ta-badge {
	margin-left: 0.3rem;
	border-radius: 999px;
	padding: 0 0.4rem;
	background: var(--il-warning-95);
	color: var(--il-warning-50);
	font-size: 0.7rem;
}

.ta-search {
	display: flex;
	flex: 1;
	min-width: 12rem;
	align-items: center;
	gap: 0.5rem;
	height: 2.4rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	padding: 0 0.9rem;
}

.ta-search input {
	flex: 1;
	border: 0;
	padding: 0;
	background: transparent;
	box-shadow: none;
	font-size: 0.875rem;
}

.ta-row {
	display: flex;
	align-items: center;
	gap: 0.85rem;
	border-bottom: 1px solid var(--il-neutral-95);
	padding: 0.7rem 1rem;
}

.ta-row:last-child {
	border-bottom: 0;
}

.ta-row.is-inactive {
	opacity: 0.55;
}

.ta-avatar {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 2.25rem;
	height: 2.25rem;
	border-radius: 999px;
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-size: 0.75rem;
	font-weight: 600;
}

.ta-avatar.is-super {
	background: #00254c;
	color: #fff;
}

.ta-role {
	flex-shrink: 0;
	border-radius: 999px;
	padding: 0.15rem 0.6rem;
	background: var(--il-neutral-95);
	color: var(--il-muted);
	font-size: 0.75rem;
	font-weight: 600;
	white-space: nowrap;
}

.ta-role.is-instructor {
	background: #eef5ff;
	color: #0062cc;
}

.ta-role.is-manager {
	background: #f3efff;
	color: #5b3fd6;
}

.ta-role.is-admin {
	background: #fff4d6;
	color: #8a5a00;
}

.ta-role.is-super {
	background: #00254c;
	color: #fff;
}

.ta-teams-cell {
	display: none;
	width: 15rem;
	flex-shrink: 0;
	flex-wrap: wrap;
	gap: 0.3rem;
}

.ta-mgr-cell {
	display: none;
	width: 11rem;
	flex-shrink: 0;
}

.ta-row > .ta-role {
	width: 7.25rem;
	text-align: center;
}

@media (min-width: 768px) {
	.ta-teams-cell {
		display: flex;
	}

	.ta-mgr-cell {
		display: block;
	}
}

.ta-chip {
	border-radius: 6px;
	padding: 0.1rem 0.45rem;
	background: var(--il-neutral-95);
	color: var(--il-ink);
	font-size: 0.72rem;
}

.ta-chip.is-primary {
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-weight: 600;
}

.ta-edit {
	display: grid;
	width: 2.25rem;
	height: 2.25rem;
	flex-shrink: 0;
	place-items: center;
	border-radius: 999px;
	color: var(--il-primary-40);
}

.ta-edit:hover {
	background: #f4f9ff;
}

.ta-link-danger {
	flex-shrink: 0;
	border-radius: 999px;
	padding: 0.3rem 0.8rem;
	color: #d12b2b;
	font-size: 0.8125rem;
	font-weight: 500;
}

.ta-link-danger:hover {
	background: #fff1f1;
}

.ta-help {
	border: 1px solid var(--il-neutral-90);
	border-radius: 16px;
	padding: 0.85rem 1rem;
	background: #fff;
}

.ta-label {
	display: block;
	margin-bottom: 0.4rem;
	color: var(--il-ink);
	font-size: 0.8125rem;
	font-weight: 600;
}

.ta-picked {
	display: flex;
	align-items: center;
	gap: 0.6rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0.5rem 0.75rem;
}

.ta-option {
	display: flex;
	flex-direction: column;
	gap: 0.2rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0.6rem 0.75rem;
	cursor: pointer;
}

.ta-option.is-on {
	border-color: var(--il-primary-50);
	background: #f4f9ff;
	box-shadow: 0 0 0 1px var(--il-primary-50);
}

.ta-option.is-off {
	cursor: not-allowed;
	opacity: 0.55;
}

.ta-pick-team {
	display: inline-flex;
	align-items: center;
	gap: 0.3rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	padding: 0.35rem 0.85rem;
	color: var(--il-ink);
	font-size: 0.8125rem;
}

.ta-pick-team.is-on {
	border-color: var(--il-primary-50);
	background: var(--il-primary-50);
	color: #fff;
}

.ta-seg {
	display: inline-flex;
	gap: 0.25rem;
	border-radius: 999px;
	padding: 0.2rem;
	background: var(--il-neutral-95);
}

.ta-seg button {
	border-radius: 999px;
	padding: 0.35rem 0.9rem;
	color: var(--il-muted);
	font-size: 0.8125rem;
	font-weight: 500;
}

.ta-seg button.is-on {
	background: #fff;
	color: var(--il-primary-40);
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.ta-select {
	height: 2.5rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 12px;
	padding: 0 0.75rem;
	background-color: #fff;
	font-size: 0.875rem;
}
</style>
