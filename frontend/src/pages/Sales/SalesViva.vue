<template>
	<div class="viva-page">
		<div class="viva-wrap">
			<button class="viva-back" @click="leave">← {{ __('Day') }} {{ dayNumber }}</button>

			<div v-if="info.loading && !info.data" class="viva-muted mt-10">{{ __('Loading…') }}</div>
			<div v-else-if="info.error" class="viva-card viva-error mt-6">
				{{ info.error.messages?.[0] || __('The viva could not be loaded.') }}
			</div>

			<!-- ============ Before the call ============ -->
			<template v-else-if="info.data && stage === 'intro'">
				<section class="viva-hero">
					<div class="viva-hero-text">
						<p class="viva-eyebrow">
							{{ __('Day') }} {{ dayNumber }} · {{ __('Voice viva') }}<template v-if="courseName !== 'sales-crt'"> · {{ info.data.course_title }}</template>
						</p>
						<h1>{{ info.data.title }}</h1>
						<p class="viva-hero-sub">
							{{ `${__('A short spoken check with Asha, your AI examiner.')} ${info.data.questions} ${__('questions')} · ${__('about 3–4 minutes')}.` }}
						</p>
					</div>
					<div class="viva-attempts">
						<span
							v-for="n in info.data.attempts_allowed"
							:key="n"
							class="viva-dot"
							:class="dotClass(n)"
						/>
						<span class="viva-attempts-label">
							{{ info.data.passed ? __('Passed') : `${info.data.attempts_left} ${__('of')} ${info.data.attempts_allowed} ${__('attempts left')}` }}
						</span>
					</div>
				</section>

				<!-- Status notes -->
				<div v-if="info.data.reason === 'passed'" class="viva-note is-good">
					<CheckCircle2 class="h-5 w-5 flex-none" />
					<div>
						<b>{{ __('You passed this viva.') }}</b>
						{{ __('This day is complete. Your report is below.') }}
					</div>
				</div>
				<div v-else-if="info.data.reason === 'blocked'" class="viva-note is-warn">
					<Lock class="h-5 w-5 flex-none" />
					<div>
						<b>{{ __('All attempts used.') }}</b>
						{{ __('Your Training Manager has your reports and can unlock three more attempts after coaching you.') }}
					</div>
				</div>
				<div v-else-if="info.data.reason === 'lessons_pending'" class="viva-note">
					<BookOpen class="h-5 w-5 flex-none" />
					<div>
						<b>{{ __('Finish today’s sessions first.') }}</b>
						{{ `${info.data.lessons_completed}/${info.data.lessons_total} ${__('sessions done. The viva unlocks when all are complete.')}` }}
					</div>
				</div>
				<div v-else-if="info.data.reason === 'not_configured'" class="viva-note">
					<Info class="h-5 w-5 flex-none" />
					<div>{{ __('The voice viva isn’t switched on yet. You can continue to the next day.') }}</div>
				</div>

				<div v-if="info.data.can_start" class="viva-grid">
					<div class="viva-card">
						<h2>{{ __('How it works') }}</h2>
						<ol class="viva-steps">
							<li><Mic class="h-4 w-4" />{{ __('Asha asks a question out loud. Answer in your own words, like you would to a parent.') }}</li>
							<li><Timer class="h-4 w-4" />{{ __('Take a breath before answering if you need to — but long silences are noted in your report.') }}</li>
							<li><Hand class="h-4 w-4" />{{ __('Pause for 3 seconds or tap “I’m done” when you finish. Asha may ask one follow-up.') }}</li>
							<li><EyeOff class="h-4 w-4" />{{ __('Stay on this screen. Switching tabs or apps during the viva is recorded.') }}</li>
						</ol>
						<p class="viva-muted mt-3">
							{{ `${__('Pass mark')} ${info.data.pass_mark}% · ${__('70% what you know, 30% how smoothly you say it.')}` }}
						</p>
					</div>

					<div class="viva-card">
						<h2>{{ __('Check your microphone') }}</h2>
						<p class="viva-muted">{{ __('Use earphones in a quiet place if you can.') }}</p>
						<div class="viva-meter mt-4">
							<div class="viva-meter-fill" :style="{ width: `${Math.round(micLevel * 100)}%` }" />
						</div>
						<p class="viva-mic-line">
							<template v-if="micState === 'idle'">{{ __('Tap “Test mic” and say a few words.') }}</template>
							<template v-else-if="micState === 'denied'">{{ __('Microphone blocked. Allow it in your browser settings and reload.') }}</template>
							<template v-else-if="micHeard">{{ __('We can hear you. You’re ready.') }}</template>
							<template v-else>{{ __('Listening… say something.') }}</template>
						</p>
						<p v-if="startError" class="viva-start-error">{{ startError }}</p>
						<div class="viva-actions">
							<button v-if="micState !== 'on'" class="viva-btn is-ghost" @click="testMic">{{ __('Test mic') }}</button>
							<button class="viva-btn" :disabled="starting || micState === 'denied'" @click="begin">
								<Mic class="h-4 w-4" />
								{{ starting ? __('Preparing your questions…') : __('Start viva') }}
							</button>
						</div>
					</div>
				</div>

				<div v-if="info.data.history?.length" class="viva-card mt-5">
					<h2>{{ __('Your attempts') }}</h2>
					<ul class="viva-history">
						<li v-for="h in info.data.history" :key="h.name" @click="openReport(h.name)">
							<span class="viva-history-n">#{{ h.attempt_no }}</span>
							<span class="flex-1">{{ formatDate(h.date) }}</span>
							<span class="viva-pill" :class="pillClass(h.status)">{{ statusLabel(h.status) }}</span>
							<span class="viva-history-score">{{ h.overall_score != null ? `${Math.round(h.overall_score)}%` : '—' }}</span>
							<ChevronRight class="h-4 w-4 text-[color:var(--il-muted)]" />
						</li>
					</ul>
				</div>
			</template>

			<!-- ============ The call ============ -->
			<section v-else-if="stage === 'live'" class="viva-call">
				<div class="viva-call-top">
					<div class="viva-progress">
						<span
							v-for="n in live.questions"
							:key="n"
							:class="{ 'is-done': n < live.questionNumber, 'is-now': n === live.questionNumber }"
						/>
					</div>
					<span class="viva-qlabel">
						{{ live.questionNumber ? `${__('Question')} ${live.questionNumber} ${__('of')} ${live.questions}` : __('Starting…') }}
					</span>
					<span class="viva-timer" :class="{ 'is-low': live.secondsLeft <= 30 }">{{ clock(live.secondsLeft) }}</span>
				</div>

				<div class="viva-stage">
					<div class="viva-avatar" :class="{ 'is-speaking': live.phase === 'asha' }">
						<span class="viva-avatar-ring" />
						<span class="viva-avatar-face">A</span>
					</div>
					<div class="viva-who">Asha</div>
					<div class="viva-phase">{{ phaseLabel }}</div>
					<p class="viva-caption">{{ live.ashaText || '…' }}</p>
				</div>

				<div class="viva-you" :class="{ 'is-live': live.inActivity }">
					<div class="viva-you-head">
						<span class="viva-level"><span :style="{ transform: `scaleX(${Math.max(0.04, live.level)})` }" /></span>
						{{ live.inActivity ? __('You’re speaking…') : __('Your answer') }}
					</div>
					<p>{{ live.userText || __('Your words will appear here as you speak.') }}</p>
				</div>

				<div class="viva-controls">
					<button class="viva-btn" :disabled="!live.inActivity" @click="engine.done()">
						<Check class="h-4 w-4" />{{ __('I’m done') }}
					</button>
					<button
						class="viva-btn is-ghost"
						@pointerdown.prevent="engine.holdStart()"
						@pointerup.prevent="engine.holdEnd()"
						@pointercancel="live.holdMode && engine.holdEnd()"
						@pointerleave="live.holdMode && engine.holdEnd()"
						style="touch-action: none"
					>
						<Mic class="h-4 w-4" />{{ live.holdMode ? __('Release to send') : __('Hold to talk') }}
					</button>
					<button class="viva-btn is-ghost" :disabled="!live.repeatsLeft || live.phase === 'asha'" @click="engine.repeat()">
						<RotateCcw class="h-4 w-4" />{{ __('Repeat question') }}
					</button>
					<button class="viva-btn is-quiet" @click="confirmEnd">{{ __('End viva') }}</button>
				</div>
			</section>

			<!-- ============ Scoring / errors ============ -->
			<section v-else-if="stage === 'scoring'" class="viva-card viva-center mt-10">
				<div class="viva-spinner" />
				<h2>{{ __('Scoring your viva…') }}</h2>
				<p class="viva-muted">{{ __('Checking each answer against today’s content. This takes a few seconds.') }}</p>
			</section>
			<section v-else-if="stage === 'error'" class="viva-card viva-center mt-10">
				<AlertTriangle class="h-8 w-8" style="color: #b36e00" />
				<h2>{{ __('The viva stopped') }}</h2>
				<p class="viva-muted">{{ live.error || startError }}</p>
				<p class="viva-muted">{{ __('Anything you answered has been saved and scored.') }}</p>
				<button class="viva-btn mt-4" @click="reset">{{ __('Back') }}</button>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, createResource } from 'frappe-ui'
