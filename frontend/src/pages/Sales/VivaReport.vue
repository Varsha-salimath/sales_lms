<template>
	<div class="vr-page">
		<div class="vr-wrap">
			<button class="vr-back" @click="back">← {{ r?.is_own ? `${__('Day')} ${r.day}` : __('Viva results') }}</button>

			<div v-if="report.loading && !r" class="vr-muted mt-10">{{ __('Loading report…') }}</div>
			<div v-else-if="report.error" class="vr-card mt-6" style="color: #b42323">
				{{ report.error.messages?.[0] || __('This report could not be loaded.') }}
			</div>

			<template v-else-if="r">
				<!-- Header -->
				<section class="vr-hero">
					<div class="vr-hero-text">
						<p class="vr-eyebrow">
							{{ r.is_own ? '' : `${r.member_name} · ` }}{{ r.course !== 'sales-crt' ? `${r.course_title} · ` : '' }}{{ __('Day') }} {{ r.day }} · {{ __('Voice viva') }} ·
							{{ __('Attempt') }} {{ r.attempt_no }}
						</p>
						<h1>{{ r.title }}</h1>
						<p class="vr-hero-sub">{{ formatDate(r.started_at) }} · {{ duration(r.duration_s) }}</p>
						<span class="vr-verdict" :class="verdictClass">{{ verdictLabel }}</span>
					</div>
					<div class="vr-ring" :style="ringStyle">
						<div>
							<b>{{ score(r.overall_score) }}</b>
							<span>{{ __('of 100') }}</span>
						</div>
					</div>
				</section>

				<div v-if="r.status === 'Scoring'" class="vr-note mt-4">{{ __('This viva is still being scored — this page updates itself.') }}</div>

				<!-- Knowledge / Fluency -->
				<div class="vr-grid mt-5">
					<div class="vr-card">
						<div class="vr-metric-head">
							<span>{{ __('Knowledge') }}</span><b>{{ score(r.knowledge_score) }}%</b>
						</div>
						<div class="vr-bar"><span :style="barStyle(r.knowledge_score)" /></div>
						<p class="vr-muted mt-2">{{ __('Did the answers have the right facts from the day’s sessions? 70% of the score.') }}</p>
					</div>
					<div class="vr-card">
						<div class="vr-metric-head">
							<span>{{ __('Fluency') }}</span><b>{{ score(r.fluency_score) }}%</b>
						</div>
						<div class="vr-bar"><span :style="barStyle(r.fluency_score)" /></div>
						<p class="vr-muted mt-2">{{ __('How quickly and smoothly you answered: time to start, pauses, pace. 30% of the score.') }}</p>
					</div>
				</div>

				<!-- Summary -->
				<div v-if="r.summary || r.strengths.length || r.improvements.length" class="vr-card mt-5">
					<h2>{{ __('Summary') }}</h2>
					<p v-if="r.summary" class="vr-body mt-2">{{ r.summary }}</p>
					<div class="vr-two mt-4">
						<div v-if="r.strengths.length">
							<h3 class="vr-h3 is-good">{{ __('Strengths') }}</h3>
							<ul class="vr-list"><li v-for="s in r.strengths" :key="s">{{ s }}</li></ul>
						</div>
						<div v-if="r.improvements.length">
							<h3 class="vr-h3 is-warn">{{ __('To work on') }}</h3>
							<ul class="vr-list"><li v-for="s in r.improvements" :key="s">{{ s }}</li></ul>
						</div>
					</div>
				</div>

				<!-- Watch-outs -->
				<div v-if="r.flags.length" class="vr-flags mt-5">
					<div class="vr-flags-head"><AlertTriangle class="h-4 w-4" />{{ __('Watch-outs') }}</div>
					<ul>
						<li v-for="f in r.flags" :key="f">{{ f }}</li>
					</ul>
					<p class="vr-muted">{{ __('Long silences and leaving the screen lower Fluency and are shown to your Training Manager. They never fail you on their own.') }}</p>
				</div>

				<!-- Questions -->
				<h2 class="vr-section">{{ __('Question by question') }}</h2>
				<div v-for="(t, i) in r.turns" :key="i" class="vr-q" :class="{ 'is-open': open === i }">
					<button class="vr-q-head" @click="open = open === i ? -1 : i">
						<span class="vr-q-n">{{ i + 1 }}</span>
						<span class="vr-q-title">{{ t.question }}</span>
						<span class="vr-chip" :style="bandStyle(t.knowledge_score)">{{ score(t.knowledge_score) }}</span>
						<ChevronDown class="vr-q-chev h-4 w-4" />
					</button>
					<div v-if="open === i" class="vr-q-body">
						<div class="vr-timing">
							<span :class="{ 'is-warn': t.think_ms > 10000 }"><Timer class="h-3.5 w-3.5" />{{ __('Started after') }} {{ secs(t.think_ms) }}</span>
							<span><Mic class="h-3.5 w-3.5" />{{ __('Spoke') }} {{ secs(t.speech_ms) }}</span>
							<span :class="{ 'is-warn': t.longest_pause_ms > 8000 }">
								<Pause class="h-3.5 w-3.5" />{{ t.pause_count || 0 }} {{ __('pauses') }}{{ t.longest_pause_ms ? ` · ${__('longest')} ${secs(t.longest_pause_ms)}` : '' }}
							</span>
							<span v-if="t.wpm">{{ t.wpm }} {{ __('words/min') }}</span>
							<span v-if="t.tab_switches" class="is-bad"><EyeOff class="h-3.5 w-3.5" />{{ __('Left screen') }} ×{{ t.tab_switches }}</span>
							<span class="vr-fluency">{{ __('Fluency') }} {{ score(t.fluency_score) }}</span>
						</div>
						<div class="vr-answer">
							<div class="vr-label">{{ t.probe_asked ? __('Answer (with follow-up)') : __('Answer') }}</div>
							<p>{{ t.answer || __('No answer given.') }}</p>
						</div>
						<p v-if="t.feedback" class="vr-feedback">{{ t.feedback }}</p>
						<div class="vr-two">
							<div v-if="t.covered_points.length">
								<div class="vr-label is-good">{{ __('Covered') }}</div>
								<ul class="vr-list is-tight"><li v-for="p in t.covered_points" :key="p">{{ p }}</li></ul>
							</div>
							<div v-if="t.missed_points.length">
								<div class="vr-label is-warn">{{ __('Missed') }}</div>
								<ul class="vr-list is-tight"><li v-for="p in t.missed_points" :key="p">{{ p }}</li></ul>
							</div>
						</div>
					</div>
				</div>

				<!-- Actions -->
				<div class="vr-actions">
					<template v-if="r.is_own">
						<button v-if="r.status === 'Passed' && r.day < r.days_total" class="vr-btn" @click="$router.push({ name: 'DayDetail', params: { courseName: r.course, day: String(r.day + 1) } })">
							{{ __('Continue to Day') }} {{ r.day + 1 }}
						</button>
						<button v-else-if="r.status === 'Passed'" class="vr-btn" @click="finished">{{ __('Back to your journey') }}</button>
						<button v-else-if="r.day_state.attempts_left > 0 && !r.day_state.passed" class="vr-btn" @click="retry">
							{{ __('Try again') }} · {{ r.day_state.attempts_left }} {{ __('left') }}
						</button>
						<p v-else-if="r.day_state.blocked" class="vr-muted">{{ __('All attempts used. Your Training Manager can unlock more after reviewing this report with you.') }}</p>
					</template>
					<template v-else>
						<button v-if="r.can_unlock" class="vr-btn" :disabled="unlocking" @click="unlock">
							{{ unlocking ? __('Unlocking…') : __('Unlock 3 more attempts') }}
						</button>
						<span v-if="unlocked" class="vr-muted">{{ __('Done — the learner can take the viva again.') }}</span>
					</template>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, createResource } from 'frappe-ui'
