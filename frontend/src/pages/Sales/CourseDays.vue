<template>
	<div class="cd-page">
		<div class="cd-wrap">
			<button class="cd-back" @click="$router.push({ name: 'CourseDetail', params: { courseName } })">← {{ __('Course') }}</button>

			<div v-if="journey.loading && !data" class="cd-muted mt-10">{{ __('Loading…') }}</div>
			<div v-else-if="journey.error" class="cd-card mt-6" style="color: #b42323">
				{{ journey.error.messages?.[0] || __('This course could not be loaded.') }}
			</div>

			<template v-else-if="data">
				<section class="cd-hero">
					<div class="min-w-0">
						<p class="cd-eyebrow">{{ __('Day-by-day journey') }}</p>
						<h1>{{ data.title }}</h1>
						<p v-if="data.description" class="cd-sub">{{ data.description }}</p>
						<button v-if="current" class="cd-cta" @click="open(current)">
							{{ current.state === 'viva_pending' ? __('Take the voice viva') : current.lessons_done ? __('Continue') : __('Start') }}
							· {{ __('Day') }} {{ current.day }}
						</button>
					</div>
					<div class="cd-ring" :style="ringStyle">
						<div>
							<b>{{ Math.round(data.progress) }}%</b><span>{{ __('done') }}</span>
						</div>
					</div>
				</section>

				<p v-if="!data.gated" class="cd-note">
					{{ __('You see every day unlocked because you are staff on this course. Learners unlock one day at a time.') }}
				</p>

				<section class="cd-card mt-5">
					<div class="cd-card-head">
						<h2>{{ __('Your days') }}</h2>
						<span class="cd-muted">{{ doneCount }} {{ __('of') }} {{ data.days.length }} {{ __('done') }}</span>
					</div>
					<ol class="cd-list">
						<li v-for="d in data.days" :key="d.day">
							<button class="cd-row" :class="rowClass(d)" :disabled="d.state === 'locked' && data.gated" @click="open(d)">
								<span class="cd-marker">
									<Check v-if="d.state === 'completed'" class="h-4 w-4" />
									<Lock v-else-if="d.state === 'locked' && data.gated" class="h-4 w-4" />
									<Mic v-else-if="d.state === 'viva_pending'" class="h-4 w-4" />
									<template v-else>{{ d.day }}</template>
								</span>
								<span class="min-w-0 flex-1">
									<span class="cd-title">{{ __('Day') }} {{ d.day }} · {{ d.title }}</span>
									<span class="cd-meta">{{ meta(d) }}</span>
									<span v-if="d.state === 'in_progress'" class="cd-bar"><span :style="{ width: `${d.progress}%` }" /></span>
								</span>
								<span class="cd-pill" :class="pillClass(d)">{{ pill(d) }}</span>
								<ChevronRight class="h-4 w-4 flex-none text-[color:var(--il-muted)]" />
							</button>
						</li>
					</ol>
				</section>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { Check, ChevronRight, Lock, Mic } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const courseName = computed(() => route.params.courseName)

const journey = createResource({
	url: 'lms.lms.day_journey.get_course_journey',
	makeParams: () => ({ course: courseName.value }),
	auto: true,
})
const data = computed(() => journey.data)
const doneCount = computed(() => (data.value?.days || []).filter((d) => d.state === 'completed').length)
const current = computed(() => (data.value?.days || []).find((d) => ['available', 'in_progress', 'viva_pending'].includes(d.state)))

const ringStyle = computed(() => ({ background: `conic-gradient(#fcde5a ${(data.value?.progress || 0) * 3.6}deg, rgba(255,255,255,0.16) 0)` }))
const meta = (d) =>
	d.state === 'viva_pending'
		? d.viva?.blocked
			? __('All attempts used · your Training Manager can unlock more')
			: `${__('Sessions done · voice viva to finish the day')} · ${d.viva?.attempts_left ?? 3} ${__('attempts left')}`
		: `${d.lessons_done} ${__('of')} ${d.lessons_total} ${__('sessions')}`
const pill = (d) =>
	({ completed: __('Done'), viva_pending: __('Voice viva'), in_progress: __('Today'), available: __('Start'), locked: __('Locked'), empty: __('No sessions') })[d.state] || ''