import {
	AlertTriangle,
	BookOpen,
	Check,
	CheckCircle2,
	ChevronRight,
	EyeOff,
	Hand,
	Info,
	Lock,
	Mic,
	RotateCcw,
	Timer,
} from 'lucide-vue-next'
import { createLiveViva } from './viva/liveViva'

const route = useRoute()
const router = useRouter()
// /courses/<course>/days/<n>-<title>/viva
const courseName = computed(() => route.params.courseName || 'sales-crt')
const dayParam = computed(() => String(route.params.day || route.params.crtNumber || '1'))
const dayNumber = computed(() => info.data?.day || parseInt(dayParam.value) || 1)

const info = createResource({
	url: 'lms.lms.sales_viva.get_viva_state',
	makeParams: () => ({ course: courseName.value, day: dayParam.value }),
	auto: true,
	onSuccess(data) {
		if (data?.slug && route.params.day !== data.slug && stage.value === 'intro') {
			router.replace({ name: 'DayViva', params: { courseName: courseName.value, day: data.slug }, query: route.query })
		}
	},
})

const stage = ref('intro')
const starting = ref(false)
const startError = ref('')
const live = reactive({ phase: 'connecting', questionNumber: 0, questions: 5, ashaText: '', userText: '', error: '', secondsLeft: 300, level: 0, repeatsLeft: 1, holdMode: false, inActivity: false })
let engine = null

