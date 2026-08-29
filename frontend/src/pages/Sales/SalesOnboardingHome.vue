<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div v-if="home.loading" class="grid min-h-[40vh] place-items-center text-sm text-[color:var(--il-muted)]">
			{{ __('Loading your onboarding…') }}
		</div>
		<div
			v-else-if="home.error"
			class="mx-auto max-w-3xl px-5 pt-16 text-center text-sm text-[color:var(--genius-red)]"
		>
			{{ home.error.messages?.[0] || __('Unable to load your Sales onboarding.') }}
			<button class="mt-3 block w-full font-semibold" style="color: #0075ff" @click="home.reload()">
				{{ __('Retry') }}
			</button>
		</div>
		<div v-else-if="home.data?.empty" class="mx-auto max-w-3xl px-5 pt-16 text-center">
			<h1 class="text-2xl font-semibold text-[color:var(--il-ink)]">{{ __('Sales CRT is not ready yet') }}</h1>
			<p class="mt-2 text-sm text-[color:var(--il-muted)]">{{ home.data.message }}</p>
		</div>
		<div v-else-if="home.data" class="mx-auto max-w-5xl px-5 pt-8">
			<section class="sales-hero rounded-[28px] px-6 py-8 text-white sm:px-10">
				<p class="text-xs font-semibold uppercase tracking-[0.22em] text-white/80">
					Infinity Learn · Sales CRT
				</p>
				<h1 class="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
					{{ __('Welcome, {0}').format(firstName) }}
				</h1>
				<p class="mt-3 max-w-2xl text-sm leading-6 text-white/85">
					{{
						__(
							'Classroom Readiness Training, then a live sales simulation. Finish CRT 1–5, review your rating, and unlock OJT.'
						)
					}}
				</p>
			</section>

			<section class="sales-card mt-6 p-5 sm:p-7">
				<div class="mb-4 flex items-end justify-between gap-3">
					<div>
						<h2 class="text-lg font-semibold text-[color:var(--il-ink)]">
							{{ __('Sales onboarding journey') }}
						</h2>
						<p class="text-sm text-[color:var(--il-muted)]">
							{{ __('CRT 1 → CRT 5 → Evaluation → OJT') }}
						</p>
					</div>
					<div class="text-right">
						<div class="text-2xl font-semibold tabular-nums" style="color: #0075ff">
							{{ Math.round(home.data.overall_progress || 0) }}%
						</div>
						<div class="text-xs text-[color:var(--il-muted)]">{{ __('Overall CRT') }}</div>
					</div>
				</div>
				<div class="flex flex-wrap gap-2">
					<button
						v-for="crt in home.data.crts"
						:key="crt.crt_number"
						type="button"
						class="sales-step"
						:class="crt.state"
						@click="openCrt(crt)"
					>
						<span class="sales-step-num">{{ crt.crt_number }}</span>
						<span class="sales-step-label">{{ crt.title }}</span>
						<span class="sales-step-state">{{ stateLabel(crt.state) }}</span>
					</button>
					<button type="button" class="sales-step" :class="evalStepClass" @click="goEval">
						<span class="sales-step-num">★</span>
						<span class="sales-step-label">{{ __('Evaluation') }}</span>
						<span class="sales-step-state">{{ evalLabel }}</span>
					</button>
					<button type="button" class="sales-step" :class="ojtStepClass" @click="$router.push({ name: 'SalesOJT' })">
						<span class="sales-step-num">◎</span>
						<span class="sales-step-label">{{ __('OJT') }}</span>
						<span class="sales-step-state">{{ home.data.ojt?.eligible ? __('Unlocked') : __('Locked') }}</span>
					</button>
				</div>
			</section>

			<div class="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
				<section class="sales-card p-5 sm:p-7">
					<p class="text-xs font-semibold uppercase tracking-[0.18em]" style="color: #0075ff">
						{{ __('Current learning') }}
					</p>
					<h2 class="mt-2 text-xl font-semibold text-[color:var(--il-ink)]">
						{{ currentTitle }}
					</h2>
					<p class="mt-2 text-sm text-[color:var(--il-muted)]">
						{{ currentDetail }}
					</p>
					<div class="mt-4 h-2 overflow-hidden rounded-full bg-[#e8f2ff]">
						<div
							class="h-full rounded-full"
							style="background: #0075ff"
							:style="{ width: `${current?.progress || 0}%` }"
						/>
					</div>
					<p class="mt-2 text-xs text-[color:var(--il-muted)]">
						{{ current?.lessons_done || 0 }}/{{ current?.lessons_total || 0 }}
						{{ __('sessions complete') }}
					</p>
					<div class="mt-5 flex flex-wrap gap-3">
						<button
							v-if="current && current.state !== 'locked' && current.state !== 'empty'"
							type="button"
							class="rounded-full px-5 py-2.5 text-sm font-semibold text-white"
							style="background: #0075ff"
							@click="continueLearning"
						>
							{{ __('Continue learning') }}
						</button>
						<button
							v-else-if="home.data.ojt?.eligible"
							type="button"
							class="rounded-full px-5 py-2.5 text-sm font-semibold text-white"
							style="background: #0075ff"
							@click="$router.push({ name: 'SalesOJT' })"
						>
							{{ __('Enter OJT') }}
						</button>
					</div>
				</section>

				<section class="sales-card p-5 sm:p-7">
					<h2 class="text-lg font-semibold text-[color:var(--il-ink)]">
						{{ __('Milestones') }}
					</h2>
					<ul v-if="home.data.milestones?.length" class="mt-4 space-y-3">
						<li
							v-for="(item, idx) in home.data.milestones"
							:key="idx"
							class="rounded-2xl border px-4 py-3"
							style="border-color: var(--il-border)"
						>
							<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ item.title }}</div>
							<div class="mt-0.5 text-xs text-[color:var(--il-muted)]">{{ item.detail }}</div>
						</li>
					</ul>
					<p v-else class="mt-4 text-sm text-[color:var(--il-muted)]">
						{{ __('Your next milestone will appear as you progress.') }}
					</p>
					<p v-if="home.data.ojt?.locked" class="mt-5 rounded-2xl bg-[#fff7e0] px-4 py-3 text-sm text-[color:var(--il-ink)]">
						<strong>{{ __('OJT locked.') }}</strong>
						{{ home.data.ojt.reason }}
					</p>
				</section>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'

