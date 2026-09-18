<template>
	<div class="il-page min-h-full pb-12">
		<nav class="flex items-center gap-1.5 pt-5 text-sm">
			<router-link :to="{ name: 'LearnerReports' }" class="text-[color:var(--il-primary-40)]">{{ __('Reports') }}</router-link>
			<span class="text-[color:var(--il-neutral-60)]">/</span>
			<router-link :to="{ name: 'LearnerReports' }" class="text-[color:var(--il-primary-40)]">{{ __('Sales CRT') }}</router-link>
			<span class="text-[color:var(--il-neutral-60)]">/</span>
			<span class="font-medium text-[color:var(--il-primary-20)]">{{ learner?.employee_name || __('Report card') }}</span>
		</nav>

		<div v-if="report.loading && !report.data" class="mt-4 space-y-4">
			<div class="h-28 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="h-44 animate-pulse rounded-3xl bg-[#e6e7e8]" />
		</div>
		<div v-else-if="report.error" class="il-card mt-4 p-8 text-center text-sm text-[color:var(--il-error-50)]">
			{{ report.error.messages?.[0] || __('Could not load this report card.') }}
		</div>

		<template v-else-if="learner">
			<!-- Profile header (PTM board) -->
			<section class="rc-card mt-3 overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 bg-[#f4f9ff] px-5 py-3.5">
					<div class="flex items-center gap-3">
						<span class="rc-avatar">{{ initials(learner.employee_name) }}</span>
						<div>
							<h1 class="text-xl font-semibold text-[color:var(--il-ink)]">{{ learner.employee_name }}</h1>
							<p class="text-xs text-[color:var(--il-muted)]">{{ learner.email }}</p>
						</div>
					</div>
					<span v-if="learner.modified" class="text-xs text-[color:var(--il-muted)]">{{ __('Last updated') }}: {{ fmtDate(learner.modified) }}</span>
				</div>
				<div class="flex flex-wrap justify-between gap-x-8 gap-y-2 px-5 py-3.5 text-sm">
					<div><span class="rc-meta">{{ __('Batch') }}</span>{{ fmtDate(learner.batch_start) }}</div>
					<div><span class="rc-meta">{{ __('Location') }}</span>{{ learner.location || '—' }}</div>
					<div><span class="rc-meta">{{ __('Training manager') }}</span>{{ managerName(learner.training_manager) }}</div>
					<div><span class="rc-meta">{{ __('Stage') }}</span>{{ learner.stage || '—' }}</div>
					<div>
						<span class="rc-meta">{{ __('Rank in batch') }}</span>
						<template v-if="batch.rank">#{{ batch.rank }} <span class="text-[color:var(--il-muted)]">{{ __('of') }} {{ batch.ranked }}</span></template>
						<template v-else>—</template>
					</div>
				</div>
			</section>

			<!-- Highlights -->
			<h2 class="rc-h2">{{ __('Highlights') }}</h2>
			<section class="rc-card rc-highlights">
				<div class="flex items-center gap-4">
					<div class="rc-donut" :style="{ '--p': learner.readiness || 0, '--c': bandStyle(learner.readiness_band).dot }">
						<span>{{ fmtPct(learner.readiness) }}</span>
					</div>
					<div>
						<div class="text-lg leading-6 text-[color:var(--il-ink)]">{{ __('Readiness') }}</div>
						<span class="rc-chip" :style="chip(learner.readiness_band)">{{ bandStyle(learner.readiness_band).label }}</span>
						<div class="mt-1 text-xs text-[color:var(--il-muted)]">{{ __('Batch avg') }} {{ fmtPct(stats.readiness?.avg) }}</div>
					</div>
				</div>
				<InsightsCard :title="__('Insights')" :items="insightItems" :chip="trendLabel" :chip-tone="trendTone" :empty="__('Insights appear once this learner has scores.')" />
			</section>

			<!-- Tabs -->
			<div class="rc-tabs">
				<button v-for="t in tabs" :key="t.key" :class="{ 'is-active': tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
			</div>

			<!-- Overview -->
			<div v-if="tab === 'overview'" class="space-y-6">
				<ReportSection :title="__('Input summary')" :subtitle="__('Each score against the batch average.')">
					<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						<div v-for="c in summaryCards" :key="c.key" class="rc-input" :style="{ background: bandStyle(c.band).soft, borderColor: bandStyle(c.band).rowBorder }">
							<div class="px-3.5 pt-3">
								<div class="text-[15px] text-[color:var(--il-ink)]">{{ c.label }}</div>
								<div class="mt-1 flex items-baseline gap-2">
									<span class="text-xl font-semibold" :style="{ color: bandStyle(c.band).text }">{{ fmt(c.value) }}</span>
									<span class="border-s border-[color:var(--il-neutral-80)] ps-2 text-xs text-[color:var(--il-muted)]">{{ __('out of') }} {{ c.max }}</span>
								</div>
							</div>
							<div class="rc-input-foot flex items-center gap-1" :class="deltaClass(c.value, c.avg)">
								<component :is="deltaIcon(c.value, c.avg)" class="h-3.5 w-3.5" />
								{{ deltaText(c.value, c.avg) }}
							</div>
						</div>
					</div>
				</ReportSection>

				<div class="grid gap-6 lg:grid-cols-2">
					<ReportSection :title="__('Tests vs batch')" :action="__('View details')" @action="tab = 'tests'">
						<div class="space-y-3">
							<ScoreBar v-for="m in testMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :avg="stats[m.key]?.avg" :band="learner.scores[m.key]?.band" />
						</div>
						<p class="mt-3 text-[11px] text-[color:var(--il-muted)]">{{ __('The dark tick is the batch average.') }}</p>
					</ReportSection>
					<ReportSection :title="__('Calling funnel')" :action="__('View details')" @action="tab = 'calling'">
						<Funnel v-if="learner.dc != null" :learner="learner" :stats="stats" />
						<p v-else class="py-8 text-center text-sm text-[color:var(--il-muted)]">{{ __('Not on live calls yet. Calling starts after CRT.') }}</p>
					</ReportSection>
				</div>
			</div>

			<!-- Test performance -->
			<div v-if="tab === 'tests'" class="space-y-6">
				<ReportSection :title="__('Test performance')" :subtitle="__('Five CRT product tests, each out of 20.')">
					<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
						<div v-for="s in testStats" :key="s.label" class="rc-stat">
							<div class="text-xl font-semibold text-[color:var(--il-ink)]">
								{{ s.value }}<small v-if="s.of" class="font-normal text-[color:var(--il-muted)]"> / {{ s.of }}</small>
							</div>
							<div class="mt-0.5 text-sm text-[color:var(--il-muted)]">{{ s.label }}</div>
						</div>
					</div>
					<ScoreTrend
						class="mt-5"
						:title="__('Score trend')"
						:items="testTrend"
						:modes="[
							{ key: 'self', label: __('Learner score') },
							{ key: 'top', label: __('vs Topper') },
							{ key: 'avg', label: __('vs Average') },
						]"
						:value-label="__('Score')"
						:best-label="__('Best score')"
					/>
				</ReportSection>

				<ReportSection :title="__('Score benchmark')" :subtitle="__('Where this learner sits in the batch on each test: lowest, average, highest.')">
					<div class="space-y-7">
						<Benchmark v-for="m in testMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :stat="stats[m.key]" :band="learner.scores[m.key]?.band" />
					</div>
				</ReportSection>
			</div>

			<!-- Calling -->
			<ReportSection v-if="tab === 'calling'" :title="__('Calling performance')">
				<div class="grid gap-3 sm:grid-cols-3">
					<div class="rc-kpi"><span>{{ fmtPct(learner.connect_rate) }}</span>{{ __('Connect rate') }} <small>{{ __('avg') }} {{ fmtPct(stats.connect_rate?.avg) }}</small></div>
					<div class="rc-kpi"><span>{{ fmtPct(learner.booking_rate) }}</span>{{ __('Booking rate') }} <small>{{ __('avg') }} {{ fmtPct(stats.booking_rate?.avg) }}</small></div>
					<div class="rc-kpi"><span>{{ fmtPct(learner.show_rate) }}</span>{{ __('Catered / booked') }} <small>{{ __('avg') }} {{ fmtPct(stats.show_rate?.avg) }}</small></div>
				</div>
				<Funnel class="mt-6" :learner="learner" :stats="stats" />
				<div class="mt-5 rounded-2xl bg-[#f4f9ff] px-4 py-3 text-sm">
					<Clock class="me-1 inline h-4 w-4 text-[color:var(--il-primary-40)]" />
					{{ __('Talk time') }}: <strong>{{ learner.talk_time || '—' }}</strong>
					<span class="text-[color:var(--il-muted)]"> · {{ __('batch avg') }} {{ fmtDuration(stats.talk_seconds?.avg) }}</span>
				</div>
			</ReportSection>

			<!-- Intent & Skill -->
			<ReportSection v-if="tab === 'intent'" :title="__('Intent & Skill')" :subtitle="__('Where this learner sits against the batch: lowest, average and highest.')">
				<div class="space-y-7">
					<Benchmark v-for="m in intentMetrics" :key="m.key" :label="m.label" :value="learner[m.key]" :max="m.max" :stat="stats[m.key]" :band="learner.scores[m.key]?.band" />
				</div>
			</ReportSection>

			<p class="mt-4 text-xs text-[color:var(--il-muted)]">{{ BAND_RULES }}. {{ __('Batch') }} = {{ batch.size }} {{ __('learners who started on') }} {{ fmtDate(batch.batch_start) }}.</p>
		</template>
	</div>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { createResource } from 'frappe-ui'