// ---------- mic test ----------
const micState = ref('idle')
const micLevel = ref(0)
const micHeard = ref(false)
let micTest = null
async function testMic() {
	try {
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
		const ctx = new (window.AudioContext || window.webkitAudioContext)()
		const analyser = ctx.createAnalyser()
		ctx.createMediaStreamSource(stream).connect(analyser)
		const buf = new Float32Array(analyser.fftSize)
		micState.value = 'on'
		const loop = () => {
			analyser.getFloatTimeDomainData(buf)
			const rms = Math.sqrt(buf.reduce((a, v) => a + v * v, 0) / buf.length)
			micLevel.value = Math.min(1, rms * 12)
			if (rms > 0.03) micHeard.value = true
			micTest.raf = requestAnimationFrame(loop)
		}
		micTest = { stream, ctx }
		loop()
	} catch (e) {
		micState.value = 'denied'
	}
}
function stopMicTest() {
	if (!micTest) return
	cancelAnimationFrame(micTest.raf)
	micTest.stream.getTracks().forEach((t) => t.stop())
	micTest.ctx.close()
	micTest = null
	micLevel.value = 0
	// Back to "idle" so "Test mic" is offered again; a refused mic stays refused.
	if (micState.value === 'on') micState.value = 'idle'
}

// ---------- the call ----------
async function begin() {
	starting.value = true
	startError.value = ''
	stopMicTest()
	try {
		const session = await call('lms.lms.sales_viva.start_attempt', { course: courseName.value, day: dayParam.value })
		engine = createLiveViva({
			attempt: session.attempt,
			wsUrl: session.ws_url,
			setup: session.setup,
			timeLimitS: session.time_limit_s,
			onChange: (snap) => {
				Object.assign(live, snap)
				if (snap.phase === 'ending') stage.value = 'scoring'
				if (snap.phase === 'error') stage.value = 'error'
			},
		})
		live.questions = session.questions
		live.secondsLeft = session.time_limit_s
		stage.value = 'live'
		await engine.start((report) => leaving || openReport(report.name, true))
	} catch (e) {
		startError.value = e?.messages?.[0] || e?.message || __('Could not start the viva.')
		if (e?.name === 'NotAllowedError') micState.value = 'denied'
		stage.value = stage.value === 'live' ? 'error' : 'intro'
		if (stage.value === 'intro') info.reload()
	} finally {
		starting.value = false
	}
}

