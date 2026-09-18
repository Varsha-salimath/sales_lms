<template>
	<div class="il-page min-h-full pb-12">
		<nav class="flex items-center gap-1.5 pt-5 text-sm">
			<router-link :to="{ name: 'LearnerReports' }" class="text-[color:var(--il-primary-40)]">{{ __('Learner reports') }}</router-link>
			<span class="text-[color:var(--il-neutral-60)]">/</span>
			<span class="text-[color:var(--il-muted)]">{{ learner?.employee_name || __('Report card') }}</span>
		</nav>

		<div v-if="report.loading && !report.data" class="mt-4 space-y-4">
			<div class="h-28 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="h-44 animate-pulse rounded-3xl bg-[#e6e7e8]" />
		</div>
		<div v-else-if="report.error" class="il-card mt-4 p-8 text-center text-sm text-[color:var(--il-error-50)]">
			{{ report.error.messages?.[0] || __('Could not load this report card.') }}
		</div>

		<template v-else-if="learner">
			<!-- Profile header (PTM style) -->
			<section class="il-card mt-3 overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 bg-[#f4f9ff] px-6 py-4">
					<div class="flex items-center gap-3">
						<span class="rc-avatar">{{ initials(learner.employee_name) }}</span>
						<div>
							<h1 class="text-xl font-semibold text-[color:var(--il-ink)]">{{ learner.employee_name }}</h1>
							<p class="text-sm text-[color:var(--il-muted)]">{{ learner.email }}</p>
						</div>
					</div>
					<span class="text-xs text-[color:var(--il-muted)]">{{ __('Sales CRT report card') }}</span>
				</div>
				<div class="grid grid-cols-2 gap-x-6 gap-y-3 px-6 py-4 text-sm sm:grid-cols-4">
					<div><span class="rc-meta">{{ __('Batch start') }}</span>{{ fmtDate(learner.batch_start) }}</div>
					<div><span class="rc-meta">{{ __('Location') }}</span>{{ learner.location || '—' }}</div>
					<div><span class="rc-meta">{{ __('Training manager') }}</span>{{ managerName(learner.training_manager) }}</div>
					<div>
						<span class="rc-meta">{{ __('Rank in batch') }}</span>
						<template v-if="batch.rank">#{{ batch.rank }} <span class="text-[color:var(--il-muted)]">{{ __('of') }} {{ batch.ranked }}</span></template>
						<template v-else>—</template>
					</div>
				</div>
			</section>

			<!-- Highlights -->
			<section class="il-card mt-6 p-5">
				<h2 class="rc-title">{{ __('Highlights') }}</h2>
				<div class="mt-3 grid gap-5 lg:grid-cols-[auto_1fr] lg:items-center">
					<div class="flex items-center gap-4 lg:border-e lg:border-[color:var(--il-neutral-90)] lg:pe-8">
						<div class="rc-donut" :style="{ '--p': learner.readiness || 0, '--c': bandStyle(learner.readiness_band).dot }">
							<span>{{ fmtPct(learner.readiness) }}</span>
						</div>
						<div>
							<div class="text-base font-medium text-[color:var(--il-ink)]">{{ __('Readiness') }}</div>
							<span class="rc-chip" :style="chip(learner.readiness_band)">{{ bandStyle(learner.readiness_band).label }}</span>
							<div class="mt-1 text-xs text-[color:var(--il-muted)]">{{ __('Batch avg') }} {{ fmtPct(stats.readiness?.avg) }}</div>
						</div>
					</div>
					<div class="rc-insights">
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2">
								<Sparkles class="h-4 w-4 text-[#6D4AFF]" />
								<span class="text-sm font-medium text-[#5B3FD6]">{{ __('Insights') }}</span>
							</div>
							<span class="rc-trend" :class="trendClass">{{ trendLabel }}</span>
						</div>
						<div class="mt-2 grid gap-3 sm:grid-cols-2">
							<div>
								<div class="text-xs font-semibold uppercase tracking-wide text-[#146C31]">{{ __('Strengths') }}</div>
								<ul class="mt-1 space-y-1">
									<li v-for="(s, i) in insights.strengths" :key="i" class="rc-li">{{ s }}</li>
									<li v-if="!insights.strengths?.length" class="rc-li text-[color:var(--il-muted)]">{{ __('No clear strengths yet.') }}</li>
								</ul>
							</div>
							<div>
								<div class="text-xs font-semibold uppercase tracking-wide text-[#B42323]">{{ __('Focus areas') }}</div>
								<ul class="mt-1 space-y-1">
									<li v-for="(g, i) in insights.gaps" :key="i" class="rc-li">{{ g }}</li>
									<li v-if="!insights.gaps?.length" class="rc-li text-[color:var(--il-muted)]">{{ __('No gaps against the batch.') }}</li>
								</ul>
							</div>
						</div>
					</div>
				</div>
			</section>

			<!-- Tabs -->
			<div class="rc-tabs mt-6">
				<button v-for="t in tabs" :key="t.key" :class="{ 'is-active': tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
			</div>

			<!-- Overview -->
			<section v-if="tab === 'overview'" class="il-card mt-4 p-5">
				<h2 class="rc-title">{{ __('Summary') }}</h2>
				<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
					<div v-for="c in summaryCards" :key="c.key" class="rc-sum" :style="{ background: bandStyle(c.band).soft, borderColor: bandStyle(c.band).bg }">
						<div class="text-sm text-[color:var(--il-ink)]">{{ c.label }}</div>
						<div class="mt-1 text-2xl font-semibold" :style="{ color: bandStyle(c.band).text }">
							{{ fmt(c.value) }}<small class="text-sm font-normal text-[color:var(--il-muted)]">/{{ c.max }}</small>
						</div>
						<div class="mt-2 flex items-center gap-1 text-xs" :class="deltaClass(c.value, c.avg)">
							<component :is="deltaIcon(c.value, c.avg)" class="h-3.5 w-3.5" />
							{{ deltaText(c.value, c.avg) }}
						</div>
					</div>
				</div>
				<div class="mt-6 grid gap-4 lg:grid-cols-2">
					<div>
						<h3 class="rc-sub">{{ __('Test scores vs batch') }}</h3>
						<div class="mt-3 space-y-3">
							<ScoreBar v-for="m in testMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :avg="stats[m.key]?.avg" :band="learner.scores[m.key]?.band" />
						</div>
					</div>
					<div>
						<h3 class="rc-sub">{{ __('Calling funnel') }}</h3>
						<Funnel class="mt-3" :learner="learner" :stats="stats" />
					</div>
				</div>
			</section>

			<!-- Intent & Skill -->
			<section v-if="tab === 'intent'" class="il-card mt-4 p-5">
				<h2 class="rc-title">{{ __('Intent & Skill') }}</h2>
				<p class="mt-1 text-sm text-[color:var(--il-muted)]">{{ __('Where this learner sits against the batch: lowest, average and highest.') }}</p>
				<div class="mt-5 space-y-6">
					<Benchmark v-for="m in intentMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :stat="stats[m.key]" :band="learner.scores[m.key]?.band" />
				</div>
			</section>

			<!-- Calling -->
			<section v-if="tab === 'calling'" class="il-card mt-4 p-5">
				<h2 class="rc-title">{{ __('Calling performance') }}</h2>
				<div class="mt-4 grid gap-3 sm:grid-cols-3">
					<div class="rc-kpi"><span>{{ fmtPct(learner.connect_rate) }}</span>{{ __('Connect rate') }} <small>{{ __('avg') }} {{ fmtPct(stats.connect_rate?.avg) }}</small></div>
					<div class="rc-kpi"><span>{{ fmtPct(learner.booking_rate) }}</span>{{ __('Booking rate') }} <small>{{ __('avg') }} {{ fmtPct(stats.booking_rate?.avg) }}</small></div>
					<div class="rc-kpi"><span>{{ fmtPct(learner.show_rate) }}</span>{{ __('Catered / booked') }} <small>{{ __('avg') }} {{ fmtPct(stats.show_rate?.avg) }}</small></div>
				</div>
				<Funnel class="mt-6" :learner="learner" :stats="stats" />
				<div class="mt-5 rounded-2xl bg-[color:var(--il-neutral-95)] px-4 py-3 text-sm">
					<Clock class="me-1 inline h-4 w-4 text-[color:var(--il-primary-40)]" />
					{{ __('Talk time') }}: <strong>{{ learner.talk_time || '—' }}</strong>
					<span class="text-[color:var(--il-muted)]"> · {{ __('batch avg') }} {{ fmtDuration(stats.talk_seconds?.avg) }}</span>
				</div>
			</section>

			<!-- Test scores -->
			<section v-if="tab === 'tests'" class="il-card mt-4 p-5">
				<h2 class="rc-title">{{ __('Test scores') }} <span class="text-sm font-normal text-[color:var(--il-muted)]">({{ __('out of 20') }})</span></h2>
				<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
					<div v-for="m in testMetrics" :key="m.key" class="rc-sum" :style="{ background: bandStyle(learner.scores[m.key]?.band).soft, borderColor: bandStyle(learner.scores[m.key]?.band).bg }">
						<div class="text-sm">{{ m.label }}</div>
						<div class="mt-1 text-2xl font-semibold" :style="{ color: bandStyle(learner.scores[m.key]?.band).text }">{{ fmt(learner[m.key]) }}</div>
						<div class="text-xs text-[color:var(--il-muted)]">{{ bandStyle(learner.scores[m.key]?.band).label }}</div>
					</div>
				</div>
				<div class="mt-6 space-y-6">
					<Benchmark v-for="m in testMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :stat="stats[m.key]" :band="learner.scores[m.key]?.band" />
				</div>
			</section>

			<p class="mt-4 text-xs text-[color:var(--il-muted)]">{{ BAND_RULES }}. {{ __('Batch') }} = {{ batch.size }} {{ __('learners who started on') }} {{ fmtDate(batch.batch_start) }}.</p>
		</template>
	</div>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { createResource } from 'frappe-ui'
import { ArrowDownRight, ArrowUpRight, Clock, Minus, Sparkles } from 'lucide-vue-next'
import { BAND_RULES, bandStyle, fmt, fmtDate, fmtDuration, fmtPct, initials, managerName } from './reportUtils'

const props = defineProps({ name: { type: String, required: true } })

const report = createResource({
	url: 'lms.lms.learner_report.get_learner_report',
	makeParams: () => ({ name: props.name }),
	auto: true,
})

const learner = computed(() => report.data?.learner)
const stats = computed(() => report.data?.stats || {})
const batch = computed(() => report.data?.batch || {})
const insights = computed(() => report.data?.insights || { strengths: [], gaps: [] })
const metrics = computed(() => report.data?.metrics || [])
const intentMetrics = computed(() => metrics.value.filter((m) => m.group === 'intent'))
const testMetrics = computed(() => metrics.value.filter((m) => m.group === 'tests'))

const tab = ref('overview')
const tabs = [
	{ key: 'overview', label: __('Overview') },
	{ key: 'intent', label: __('Intent & Skill') },
	{ key: 'calling', label: __('Calling') },
	{ key: 'tests', label: __('Test Scores') },
]

const summaryCards = computed(() => {
	const l = learner.value
	if (!l) return []
	const productBand = l.product_avg == null ? null : bandOf((l.product_avg / 20) * 100)
	return [
		{ key: 'attendance_days', label: __('Attendance days'), value: l.attendance_days, max: 15, avg: stats.value.attendance_days?.avg, band: l.scores.attendance_days?.band },
		{ key: 'ai_mock_score', label: __('AI mock'), value: l.ai_mock_score, max: 20, avg: stats.value.ai_mock_score?.avg, band: l.scores.ai_mock_score?.band },
		{ key: 'audit_score', label: __('Audit'), value: l.audit_score, max: 20, avg: stats.value.audit_score?.avg, band: l.scores.audit_score?.band },
		{ key: 'product_avg', label: __('Product tests avg'), value: l.product_avg, max: 20, avg: stats.value.product_avg?.avg, band: productBand },
	]
})

function bandOf(p) {
	for (const { min, key } of report.data?.bands || []) if (p >= min) return key
	return 'needs_improvement'
}

const trendLabel = computed(() => {
	const band = learner.value?.readiness_band
	return { excellent: __('Certification ready'), good: __('On track'), average: __('Needs support'), needs_improvement: __('At risk') }[band] || __('Not scored')
})
const trendClass = computed(() => `is-${learner.value?.readiness_band || 'none'}`)

function chip(band) {
	const s = bandStyle(band)
	return { background: s.soft, color: s.text, borderColor: s.bg }
}
function deltaText(v, avg) {
	if (v == null || avg == null) return __('No batch comparison')
	const d = Math.round((v - avg) * 10) / 10
	if (d === 0) return __('Same as batch avg')
	return `${d > 0 ? '+' : ''}${d} ${__('vs batch avg')} (${fmt(avg)})`
}
function deltaClass(v, avg) {
	if (v == null || avg == null || v === avg) return 'text-[color:var(--il-muted)]'
	return v > avg ? 'text-[#04742D]' : 'text-[#D12B2B]'
}
function deltaIcon(v, avg) {
	if (v == null || avg == null || v === avg) return Minus
	return v > avg ? ArrowUpRight : ArrowDownRight
}

// Horizontal score bar with a batch-average marker.
const ScoreBar = (p) => {
	const pct = p.value == null ? 0 : Math.min(100, (p.value / p.max) * 100)
	const avgPct = p.avg == null ? null : Math.min(100, (p.avg / p.max) * 100)
	const s = bandStyle(p.band)
	return h('div', [
		h('div', { class: 'flex items-center justify-between text-sm' }, [
			h('span', { class: 'text-[color:var(--il-ink)]' }, p.label),
			h('span', { class: 'font-semibold tabular-nums', style: { color: s.text } }, `${fmt(p.value)} / ${p.max}`),
		]),
		h('div', { class: 'relative mt-1.5 h-2.5 rounded-full bg-[#eef0f3]' }, [
			h('div', { class: 'h-full rounded-full', style: { width: `${pct}%`, background: s.dot } }),
			avgPct == null
				? null
				: h('div', { class: 'rc-avg-mark', style: { left: `${avgPct}%` }, title: `${__('Batch avg')} ${fmt(p.avg)}` }),
		]),
	])
}
ScoreBar.props = ['label', 'value', 'max', 'avg', 'band']

// Mock-test "Score Benchmark" strip: lowest · average · highest · you.
const Benchmark = (p) => {
	const at = (v) => (v == null ? null : `${Math.min(100, (v / p.max) * 100)}%`)
	const s = bandStyle(p.band)
	const st = p.stat || {}
	const marker = (v, cls, label) =>
		v == null ? null : h('div', { class: `rc-bm ${cls}`, style: { left: at(v) } }, [h('span', { class: 'rc-bm-label' }, `${label} ${fmt(v)}`)])
	return h('div', [
		h('div', { class: 'flex items-center justify-between text-sm' }, [
			h('span', { class: 'font-medium text-[color:var(--il-ink)]' }, p.label),
			h('span', { class: 'rc-chip', style: chip(p.band) }, `${fmt(p.value)} / ${p.max} · ${s.label}`),
		]),
		h('div', { class: 'rc-bm-track mt-7' }, [
			marker(st.min, 'is-low', __('Lowest')),
			marker(st.avg, 'is-avg', __('Avg')),
			marker(st.max, 'is-high', __('Highest')),
			marker(p.value, 'is-you', __('You')),
		]),
		h('div', { class: 'mt-1 flex justify-between text-[11px] text-[color:var(--il-neutral-60)]' }, [h('span', '0'), h('span', String(p.max))]),
	])
}
Benchmark.props = ['label', 'value', 'max', 'stat', 'band']

// DC → CC → Booked → Catered.
const Funnel = (p) => {
	const l = p.learner
	const steps = [
		{ label: __('Dialled (DC)'), value: l.dc, avg: p.stats.dc?.avg },
		{ label: __('Connected (CC)'), value: l.cc, avg: p.stats.cc?.avg, rate: l.connect_rate },
		{ label: __('Booked'), value: l.booked, avg: p.stats.booked?.avg, rate: l.booking_rate },
		{ label: __('Catered'), value: l.catered, avg: p.stats.catered?.avg, rate: l.show_rate },
	]
	const top = Math.max(...steps.map((s) => Number(s.value) || 0), 1)
	const width = (s) => Math.max(4, ((Number(s.value) || 0) / top) * 100)
	return h(
		'div',
		{ class: 'space-y-2' },
		steps.map((s, i) =>
			h('div', { class: 'flex items-center gap-3' }, [
				h('div', { class: 'w-32 shrink-0 text-sm text-[color:var(--il-ink)]' }, s.label),
				h('div', { class: 'relative h-8 flex-1 overflow-hidden rounded-xl bg-[#eef5ff]' }, [
					h('div', {
						class: 'h-full rounded-xl',
						style: { width: `${width(s)}%`, background: ['#027BFF', '#3395FF', '#67B0FF', '#99CAFF'][i] },
					}),
					// White on a wide bar, dark just past the end of a short one.
					width(s) > 18
						? h('span', { class: 'absolute inset-y-0 left-3 flex items-center text-sm font-semibold text-white' }, fmt(s.value))
						: h('span', { class: 'absolute inset-y-0 flex items-center text-sm font-semibold text-[color:var(--il-ink)]', style: { left: `calc(${width(s)}% + 0.5rem)` } }, fmt(s.value)),
				]),
				h('div', { class: 'w-24 shrink-0 text-right text-xs text-[color:var(--il-muted)]' }, s.rate == null ? `${__('avg')} ${fmt(s.avg)}` : `${fmtPct(s.rate)} ${__('conv.')}`),
			])
		)
	)
}
Funnel.props = ['learner', 'stats']
</script>

<style scoped>
.rc-avatar {
	display: grid;
	place-items: center;
	width: 3rem;
	height: 3rem;
	border-radius: 999px;
	background: var(--il-primary-50);
	color: #fff;
	font-weight: 600;
}

.rc-meta {
	display: block;
	color: var(--il-muted);
	font-size: 0.75rem;
}

.rc-title {
	margin: 0;
	color: var(--il-ink);
	font-size: 1.125rem;
	font-weight: 500;
}

.rc-sub {
	color: var(--il-ink);
	font-size: 0.95rem;
	font-weight: 500;
}

.rc-donut {
	--p: 0;
	--c: #35c759;
	display: grid;
	place-items: center;
	width: 6rem;
	height: 6rem;
	border-radius: 999px;
	background: radial-gradient(closest-side, #fff 76%, transparent 77%), conic-gradient(var(--c) calc(var(--p) * 1%), #e6e7e8 0);
}

.rc-donut span {
	font-size: 1.25rem;
	font-weight: 600;
	color: var(--il-ink);
}

.rc-chip {
	display: inline-block;
	margin-top: 0.25rem;
	border: 1px solid;
	border-radius: 999px;
	padding: 0.1rem 0.6rem;
	font-size: 0.75rem;
	font-weight: 500;
}

.rc-insights {
	border-radius: 16px;
	padding: 1rem 1.25rem;
	background: linear-gradient(100deg, #ffffff 0%, #f3efff 55%, #e9e3ff 100%);
}

.rc-li {
	position: relative;
	padding-left: 0.9rem;
	color: var(--il-ink);
	font-size: 0.8125rem;
	line-height: 1.25rem;
}

.rc-li::before {
	content: '';
	position: absolute;
	left: 0;
	top: 0.5rem;
	width: 0.3rem;
	height: 0.3rem;
	border-radius: 999px;
	background: currentColor;
	opacity: 0.5;
}

.rc-trend {
	border: 1px solid;
	border-radius: 999px;
	padding: 0.15rem 0.7rem;
	font-size: 0.7rem;
	font-weight: 500;
}

.rc-trend.is-excellent,
.rc-trend.is-good {
	border-color: #35c759;
	background: #e7f8ec;
	color: #146c31;
}

.rc-trend.is-average {
	border-color: #ffab00;
	background: #fff8e6;
	color: #8a5a00;
}

.rc-trend.is-needs_improvement {
	border-color: #f03e3e;
	background: #fff1f1;
	color: #b42323;
}

.rc-tabs {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 0.75rem;
}

.rc-tabs button {
	height: 2.5rem;
	border: 1px solid var(--il-primary-40);
	border-radius: 999px;
	background: #fff;
	color: var(--il-primary-20);
	font-size: 0.875rem;
	font-weight: 500;
}

.rc-tabs button.is-active {
	border-color: #00254c;
	background: #00254c;
	color: #fff;
}

.rc-sum {
	border: 1px solid;
	border-radius: 16px;
	padding: 1rem;
}

.rc-kpi {
	display: flex;
	flex-direction: column;
	border: 1px solid var(--il-neutral-90);
	border-radius: 16px;
	padding: 0.9rem 1rem;
	color: var(--il-muted);
	font-size: 0.8125rem;
}

.rc-kpi span {
	color: var(--il-ink);
	font-size: 1.5rem;
	font-weight: 600;
}

.rc-kpi small {
	color: var(--il-neutral-60);
}

:deep(.rc-avg-mark) {
	position: absolute;
	top: -3px;
	width: 2px;
	height: calc(100% + 6px);
	background: #00254c;
	transform: translateX(-1px);
}

:deep(.rc-bm-track) {
	position: relative;
	height: 0.5rem;
	border-radius: 999px;
	background: repeating-linear-gradient(90deg, #cecfd0 0 6px, transparent 6px 10px);
}

:deep(.rc-bm) {
	position: absolute;
	top: 50%;
	width: 0.85rem;
	height: 0.85rem;
	border: 2px solid #fff;
	border-radius: 999px;
	transform: translate(-50%, -50%);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

:deep(.rc-bm-label) {
	position: absolute;
	bottom: 1.1rem;
	left: 50%;
	transform: translateX(-50%);
	white-space: nowrap;
	font-size: 0.6875rem;
	color: var(--il-muted);
}

:deep(.rc-bm.is-low) {
	background: #f03e3e;
}

:deep(.rc-bm.is-avg) {
	background: #ffab00;
}

:deep(.rc-bm.is-high) {
	background: #35c759;
}

:deep(.rc-bm.is-you) {
	z-index: 2;
	width: 1.1rem;
	height: 1.1rem;
	background: #027bff;
}

:deep(.rc-bm.is-you .rc-bm-label) {
	bottom: auto;
	top: 1.2rem;
	color: #0062cc;
	font-weight: 600;
}

@media (max-width: 640px) {
	.rc-tabs {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
