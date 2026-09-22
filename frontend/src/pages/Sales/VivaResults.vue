<template>
	<div class="vx-page">
		<header class="vx-head">
			<div>
				<h1>{{ __('Voice vivas') }}</h1>
				<p>{{ __('Day-by-day courses end each day with a spoken viva. Open any attempt for answers, timing and watch-outs.') }}</p>
			</div>
		</header>

		<div v-if="results.data && !results.data.configured" class="vx-note">
			{{ __('The voice viva is not switched on yet (Gemini API key missing), so learners are not being asked to take it.') }}
		</div>

		<!-- Needs attention: learners out of attempts -->
		<section v-if="blocked.length" class="vx-card vx-attention">
			<div class="vx-card-head">
				<AlertTriangle class="h-4 w-4" />
				<h2>{{ __('Out of attempts') }}</h2>
				<span class="vx-count">{{ blocked.length }}</span>
			</div>
			<p class="vx-muted">{{ __('These learners failed all their attempts for a day. Review the latest report with them, then unlock three more.') }}</p>
			<ul class="vx-blocked">
				<li v-for="b in blocked" :key="`${b.member}-${b.crt_number}`">
					<span class="vx-avatar">{{ initials(b.member_name) }}</span>
					<div class="flex-1 min-w-0">
						<div class="vx-name">{{ b.member_name }}</div>
						<div class="vx-muted">{{ multiCourse ? `${b.course_title} · ` : '' }}{{ __('Day') }} {{ b.day }} · {{ b.attempts_used }} {{ __('attempts') }} · {{ __('best') }} {{ score(b.best_score) }}%</div>
					</div>
					<button v-if="b.can_unlock" class="vx-btn" :disabled="busy === key(b)" @click="unlock(b)">
						{{ busy === key(b) ? __('Unlocking…') : __('Unlock 3 more') }}
					</button>
				</li>
			</ul>
		</section>

		<!-- Filters -->
		<div class="vx-filters">
			<select v-if="multiCourse" v-model="filters.course" class="vx-select">
				<option value="">{{ __('All courses') }}</option>
				<option v-for="c in courses" :key="c.name" :value="c.name">{{ c.title }}</option>
			</select>
			<button v-for="d in [0, 1, 2, 3, 4, 5]" :key="d" class="vx-chip" :class="{ 'is-on': filters.day === d }" @click="filters.day = d">
				{{ d ? `${__('Day')} ${d}` : __('All days') }}
			</button>
			<select v-model="filters.status" class="vx-select">
				<option value="">{{ __('All results') }}</option>
				<option value="Passed">{{ __('Passed') }}</option>
				<option value="Not Passed">{{ __('Not yet') }}</option>
			</select>
			<input v-model="filters.search" class="vx-search" :placeholder="__('Search learner')" />
		</div>

		<!-- Attempts -->
		<section class="vx-card vx-table">
			<div v-if="results.loading && !rows.length" class="vx-muted p-6">{{ __('Loading…') }}</div>
			<div v-else-if="!rows.length" class="vx-empty">
				<Mic class="h-6 w-6" />
				<p>{{ __('No vivas yet for this filter.') }}</p>
			</div>
			<template v-else>
				<div class="vx-row vx-row-head">
					<span>{{ __('Learner') }}</span>
					<span>{{ __('Day') }}</span>
					<span>{{ __('Score') }}</span>
					<span class="vx-hide-sm">{{ __('Knowledge') }}</span>
					<span class="vx-hide-sm">{{ __('Fluency') }}</span>
					<span>{{ __('Result') }}</span>
					<span class="vx-hide-sm">{{ __('Watch-outs') }}</span>
				</div>
				<button v-for="r in rows" :key="r.name" class="vx-row" @click="$router.push({ name: 'VivaReport', params: { attempt: r.name } })">
					<span class="vx-learner">
						<span class="vx-avatar">{{ initials(r.member_name) }}</span>
						<span class="min-w-0">
							<span class="vx-name">{{ r.member_name }}</span>
							<span class="vx-muted">{{ multiCourse ? `${r.course_title} · ` : '' }}{{ __('Attempt') }} {{ r.attempt_no }} · {{ formatDate(r.started_at) }}</span>
						</span>
					</span>
					<span>{{ r.crt_number }}</span>
					<span><b>{{ score(r.overall_score) }}</b></span>
					<span class="vx-hide-sm">{{ score(r.knowledge_score) }}</span>
					<span class="vx-hide-sm">{{ score(r.fluency_score) }}</span>
					<span><span class="vx-pill" :class="r.status === 'Passed' ? 'is-good' : r.status === 'Not Passed' ? 'is-bad' : ''">{{ label(r.status) }}</span></span>
					<span class="vx-hide-sm">
						<span v-if="r.flag_count" class="vx-flag"><AlertTriangle class="h-3.5 w-3.5" />{{ r.flag_count }}</span>
						<span v-else class="vx-muted">—</span>
					</span>
				</button>
			</template>
		</section>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { call, createResource, debounce } from 'frappe-ui'
import { AlertTriangle, Mic } from 'lucide-vue-next'

const filters = reactive({ day: 0, status: '', search: '', course: '' })
const busy = ref('')