import { ArrowDownRight, ArrowUpRight, Clock, Minus } from 'lucide-vue-next'
import ReportSection from './ReportSection.vue'
import InsightsCard from './InsightsCard.vue'
import ScoreTrend from './ScoreTrend.vue'
import { BAND_RULES, bandStyle, fmt, fmtDate, fmtDuration, fmtPct, initials, managerName, median } from './reportUtils'

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
	{ key: 'tests', label: __('Test performance') },
	{ key: 'intent', label: __('Intent & Skill') },
	{ key: 'calling', label: __('Calling') },
]

const insightItems = computed(() => [
	...insights.value.strengths.map((text) => ({ lead: __('Strength:'), text })),
	...insights.value.gaps.map((text) => ({ lead: __('Focus:'), text })),
])

const scoredTests = computed(() => testMetrics.value.filter((m) => learner.value?.[m.key] != null && learner.value?.[m.key] !== ''))
const testStats = computed(() => {
	const pcts = scoredTests.value.map((m) => learner.value.scores[m.key]?.pct)
	return [
		{ label: __('Tests taken'), value: String(scoredTests.value.length).padStart(2, '0'), of: testMetrics.value.length },
		{ label: __('Tests pending'), value: String(testMetrics.value.length - scoredTests.value.length).padStart(2, '0'), of: testMetrics.value.length },
		{ label: __('Highest score'), value: pcts.length ? `${Math.round(Math.max(...pcts))}%` : '—' },
		{ label: __('Median score'), value: pcts.length ? `${Math.round(median(pcts))}%` : '—' },
	]
})
const testTrend = computed(() =>
	testMetrics.value.map((m) => {
		const st = stats.value[m.key] || {}
		const toPct = (v) => (v == null ? null : Math.min(100, (v / m.max) * 100))
		return {
			label: m.label,
			value: learner.value.scores[m.key]?.pct ?? null,
			display: learner.value[m.key] == null ? __('Not taken') : `${fmt(learner.value[m.key])}/${m.max}`,
			compare: { top: toPct(st.max), avg: toPct(st.avg) },
		}
	})
)

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
const trendTone = computed(() => ({ excellent: 'good', good: 'good', average: 'warn', needs_improvement: 'bad' })[learner.value?.readiness_band] || 'warn')

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

