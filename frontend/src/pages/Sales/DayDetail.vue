<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div class="mx-auto max-w-4xl px-5 pt-8">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="back">
				← {{ isCrt ? __('Home') : detail.data?.course_title || __('Course') }}
			</button>

			<div v-if="detail.loading && !detail.data" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading…') }}
			</div>
			<div v-else-if="detail.error" class="mt-10 text-sm text-[color:var(--genius-red)]">
				{{ detail.error.messages?.[0] || __('This day could not be loaded.') }}
			</div>
			<div v-else-if="day" class="mt-6">
				<p class="text-xs font-semibold uppercase tracking-[0.2em]" style="color: #0075ff">
					{{ __('Day') }} {{ day.day }} {{ __('of') }} {{ journey.length }} · {{ detail.data.course_title }}
				</p>
				<div class="mt-2 flex flex-wrap items-end justify-between gap-3">
					<h1 class="text-3xl font-semibold text-[color:var(--il-ink)]">{{ day.title }}</h1>
					<span class="rounded-full px-3 py-1 text-xs font-semibold" :class="badgeClass">
						{{ stateLabel(day.state) }}
					</span>
				</div>
				<p class="mt-2 text-sm text-[color:var(--il-muted)]">
					{{ day.lessons_done }}/{{ day.lessons_total }} {{ __('sessions complete') }} · {{ day.progress }}%
				</p>

				<div v-if="day.state === 'locked'" class="sales-card mt-6 p-6 text-sm text-[color:var(--il-ink)]">
					{{ __('Finish the previous day before this one unlocks.') }}
				</div>
				<div v-else-if="!day.lessons_total" class="sales-card mt-6 p-6 text-sm text-[color:var(--il-muted)]">
					{{ __('No sessions have been added to this day yet.') }}
				</div>
				<ol v-else class="mt-6 space-y-3">
					<li
						v-for="lesson in day.lessons"
						:key="lesson.name"
						class="sales-card flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6"
					>
						<div>
							<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ lesson.title }}</div>
							<div class="text-xs text-[color:var(--il-muted)]">{{ sessionMeta(lesson) }}</div>
						</div>
						<button
							v-if="!lesson.locked && !lesson.complete"
							type="button"
							class="rounded-full px-4 py-2 text-xs font-semibold text-white"
							style="background: #0075ff"
							@click="openLesson(lesson)"
						>
							{{ __('Open') }}
						</button>
						<button
							v-else-if="lesson.complete"
							type="button"
							class="rounded-full border px-4 py-2 text-xs font-semibold"
							style="border-color: #d7e4f7; color: #0075ff"
							@click="openLesson(lesson)"
						>
							{{ __('Review') }}
						</button>
						<span v-else class="text-xs font-semibold text-[color:var(--il-muted)]">{{ __('Locked') }}</span>
					</li>
				</ol>

				<div v-if="day.viva?.required || day.viva?.can_try" class="viva-card mt-6" :class="{ 'is-ready': vivaReady }">
					<div class="viva-icon"><Mic class="h-5 w-5" /></div>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ __('Voice viva') }}</div>
						<div class="text-xs text-[color:var(--il-muted)]">{{ vivaLine }}</div>
					</div>
					<button
						v-if="day.viva.passed || vivaReady || day.viva.history?.length"
						type="button"
						class="rounded-full px-4 py-2 text-xs font-semibold"
						:class="vivaReady ? 'text-white' : 'border'"
						:style="vivaReady ? 'background: #0075ff' : 'border-color: #d7e4f7; color: #0075ff'"
						@click="openViva"
					>
						{{ vivaReady ? (day.viva.can_try ? __('Try the viva') : __('Start viva')) : __('View') }}
					</button>
				</div>

				<div class="mt-8 flex flex-wrap gap-3">
					<button
						v-if="prevDay"
						type="button"
						class="rounded-full border px-4 py-2 text-sm font-semibold"
						style="border-color: #d7e4f7"
						@click="goDay(prevDay)"
					>
						← {{ __('Day') }} {{ prevDay.day }}
					</button>
					<button
						v-if="nextDay"
						type="button"
						class="rounded-full border px-4 py-2 text-sm font-semibold"
						style="border-color: #d7e4f7"
						@click="goDay(nextDay)"
					>
						{{ __('Day') }} {{ nextDay.day }} →
					</button>
					<button
						v-else-if="detail.data.next_step === 'evaluation'"
						type="button"
						class="rounded-full px-4 py-2 text-sm font-semibold text-white"
						style="background: #0075ff"
						@click="$router.push({ name: 'SalesEvaluation' })"
					>
						{{ __('Training evaluation') }}
					</button>
					<button
						v-else
						type="button"
						class="rounded-full px-4 py-2 text-sm font-semibold text-white"
						style="background: #0075ff"
						@click="$router.push({ name: 'CourseDays', params: { courseName } })"
					>
						{{ __('All days') }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { Mic } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const courseName = computed(() => route.params.courseName)
const isCrt = computed(() => courseName.value === 'sales-crt')

const detail = createResource({
	url: 'lms.lms.day_journey.get_day_detail',
	makeParams: () => ({ course: courseName.value, day: route.params.day }),
	auto: true,
	onSuccess(data) {
		// Canonical address: /courses/<course>/days/<n>-<title-slug>
		if (data?.day?.slug && route.params.day !== data.day.slug) {
			router.replace({ name: 'DayDetail', params: { courseName: courseName.value, day: data.day.slug } })
		}
	},
})
watch(
	() => [route.params.courseName, parseInt(route.params.day)],
	(next, prev) => {
		if (!prev || next[0] !== prev[0] || next[1] !== prev[1]) detail.reload()
	}
)

const day = computed(() => detail.data?.day)
const journey = computed(() => detail.data?.journey || [])
const prevDay = computed(() => journey.value.find((d) => d.day === (day.value?.day || 0) - 1))
const nextDay = computed(() => journey.value.find((d) => d.day === (day.value?.day || 0) + 1))

const badgeClass = computed(() => {
	const state = day.value?.state
	if (state === 'completed') return 'bg-green-50 text-green-700'
	if (state === 'viva_pending') return 'bg-amber-50 text-amber-700'
	if (state === 'in_progress' || state === 'available') return 'bg-[#e8f2ff] text-[#005fe0]'
	return 'bg-slate-100 text-slate-500'
})
const stateLabel = (state) =>
	({
		completed: __('Completed'),
		viva_pending: __('Viva pending'),
		in_progress: __('In progress'),
		available: __('Available'),
		locked: __('Locked'),
		empty: __('No sessions'),
	})[state] || state

const vivaReady = computed(
	() => (day.value?.state === 'viva_pending' && !day.value?.viva?.blocked) || Boolean(day.value?.viva?.can_try && !day.value?.viva?.passed)
)
const vivaLine = computed(() => {
	const d = day.value
	const v = d?.viva || {}
	if (v.passed) return __('Passed · this day is complete')
	if (v.can_try) return __('Staff preview · try this day’s viva any time (learners get it after the sessions)')
	if (v.blocked) return __('All attempts used · your Training Manager can unlock more')
	if (d?.state === 'viva_pending') return `${__('A 3–4 minute spoken check on today’s content')} · ${v.attempts_left ?? 3} ${__('attempts left')}`
	return __('Unlocks when all sessions above are done')
})

const sessionMeta = (lesson) => {
	const row = (detail.data?.sessions || []).find((s) => s.lesson === lesson.name)
	if (!row) return lesson.complete ? __('Completed') : __('Session')
	return [row.time_label, row.stakeholder].filter(Boolean).join(' · ')
}

const goDay = (d) => router.push({ name: 'DayDetail', params: { courseName: courseName.value, day: d.slug } })
const openViva = () => router.push({ name: 'DayViva', params: { courseName: courseName.value, day: day.value.slug } })
const back = () =>
	isCrt.value ? router.push({ name: 'StudentDashboard' }) : router.push({ name: 'CourseDays', params: { courseName: courseName.value } })

const openLesson = (lesson) => {
	const [chapterNumber, lessonNumber] = String(lesson.number).split('-')
	router.push({ name: 'Lesson', params: { courseName: courseName.value, chapterNumber, lessonNumber } })
}
</script>

<style scoped>
.viva-card {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 16px 20px;
	border-radius: 20px;
	border: 1px dashed #cfe5ff;
	background: #ffffff;
}
.viva-card.is-ready {
	border-style: solid;
	background: #f4f9ff;
}
.viva-icon {
	display: grid;
	place-items: center;
	width: 40px;
	height: 40px;
	border-radius: 999px;
	flex: none;
	background: #e6f2ff;
	color: #0062cc;
}
</style>