const results = createResource({
	url: 'lms.lms.sales_viva.get_viva_results',
	makeParams: () => ({ course: filters.course || null, crt_number: filters.day || null, status: filters.status || null, search: filters.search || null }),
	auto: true,
})
const reload = debounce(() => results.reload(), 300)
watch(() => [filters.day, filters.status, filters.course], () => results.reload())
watch(() => filters.search, reload)

const rows = computed(() => results.data?.rows || [])
const blocked = computed(() => results.data?.blocked || [])
const courses = computed(() => results.data?.courses || [])
const multiCourse = computed(() => courses.value.length > 1)

const key = (b) => `${b.member}-${b.course}-${b.day}`
const score = (v) => (v == null ? '—' : Math.round(v))
const initials = (name) => (name || '?').split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
const label = (s) => ({ Passed: __('Passed'), 'Not Passed': __('Not yet'), Scoring: __('Scoring') })[s] || s
const formatDate = (d) => (d ? new Date(String(d).replace(' ', 'T')).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '')

async function unlock(b) {
	busy.value = key(b)
	try {
		await call('lms.lms.sales_viva.grant_attempts', { member: b.member, course: b.course, day: b.day, reason: 'Unlocked from Voice vivas' })
		results.reload()
	} finally {
		busy.value = ''
	}
}
</script>

<style scoped>
.vx-page {
	max-width: 1112px;
	margin: 0 auto;
	padding: 28px 24px 64px;
}
.vx-head h1 {
	font-size: 28px;
	line-height: 36px;
	font-weight: 600;
	color: #080e14;
}
.vx-head p,
.vx-muted {
	font-size: 13px;
	color: #52565c;
}
.vx-note {
	margin-top: 16px;
	padding: 12px 16px;
	border-radius: 16px;
	font-size: 14px;
	background: #fff8e6;
	border: 1px solid #ffcf66;
	color: #8a5a00;
}
.vx-card {
	margin-top: 18px;
	border-radius: 24px;
	background: #fff;
	border: 1px solid #e6e7e8;
	box-shadow: 0 1px 12px rgba(0, 0, 0, 0.12);
}
.vx-attention {
	padding: 18px 22px;
	background: #fffdf5;
	border-color: #ffcf66;
}
.vx-card-head {
	display: flex;
	align-items: center;
	gap: 8px;
	color: #8a5a00;
}
.vx-card-head h2 {
	font-size: 16px;
	font-weight: 600;
	color: #080e14;
}
.vx-count {
	padding: 1px 9px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #ffeecc;
}
.vx-blocked li {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 0;
	border-bottom: 1px solid #f2f2f2;
}
.vx-blocked li:last-child {
	border-bottom: 0;
}
.vx-avatar {
	width: 36px;
	height: 36px;
	flex: none;
	display: grid;
	place-items: center;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #e6f2ff;
	color: #0062cc;
}
.vx-name {
	display: block;
	font-size: 14px;
	font-weight: 500;
	color: #080e14;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.vx-btn {
	height: 36px;
	padding: 0 18px;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	color: #fff;
	background: #027bff;
	flex: none;
}
.vx-btn:disabled {
	opacity: 0.5;
}
.vx-filters {
	margin-top: 22px;
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	align-items: center;
}
.vx-chip {
	height: 36px;
	padding: 0 16px;
	border-radius: 999px;
	font-size: 14px;
	border: 1px solid #e6e7e8;
	background: #fff;
	color: #080e14;
}
.vx-chip.is-on {
	background: #00254c;
	border-color: #00254c;
	color: #fff;
}
.vx-select,
.vx-search {
	height: 36px;
	border-radius: 999px;
	border: 1px solid #e6e7e8;
	background: #fff;
	font-size: 14px;
	padding: 0 14px;
}
.vx-search {
	flex: 1;
	min-width: 180px;
}
.vx-table {
	overflow: hidden;
}
.vx-row {
	width: 100%;
	display: grid;
	grid-template-columns: minmax(0, 2.4fr) 0.5fr 0.6fr 0.8fr 0.8fr 0.9fr 0.8fr;
	align-items: center;
	gap: 10px;
	padding: 12px 20px;
	text-align: left;
	font-size: 14px;
	border-bottom: 1px solid #f2f2f2;
}
button.vx-row:hover {
	background: #f4f9ff;
}
.vx-row-head {
	font-size: 12px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: #52565c;
	background: #f4f9ff;
}
.vx-learner {
	display: flex;
	align-items: center;
	gap: 10px;
	min-width: 0;
}
.vx-pill {
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #f2f2f2;
	color: #52565c;
}
.vx-pill.is-good {
	background: #d6f4de;
	color: #04742d;
}
.vx-pill.is-bad {
	background: #fef0f0;
	color: #b42323;
}
.vx-flag {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 9px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #ffeecc;
	color: #8a5a00;
}
.vx-empty {
	display: grid;
	justify-items: center;
	gap: 8px;
	padding: 40px;
	color: #85878a;
	font-size: 14px;
}
@media (max-width: 767px) {
	.vx-page {
		padding: 20px 16px 48px;
	}
	.vx-row {
		grid-template-columns: minmax(0, 1fr) 40px 44px 76px;
		padding: 12px 14px;
	}
	.vx-hide-sm {
		display: none;
	}
}
</style>