.rc-card {
	border: 1px solid #edf0f4;
	border-radius: 20px;
	background: #fff;
	box-shadow: 0 2px 10px rgba(0, 37, 76, 0.06);
}

.rc-h2 {
	margin: 1.5rem 0 0.75rem;
	color: var(--il-ink);
	font-size: 1.25rem;
	font-weight: 400;
}

.rc-highlights {
	display: grid;
	gap: 1.25rem;
	align-items: center;
	padding: 1.1rem 1.25rem;
}

@media (min-width: 1024px) {
	.rc-highlights {
		grid-template-columns: 17rem 1fr;
	}

	.rc-highlights > :first-child {
		height: 100%;
		border-right: 1px solid var(--il-neutral-90);
	}
}

.rc-donut {
	--p: 0;
	--c: #35c759;
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 6.25rem;
	height: 6.25rem;
	border-radius: 999px;
	background: radial-gradient(closest-side, #fff 68%, transparent 69%), conic-gradient(var(--c) calc(var(--p) * 1%), #e6f2ff 0);
}

.rc-donut span {
	font-size: 1.25rem;
	font-weight: 500;
	color: var(--il-ink);
}

.rc-input {
	overflow: hidden;
	border: 1px solid;
	border-radius: 12px;
}

.rc-input-foot {
	margin-top: 0.75rem;
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	padding: 0.45rem 0.9rem;
	background: #fff;
	font-size: 0.75rem;
}

.rc-stat {
	border: 1px solid #edf0f4;
	border-radius: 14px;
	padding: 0.85rem 1rem;
	text-align: center;
	box-shadow: 0 1px 4px rgba(0, 37, 76, 0.05);
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

.rc-tabs {
	margin: 1.5rem 0 1.25rem;
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