const pillClass = (d) => ({ completed: 'is-good', viva_pending: 'is-warn', in_progress: 'is-now', available: 'is-now' })[d.state] || ''
const rowClass = (d) => ({ 'is-current': current.value && d.day === current.value.day, 'is-locked': d.state === 'locked' && data.value.gated })

function open(d) {
	if (d.state === 'viva_pending') router.push({ name: 'DayViva', params: { courseName: courseName.value, day: d.slug } })
	else router.push({ name: 'DayDetail', params: { courseName: courseName.value, day: d.slug } })
}
</script>

<style scoped>
.cd-page {
	min-height: 100vh;
	background: #fff;
	padding-bottom: 64px;
}
.cd-wrap {
	max-width: 880px;
	margin: 0 auto;
	padding: 28px 20px 0;
}
.cd-back {
	font-size: 14px;
	font-weight: 600;
	color: #0062cc;
}
.cd-muted {
	font-size: 13px;
	color: #52565c;
}
.cd-hero {
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
.cd-eyebrow {
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	opacity: 0.75;
}
.cd-hero h1 {
	margin-top: 6px;
	font-size: 28px;
	line-height: 34px;
	font-weight: 600;
}
.cd-sub {
	margin-top: 6px;
	font-size: 14px;
	opacity: 0.85;
	max-width: 520px;
}
.cd-cta {
	margin-top: 16px;
	height: 44px;
	padding: 0 22px;
	border-radius: 999px;
	font-size: 14px;
	font-weight: 600;
	color: #013166;
	background: #fff;
}
.cd-ring {
	width: 120px;
	height: 120px;
	border-radius: 999px;
	display: grid;
	place-items: center;
	flex: none;
}
.cd-ring > div {
	width: 94px;
	height: 94px;
	border-radius: 999px;
	background: #00254c;
	display: grid;
	place-content: center;
	text-align: center;
}
.cd-ring b {
	font-size: 24px;
	font-weight: 600;
}
.cd-ring span {
	font-size: 11px;
	opacity: 0.7;
	text-transform: uppercase;
}
.cd-note {
	margin-top: 14px;
	padding: 10px 16px;
	border-radius: 14px;
	font-size: 13px;
	background: #f4f9ff;
	border: 1px solid #cfe5ff;
}
.cd-card {
	padding: 18px 16px;
	border-radius: 24px;
	background: #fff;
	border: 1px solid #e6e7e8;
	box-shadow: 0 1px 12px rgba(0, 0, 0, 0.12);
}
.cd-card-head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	padding: 0 8px 8px;
}
.cd-card-head h2 {
	font-size: 18px;
	font-weight: 600;
}
.cd-list li + li {
	margin-top: 4px;
}
.cd-row {
	width: 100%;
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 11px 12px;
	border-radius: 16px;
	border: 1px solid transparent;
	text-align: left;
}
.cd-row:hover:not(:disabled) {
	background: #f4f9ff;
}
.cd-row.is-current {
	background: #f4f9ff;
	border-color: #cfe5ff;
}
.cd-row.is-locked {
	opacity: 0.6;
}
.cd-marker {
	width: 40px;
	height: 40px;
	flex: none;
	display: grid;
	place-items: center;
	border-radius: 999px;
	font-size: 15px;
	font-weight: 600;
	background: #e6f2ff;
	color: #0062cc;
}
.cd-row.is-current .cd-marker {
	background: #027bff;
	color: #fff;
}
.cd-title {
	display: block;
	font-size: 15px;
	font-weight: 500;
	color: #080e14;
}
.cd-meta {
	display: block;
	font-size: 12px;
	color: #52565c;
}
.cd-bar {
	display: block;
	margin-top: 6px;
	height: 4px;
	border-radius: 999px;
	background: #e6e7e8;
	overflow: hidden;
}
.cd-bar span {
	display: block;
	height: 100%;
	background: #027bff;
}
.cd-pill {
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
	background: #f2f2f2;
	color: #52565c;
	flex: none;
}
.cd-pill.is-good {
	background: #d6f4de;
	color: #04742d;
}
.cd-pill.is-warn {
	background: #ffeecc;
	color: #8a5a00;
}
.cd-pill.is-now {
	background: #027bff;
	color: #fff;
}
</style>