// Set once the learner has navigated away: the scoring callback must not route them back.
let leaving = false

function confirmEnd() {
	if (window.confirm(__('End the viva now? Unanswered questions score zero and this counts as an attempt.'))) engine?.stop()
}

function reset() {
	engine?.destroy()
	engine = null
	stage.value = 'intro'
	info.reload()
}

function openReport(name, replace = false) {
	router[replace ? 'replace' : 'push']({ name: 'VivaReport', params: { attempt: name } })
}

function leave() {
	if (stage.value === 'live' && !window.confirm(__('Leave the viva? It will end and count as an attempt.'))) return
	if (stage.value === 'live') {
		// Stopping scores the attempt, and scoring used to navigate to the report — pulling the
		// learner off whatever page they had just opened. Once they have chosen to leave, the
		// report callback stays quiet.
		leaving = true
		engine?.stop()
	}
	router.push({ name: 'DayDetail', params: { courseName: courseName.value, day: info.data?.slug || dayParam.value } })
}

// Local dev only (stripped from production builds): /crt/N/viva?preview=call shows the call screen
// with a scripted conversation, so the design can be reviewed without a Gemini connection.
let previewTimer = null
if (import.meta.env.DEV && route.query.preview === 'call') {
	const script = [
		{ phase: 'asha', questionNumber: 2, ashaText: 'Okay, thank you. Next one: what does LPDT stand for, and how does it help a student?' },
		{ phase: 'listening', ashaText: 'Okay, thank you. Next one: what does LPDT stand for, and how does it help a student?' },
		{ phase: 'listening', inActivity: true, level: 0.5, userText: 'Learn, Practice, Doubt-solving and Test. Every chapter goes through these four steps' },
		{ phase: 'listening', inActivity: true, level: 0.3, userText: 'Learn, Practice, Doubt-solving and Test. Every chapter goes through these four steps so the child does not just watch videos but practises and gets tested.' },
		{ phase: 'thinking', inActivity: false, level: 0 },
	]
	let i = 0
	stage.value = 'live'
	Object.assign(live, { questions: 5, secondsLeft: 212, repeatsLeft: 1 })
	engine = { done() {}, holdStart() {}, holdEnd() {}, repeat() {}, stop() {}, destroy() {} }
	const step = () => {
		Object.assign(live, { inActivity: false, level: 0, userText: '' }, script[i % script.length])
		live.secondsLeft = Math.max(0, live.secondsLeft - 3)
		i += 1
	}
	step()
	previewTimer = setInterval(step, 3000)
}

onBeforeUnmount(() => {
	clearInterval(previewTimer)
	stopMicTest()
	leaving = true
	if (engine && stage.value === 'live') engine.stop()
	// Any other stage (an error before or during connect) still has to release the microphone.
	else engine?.destroy()
})

// ---------- labels ----------
const phaseLabel = computed(
	() =>
		({
			connecting: __('Connecting…'),
			asha: __('Asha is speaking'),
			listening: __('Listening — answer when you’re ready'),
			thinking: __('Asha is thinking…'),
			ending: __('Wrapping up…'),
		})[live.phase] || ''
)
const clock = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
const statusLabel = (s) => ({ Passed: __('Passed'), 'Not Passed': __('Not yet'), Scoring: __('Scoring'), Abandoned: __('Not finished') })[s] || s
const pillClass = (s) => ({ Passed: 'is-good', 'Not Passed': 'is-bad' })[s] || ''
const formatDate = (d) => (d ? new Date(String(d).replace(' ', 'T')).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) : '')
function dotClass(n) {
	const d = info.data
	const scored = (d.history || []).filter((h) => h.status === 'Passed' || h.status === 'Not Passed')
	const h = scored[n - 1]
	if (!h) return ''
	return h.status === 'Passed' ? 'is-pass' : 'is-fail'
}
</script>