const user = inject('$user')
const router = useRouter()

const home = createResource({
	url: 'lms.lms.sales_journey.get_onboarding_home',
	auto: true,
	cache: ['sales-onboarding-home'],
})

const firstName = computed(() => {
	const full = home.data?.learner?.full_name || user.data?.full_name || ''
	return full.split(' ')[0] || __('there')
})

const current = computed(() => home.data?.current)

const currentTitle = computed(() => {
	if (!current.value) return __('Sales CRT')
	return `${current.value.title}${current.value.current_lesson ? ' · ' + current.value.current_lesson.title : ''}`
})

const currentDetail = computed(() => {
	if (!current.value) return ''
	if (current.value.state === 'completed') {
		return __('Classroom CRTs are complete. Review your training evaluation, then enter OJT.')
	}
	if (current.value.state === 'locked') {
		return __('Finish the previous CRT to unlock this stage.')
	}
	return __('Stay on this CRT until every session is complete.')
})

const evalLabel = computed(() => {
	const status = home.data?.evaluation?.status
	if (status === 'Completed') return __('Done')
	if (status === 'Ready') return __('Ready')
	return __('Locked')
})

const evalStepClass = computed(() => {
	const status = home.data?.evaluation?.status
	if (status === 'Completed') return 'completed'
	if (status === 'Ready') return 'available'
	return 'locked'
})

const ojtStepClass = computed(() => (home.data?.ojt?.eligible ? 'available' : 'locked'))

const stateLabel = (state) =>
	({
		completed: __('Completed'),
		in_progress: __('In progress'),
		available: __('Current'),
		locked: __('Locked'),
		empty: __('Pending'),
	})[state] || state

const openCrt = (crt) => {
	if (crt.state === 'locked' || crt.state === 'empty') return
	router.push({ name: 'SalesCRT', params: { crtNumber: String(crt.crt_number) } })
}

const goEval = () => router.push({ name: 'SalesEvaluation' })

const continueLearning = () => {
	const lesson = current.value?.current_lesson
	if (lesson?.number) {
		const [chapterNumber, lessonNumber] = String(lesson.number).split('-')
		router.push({
			name: 'Lesson',
			params: {
				courseName: home.data.course,
				chapterNumber,
				lessonNumber,
			},
		})
		return
	}
	openCrt(current.value)
}
</script>