import { AlertTriangle, ChevronDown, EyeOff, Mic, Pause, Timer } from 'lucide-vue-next'
import { bandOfPct, bandStyle as bandPalette } from '@/pages/Reports/reportUtils'

const route = useRoute()
const router = useRouter()
const open = ref(0)
const unlocking = ref(false)
const unlocked = ref(false)

const report = createResource({
	url: 'lms.lms.sales_viva.get_viva_report',
	makeParams: () => ({ attempt: route.params.attempt }),
	auto: true,
})
const r = computed(() => report.data)

// Scoring happens after the call ends, so poll until the result lands instead of asking the
// learner to refresh.
let scoringPoll = null
watch(
	() => r.value?.status,
	(status) => {
		if (status === 'Scoring' && !scoringPoll) scoringPoll = setInterval(() => report.reload(), 5000)
		else if (status !== 'Scoring' && scoringPoll) {
			clearInterval(scoringPoll)
			scoringPoll = null
		}
	}
)
onBeforeUnmount(() => scoringPoll && clearInterval(scoringPoll))

const score = (v) => (v == null ? '—' : Math.round(v))
const secs = (ms) => {
	const s = Math.round((ms || 0) / 1000)
	return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`
}
const duration = (s) => (s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')} ${__('min')}` : '')
const formatDate = (d) => (d ? new Date(String(d).replace(' ', 'T')).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : '')