<style scoped>
.viva-page {
	min-height: 100vh;
	background: #ffffff;
	padding-bottom: 64px;
}
.viva-wrap {
	max-width: 880px;
	margin: 0 auto;
	padding: 28px 20px 0;
}
.viva-back {
	font-size: 14px;
	font-weight: 600;
	color: #0062cc;
}
.viva-muted {
	font-size: 13px;
	color: #52565c;
}
.viva-hero {
	margin-top: 18px;
	display: flex;
	flex-wrap: wrap;
	align-items: flex-end;
	justify-content: space-between;
	gap: 18px;
	padding: 28px;
	border-radius: 24px;
	color: #fff;
	background: linear-gradient(135deg, #00254c 0%, #013166 100%);
}
.viva-hero-text {
	max-width: 520px;
}
.viva-eyebrow {
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	opacity: 0.75;
}
.viva-hero h1 {
	margin-top: 6px;
	font-size: 28px;
	line-height: 34px;
	font-weight: 600;
}
.viva-hero-sub {
	margin-top: 8px;
	font-size: 14px;
	opacity: 0.85;
}
.viva-attempts {
	display: flex;
	align-items: center;
	gap: 6px;
}
.viva-dot {
	width: 12px;
	height: 12px;
	border-radius: 999px;
	border: 2px solid rgba(255, 255, 255, 0.5);
}
.viva-dot.is-pass {
	background: #35c759;
	border-color: #35c759;
}
.viva-dot.is-fail {
	background: #f03e3e;
	border-color: #f03e3e;
}
.viva-attempts-label {
	margin-left: 6px;
	font-size: 13px;
	font-weight: 600;
}
.viva-note {
	margin-top: 16px;
	display: flex;
	gap: 12px;
	padding: 14px 18px;
	border-radius: 16px;
	font-size: 14px;
	color: #080e14;
	background: #f4f9ff;
	border: 1px solid #cfe5ff;
}
.viva-note.is-good {
	background: #d6f4de;
	border-color: #8adb9f;
	color: #04742d;
}
.viva-note.is-warn {
	background: #ffeecc;
	border-color: #ffcf66;
	color: #8a5a00;
}
.viva-grid {
	margin-top: 18px;
	display: grid;
	gap: 16px;
}
@media (min-width: 768px) {
	.viva-grid {
		grid-template-columns: 1.2fr 1fr;
	}
}
.viva-card {
	padding: 22px 24px;
	border-radius: 24px;
	background: #fff;
	border: 1px solid #e6e7e8;
	box-shadow: 0 1px 12px rgba(0, 0, 0, 0.12);
}
.viva-card h2 {
	font-size: 18px;
	line-height: 24px;
	font-weight: 600;
	color: #080e14;
}
.viva-error {
	color: #f03e3e;
	font-size: 14px;
}
.viva-steps {
	margin-top: 12px;
	display: grid;
	gap: 12px;
	font-size: 14px;
	color: #080e14;
}
.viva-steps li {
	display: flex;
	gap: 10px;
	align-items: flex-start;
}
.viva-steps svg {
	margin-top: 3px;
	flex: none;
	color: #0062cc;
}
.viva-meter {
	height: 10px;
	border-radius: 999px;
	background: #f2f2f2;
	overflow: hidden;
}
.viva-meter-fill {
	height: 100%;
	border-radius: 999px;
	background: #027bff;
	transition: width 80ms linear;
}
.viva-mic-line {
	margin-top: 8px;
	font-size: 13px;
	color: #52565c;
}
.viva-start-error {
	margin-top: 10px;
	font-size: 13px;
	color: #b42323;
}
.viva-actions {
	margin-top: 18px;
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
}
.viva-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	height: 44px;
	padding: 0 22px;
	border-radius: 999px;
	font-size: 14px;
	font-weight: 600;
	color: #fff;
	background: #027bff;
	transition: opacity 0.15s ease;
}
.viva-btn:disabled {
	opacity: 0.45;
}
.viva-btn.is-ghost {
	background: #fff;
	color: #0062cc;
	border: 1px solid #e6e7e8;
}
.viva-btn.is-quiet {
	background: transparent;
	color: #52565c;
}
.viva-history {
	margin-top: 8px;
}
.viva-history li {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 4px;
	font-size: 14px;
	border-bottom: 1px solid #e6e7e8;
	cursor: pointer;
}
.viva-history li:last-child {
	border-bottom: 0;
}
.viva-history-n {
	font-weight: 600;
	color: #52565c;
	width: 28px;
}
.viva-history-score {
	width: 44px;
	text-align: right;
	font-weight: 600;
}
.viva-pill {
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #f2f2f2;
	color: #52565c;
}
.viva-pill.is-good {
	background: #d6f4de;
	color: #04742d;
}
.viva-pill.is-bad {
	background: #fef0f0;
	color: #b42323;
}
/* call */
.viva-call {
	margin-top: 18px;
	border-radius: 24px;
	overflow: hidden;
	background: linear-gradient(180deg, #00254c 0%, #013166 60%, #02448c 100%);
	color: #fff;
	padding: 20px;
}
.viva-call-top {
	display: flex;
	align-items: center;
	gap: 12px;
}
.viva-progress {
	display: flex;
	gap: 6px;
}
.viva-progress span {
	width: 22px;
	height: 6px;
	border-radius: 999px;
	background: rgba(255, 255, 255, 0.2);
}
.viva-progress span.is-done {
	background: #35c759;
}
.viva-progress span.is-now {
	background: #fcde5a;
}
.viva-qlabel {
	flex: 1;
	font-size: 13px;
	font-weight: 600;
	opacity: 0.85;
}
.viva-timer {
	font-variant-numeric: tabular-nums;
	font-weight: 600;
	padding: 4px 12px;
	border-radius: 999px;
	background: rgba(255, 255, 255, 0.12);
}
.viva-timer.is-low {
	background: #f03e3e;
}
.viva-stage {
	padding: 36px 8px 24px;
	text-align: center;
}
.viva-avatar {
	position: relative;
	width: 112px;
	height: 112px;
	margin: 0 auto;
}
.viva-avatar-face {
	position: absolute;
	inset: 0;
	display: grid;
	place-items: center;
	border-radius: 999px;
	font-size: 44px;
	font-weight: 600;
	color: #00254c;
	background: linear-gradient(135deg, #ffffff, #cce5ff);
}
.viva-avatar-ring {
	position: absolute;
	inset: -10px;
	border-radius: 999px;
	border: 3px solid rgba(252, 222, 90, 0);
}
.viva-avatar.is-speaking .viva-avatar-ring {
	border-color: #fcde5a;
	animation: viva-pulse 1.2s ease-in-out infinite;
}
@keyframes viva-pulse {
	0%,
	100% {
		transform: scale(1);
		opacity: 1;
	}
	50% {
		transform: scale(1.08);
		opacity: 0.55;
	}
}
.viva-who {
	margin-top: 14px;
	font-size: 18px;
	font-weight: 600;
}
.viva-phase {
	margin-top: 2px;
	font-size: 13px;
	opacity: 0.75;
}
.viva-caption {
	max-width: 560px;
	margin: 16px auto 0;
	font-size: 18px;
	line-height: 27px;
	min-height: 54px;
}
.viva-you {
	border-radius: 20px;
	padding: 14px 18px;
	background: rgba(255, 255, 255, 0.08);
	border: 1px solid rgba(255, 255, 255, 0.12);
}
.viva-you.is-live {
	border-color: #35c759;
}
.viva-you-head {
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: 12px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	opacity: 0.8;
}
.viva-you p {
	margin-top: 6px;
	font-size: 15px;
	line-height: 22px;
	max-height: 110px;
	overflow-y: auto;
}
.viva-level {
	width: 48px;
	height: 6px;
	border-radius: 999px;
	background: rgba(255, 255, 255, 0.2);
	overflow: hidden;
}
.viva-level span {
	display: block;
	height: 100%;
	background: #35c759;
	transform-origin: left;
	transition: transform 80ms linear;
}
.viva-controls {
	margin-top: 18px;
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
	justify-content: center;
}
.viva-call .viva-btn.is-ghost {
	background: rgba(255, 255, 255, 0.1);
	border-color: rgba(255, 255, 255, 0.25);
	color: #fff;
	touch-action: none;
}
.viva-call .viva-btn.is-quiet {
	color: rgba(255, 255, 255, 0.7);
}
.viva-center {
	text-align: center;
	display: grid;
	justify-items: center;
	gap: 10px;
}
.viva-spinner {
	width: 40px;
	height: 40px;
	border-radius: 999px;
	border: 4px solid #e6f2ff;
	border-top-color: #027bff;
	animation: viva-spin 0.9s linear infinite;
}
@keyframes viva-spin {
	to {
		transform: rotate(360deg);
	}
}
@media (max-width: 640px) {
	.viva-hero {
		padding: 22px;
	}
	.viva-hero h1 {
		font-size: 22px;
		line-height: 28px;
	}
	.viva-controls .viva-btn {
		flex: 1 1 45%;
		padding: 0 12px;
		font-size: 13px;
		white-space: nowrap;
	}
	.viva-qlabel {
		white-space: nowrap;
		font-size: 12px;
	}
	.viva-progress span {
		width: 14px;
	}
}
</style>