const verdictLabel = computed(() => {
	if (!r.value) return ''
	if (r.value.status === 'Passed') return r.value.verdict || __('Passed')
	if (r.value.status === 'Scoring') return __('Scoring')
	return __('Not yet')
})
const verdictClass = computed(() => ({ Passed: 'is-good', 'Not Passed': 'is-bad' })[r.value?.status] || '')
const ringStyle = computed(() => {
	const pct = Math.max(0, Math.min(100, r.value?.overall_score || 0))
	const color = r.value?.status === 'Passed' ? '#35C759' : '#FCDE5A'
	return { background: `conic-gradient(${color} ${pct * 3.6}deg, rgba(255,255,255,0.16) 0)` }
})
const barStyle = (v) => ({ width: `${Math.max(2, Math.min(100, v || 0))}%`, background: bandPalette(bandOfPct(v)).solid })
const bandStyle = (v) => {
	const b = bandPalette(bandOfPct(v))
	return { background: b.soft, color: b.text }
}

function back() {
	if (r.value?.is_own) router.push({ name: 'DayViva', params: { courseName: r.value.course, day: r.value.slug } })
	else router.push({ name: 'VivaResults' })
}
function retry() {
	router.push({ name: 'DayViva', params: { courseName: r.value.course, day: r.value.slug } })
}
function finished() {
	if (r.value.course === 'sales-crt') router.push({ name: 'StudentDashboard' })
	else router.push({ name: 'CourseDays', params: { courseName: r.value.course } })
}
async function unlock() {
	unlocking.value = true
	try {
		await call('lms.lms.sales_viva.grant_attempts', { member: r.value.member, course: r.value.course, day: r.value.day, reason: 'Unlocked from viva report' })
		unlocked.value = true
		report.reload()
	} finally {
		unlocking.value = false
	}
}
</script>

<style scoped>
.vr-page {
	min-height: 100vh;
	background: #fff;
	padding-bottom: 64px;
}
.vr-wrap {
	max-width: 880px;
	margin: 0 auto;
	padding: 28px 20px 0;
}
.vr-back {
	font-size: 14px;
	font-weight: 600;
	color: #0062cc;
}
.vr-muted {
	font-size: 13px;
	color: #52565c;
}
.vr-hero {
	margin-top: 18px;
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	padding: 28px;
	border-radius: 24px;
	color: #fff;
	background: linear-gradient(135deg, #00254c 0%, #013166 100%);
}
.vr-hero-text {
	max-width: 520px;
}
.vr-eyebrow {
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	opacity: 0.75;
}
.vr-hero h1 {
	margin-top: 6px;
	font-size: 26px;
	line-height: 32px;
	font-weight: 600;
}
.vr-hero-sub {
	margin-top: 6px;
	font-size: 13px;
	opacity: 0.8;
}
.vr-verdict {
	display: inline-block;
	margin-top: 14px;
	padding: 4px 14px;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	background: rgba(255, 255, 255, 0.15);
}
.vr-verdict.is-good {
	background: #35c759;
}
.vr-verdict.is-bad {
	background: #fcde5a;
	color: #00254c;
}
.vr-ring {
	width: 132px;
	height: 132px;
	border-radius: 999px;
	display: grid;
	place-items: center;
	flex: none;
}
.vr-ring > div {
	width: 104px;
	height: 104px;
	border-radius: 999px;
	background: #00254c;
	display: grid;
	place-content: center;
	text-align: center;
}
.vr-ring b {
	font-size: 34px;
	line-height: 36px;
	font-weight: 600;
}
.vr-ring span {
	font-size: 11px;
	opacity: 0.7;
}
.vr-note {
	padding: 12px 16px;
	border-radius: 16px;
	background: #f4f9ff;
	border: 1px solid #cfe5ff;
	font-size: 14px;
}
.vr-grid {
	display: grid;
	gap: 16px;
}
@media (min-width: 768px) {
	.vr-grid {
		grid-template-columns: 1fr 1fr;
	}
}
.vr-card {
	padding: 20px 24px;
	border-radius: 24px;
	background: #fff;
	border: 1px solid #e6e7e8;
	box-shadow: 0 1px 12px rgba(0, 0, 0, 0.12);
}
.vr-card h2,
.vr-section {
	font-size: 18px;
	line-height: 24px;
	font-weight: 600;
	color: #080e14;
}
.vr-section {
	margin: 28px 0 12px;
}
.vr-metric-head {
	display: flex;
	justify-content: space-between;
	font-size: 15px;
	font-weight: 500;
}
.vr-metric-head b {
	font-size: 22px;
	font-weight: 600;
}
.vr-bar {
	margin-top: 10px;
	height: 10px;
	border-radius: 999px;
	background: #f2f2f2;
	overflow: hidden;
}
.vr-bar span {
	display: block;
	height: 100%;
	border-radius: 999px;
}
.vr-body {
	font-size: 14px;
	line-height: 21px;
	color: #080e14;
}
.vr-two {
	display: grid;
	gap: 14px;
}
@media (min-width: 640px) {
	.vr-two {
		grid-template-columns: 1fr 1fr;
	}
}
.vr-h3,
.vr-label {
	font-size: 12px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	color: #52565c;
}
.vr-h3.is-good,
.vr-label.is-good {
	color: #04742d;
}
.vr-h3.is-warn,
.vr-label.is-warn {
	color: #b36e00;
}
.vr-list {
	margin-top: 6px;
	padding-left: 18px;
	list-style: disc;
	font-size: 14px;
	line-height: 21px;
	color: #080e14;
}
.vr-list.is-tight {
	font-size: 13px;
	line-height: 19px;
}
.vr-flags {
	padding: 16px 20px;
	border-radius: 20px;
	background: #fff8e6;
	border: 1px solid #ffcf66;
}
.vr-flags-head {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 14px;
	font-weight: 600;
	color: #8a5a00;
}
.vr-flags ul {
	margin: 8px 0;
	padding-left: 18px;
	list-style: disc;
	font-size: 14px;
	color: #080e14;
}
.vr-q {
	border: 1px solid #e6e7e8;
	border-radius: 16px;
	margin-bottom: 10px;
	background: #fff;
}
.vr-q.is-open {
	border-color: #cfe5ff;
	background: #f4f9ff;
}
.vr-q-head {
	width: 100%;
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 14px 16px;
	text-align: left;
}
.vr-q-n {
	width: 28px;
	height: 28px;
	flex: none;
	display: grid;
	place-items: center;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	background: #e6f2ff;
	color: #0062cc;
}
.vr-q-title {
	flex: 1;
	font-size: 15px;
	line-height: 22px;
	font-weight: 500;
	color: #080e14;
}
.vr-chip {
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	flex: none;
}
.vr-q-chev {
	flex: none;
	color: #85878a;
	transition: transform 0.15s ease;
}
.vr-q.is-open .vr-q-chev {
	transform: rotate(180deg);
}
.vr-q-body {
	padding: 0 16px 16px 56px;
	display: grid;
	gap: 12px;
}
@media (max-width: 640px) {
	.vr-q-body {
		padding-left: 16px;
	}
}
.vr-timing {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}
.vr-timing span {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 500;
	background: #fff;
	border: 1px solid #e6e7e8;
	color: #52565c;
}
.vr-timing span.is-warn {
	background: #ffeecc;
	border-color: #ffcf66;
	color: #8a5a00;
}
.vr-timing span.is-bad {
	background: #fef0f0;
	border-color: #f4a3a3;
	color: #b42323;
}
.vr-timing .vr-fluency {
	font-weight: 600;
	color: #0062cc;
}
.vr-answer p {
	margin-top: 4px;
	font-size: 14px;
	line-height: 21px;
	color: #080e14;
	white-space: pre-line;
}
.vr-feedback {
	font-size: 14px;
	line-height: 21px;
	padding: 10px 14px;
	border-radius: 12px;
	background: #fff;
	border-left: 3px solid #027bff;
}
.vr-actions {
	margin-top: 24px;
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 12px;
}
.vr-btn {
	height: 44px;
	padding: 0 24px;
	border-radius: 999px;
	font-size: 14px;
	font-weight: 600;
	color: #fff;
	background: #027bff;
}
.vr-btn:disabled {
	opacity: 0.5;
}
</style>
