<template>
	<div class="il-page min-h-full">
		<!-- Page header: IL "Home" title + program pill -->
		<header class="flex flex-wrap items-center justify-between gap-3 pt-5 pb-2">
			<h1 class="il-page-title">{{ __('Home') }}</h1>
			<span class="il-pill text-sm sm:text-base">
				<GraduationCap class="h-5 w-5 stroke-[1.75]" />
				{{ __('Sales Onboarding · CRT') }}
			</span>
		</header>

		<div v-if="home.loading || (!home.data && !home.error)" class="mt-6 space-y-6">
			<div class="h-40 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="flex gap-4 overflow-hidden">
				<div v-for="n in 6" :key="n" class="h-32 w-32 shrink-0 animate-pulse rounded-2xl bg-[#e6e7e8]" />
			</div>
		</div>

		<div v-else-if="home.error" class="il-card mx-auto mt-10 max-w-lg p-8 text-center">
			<p class="text-sm text-[color:var(--il-error-50)]">
				{{ home.error.messages?.[0] || __('Unable to load your Sales onboarding.') }}
			</p>
			<button class="il-btn il-btn-primary mt-4" @click="home.reload()">{{ __('Retry') }}</button>
		</div>

		<div v-else-if="home.data?.empty" class="il-card mx-auto mt-10 max-w-lg p-8 text-center">
			<h2 class="text-xl font-semibold text-[color:var(--il-ink)]">{{ __('Sales CRT is not ready yet') }}</h2>
			<p class="mt-2 text-sm text-[color:var(--il-muted)]">{{ home.data.message }}</p>
		</div>

		<template v-else-if="home.data">
			<!-- Greeting + progress banner (IL promo-banner style) -->
			<section class="il-home-banner mt-4">
				<div class="relative z-[1] flex min-w-0 flex-1 flex-col gap-2">
					<p class="text-sm font-medium text-white/75">{{ greeting }}, {{ firstName }} 👋</p>
					<h2 class="text-2xl font-semibold leading-tight text-white sm:text-[1.75rem]">
						{{ bannerTitle }}
					</h2>
					<p class="max-w-xl text-sm leading-6 text-white/80">{{ bannerDetail }}</p>
					<div class="mt-3 flex flex-wrap gap-3">
						<button
							v-if="current && current.state !== 'locked' && current.state !== 'empty' && current.state !== 'completed'"
							type="button"
							class="il-btn il-btn-light"
							@click="continueLearning"
						>
							<PlayCircle class="h-4 w-4" />
							{{ __('Continue learning') }}
						</button>
						<button
							v-else-if="home.data.ojt?.eligible"
							type="button"
							class="il-btn il-btn-light"
							@click="$router.push({ name: 'SalesOJT' })"
						>
							<PhoneCall class="h-4 w-4" />
							{{ __('Enter OJT') }}
						</button>
						<button
							v-else-if="home.data.evaluation?.status === 'Ready' || home.data.evaluation?.status === 'Completed'"
							type="button"
							class="il-btn il-btn-light"
							@click="goEval"
						>
							<Star class="h-4 w-4" />
							{{ __('View evaluation') }}
						</button>
					</div>
				</div>
				<div class="il-home-ring" :style="{ '--p': overall }" role="img" :aria-label="`${overall}% ${__('complete')}`">
					<div class="il-home-ring-inner">
						<span class="text-2xl font-semibold tabular-nums text-white">{{ overall }}%</span>
						<span class="text-[11px] font-medium uppercase tracking-wider text-white/70">{{ __('CRT done') }}</span>
					</div>
				</div>
			</section>

			<!-- Journey tiles (IL subject-tile pattern) -->
			<section class="mt-8">
				<div class="mb-4 flex items-end justify-between gap-3">
					<h2 class="il-section-title !mb-0">{{ __('Your journey') }}</h2>
					<span class="text-sm text-[color:var(--il-muted)]">{{ completedCount }}/{{ totalSteps }} {{ __('steps complete') }}</span>
				</div>
				<div class="il-journey no-scrollbar">
					<button
						v-for="crt in home.data.crts"
						:key="crt.crt_number"
						type="button"
						class="il-journey-step"
						:class="`is-${crt.state}`"
						:disabled="!home.data.is_staff && (crt.state === 'locked' || crt.state === 'empty')"
						@click="openCrt(crt)"
					>
						<span class="il-journey-tile">
							<Check v-if="crt.state === 'completed'" class="h-7 w-7" />
							<Lock v-else-if="crt.state === 'locked' || crt.state === 'empty'" class="h-6 w-6" />
							<span v-else class="text-2xl font-semibold">{{ crt.crt_number }}</span>
						</span>
						<span class="il-journey-label">{{ crt.title }}</span>
						<span class="il-journey-state">{{ stateLabel(crt.state) }}</span>
					</button>
					<button type="button" class="il-journey-step is-amber" :class="`is-${evalStepClass}`" @click="goEval">
						<span class="il-journey-tile"><Star class="h-7 w-7" /></span>
						<span class="il-journey-label">{{ __('Evaluation') }}</span>
						<span class="il-journey-state">{{ evalLabel }}</span>
					</button>
					<button
						type="button"
						class="il-journey-step is-green"
						:class="`is-${ojtStepClass}`"
						@click="$router.push({ name: 'SalesOJT' })"
					>
						<span class="il-journey-tile"><PhoneCall class="h-7 w-7" /></span>
						<span class="il-journey-label">{{ __('OJT') }}</span>
						<span class="il-journey-state">{{ home.data.ojt?.eligible ? __('Unlocked') : __('Locked') }}</span>
					</button>
				</div>
			</section>

			<div class="mt-8 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
				<!-- Current learning -->
				<section class="il-card p-6">
					<p class="text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--il-primary-40)]">
						{{ __('Resume learning') }}
					</p>
					<h3 class="mt-2 text-lg font-semibold text-[color:var(--il-ink)]">{{ currentTitle }}</h3>
					<p class="mt-1 text-sm text-[color:var(--il-muted)]">{{ currentDetail }}</p>
					<div class="mt-5 flex items-center gap-3">
						<div class="h-2 flex-1 overflow-hidden rounded-full bg-[color:var(--il-primary-95)]">
							<div
								class="h-full rounded-full bg-[color:var(--il-primary-50)] transition-all duration-500"
								:style="{ width: `${current?.progress || 0}%` }"
							/>
						</div>
						<span class="text-sm font-semibold tabular-nums text-[color:var(--il-ink)]">{{ Math.round(current?.progress || 0) }}%</span>
					</div>
					<p class="mt-2 text-xs text-[color:var(--il-muted)]">
						{{ current?.lessons_done || 0 }}/{{ current?.lessons_total || 0 }} {{ __('sessions complete') }}
					</p>
					<button
						v-if="current && current.state !== 'locked' && current.state !== 'empty' && current.state !== 'completed'"
						type="button"
						class="il-btn il-btn-primary mt-5"
						@click="continueLearning"
					>
						{{ __('Continue') }}
						<ChevronRight class="h-4 w-4" />
					</button>
				</section>

				<!-- Milestones -->
				<section class="il-card p-6">
					<h3 class="text-lg font-semibold text-[color:var(--il-ink)]">{{ __('Milestones') }}</h3>
					<ul v-if="home.data.milestones?.length" class="mt-4 space-y-3">
						<li
							v-for="(item, idx) in home.data.milestones"
							:key="idx"
							class="flex items-start gap-3 rounded-2xl bg-[color:var(--il-neutral-95)] px-4 py-3"
						>
							<span class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[color:var(--il-primary-95)] text-[color:var(--il-primary-40)]">
								<Flag class="h-3.5 w-3.5" />
							</span>
							<div class="min-w-0">
								<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ item.title }}</div>
								<div class="mt-0.5 text-xs text-[color:var(--il-muted)]">{{ item.detail }}</div>
							</div>
						</li>
					</ul>
					<p v-else class="mt-4 text-sm text-[color:var(--il-muted)]">
						{{ __('Your next milestone will appear as you progress.') }}
					</p>
				</section>
			</div>

			<!-- OJT locked notice (IL gold "Stuck on a problem?" card) -->
			<section
				v-if="home.data.ojt?.locked && !home.data.is_staff"
				class="mt-6 flex items-start gap-4 rounded-3xl bg-[color:var(--il-secondary-95)] p-5 shadow-[0_1px_12px_rgba(0,0,0,0.08)]"
			>
				<span class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[color:var(--il-secondary-50)] text-[color:var(--il-ink)]">
					<Lock class="h-5 w-5" />
				</span>
				<div>
					<h3 class="text-base font-semibold text-[color:var(--il-ink)]">{{ __('OJT is locked') }}</h3>
					<p class="mt-1 text-sm text-[color:var(--il-muted)]">{{ home.data.ojt.reason }}</p>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { Check, ChevronRight, Flag, GraduationCap, Lock, PhoneCall, PlayCircle, Star } from 'lucide-vue-next'

const user = inject('$user')
const router = useRouter()

const home = createResource({
	url: 'lms.lms.sales_journey.get_onboarding_home',
	auto: true,
})

const firstName = computed(() => {
	const full = home.data?.learner?.full_name || user.data?.full_name || ''
	return full.split(' ')[0] || __('there')
})

const current = computed(() => home.data?.current)

const overall = computed(() => Math.round(home.data?.overall_progress || 0))

const greeting = computed(() => {
	const hour = new Date().getHours()
	if (hour < 12) return __('Good morning')
	if (hour < 17) return __('Good afternoon')
	return __('Good evening')
})

const totalSteps = computed(() => (home.data?.crts?.length || 0) + 2)

const completedCount = computed(() => {
	const crts = (home.data?.crts || []).filter((c) => c.state === 'completed').length
	const evalDone = home.data?.evaluation?.status === 'Completed' ? 1 : 0
	return crts + evalDone
})

const bannerTitle = computed(() => {
	if (home.data?.ojt?.eligible) return __("You're ready for OJT")
	if (current.value?.state === 'completed') return __('Classroom training complete')
	if (current.value) return __('Up next: {0}', [current.value.title])
	return __('Your Sales onboarding')
})

const bannerDetail = computed(() =>
	__(
		'Classroom Readiness Training, then a live sales simulation. Finish CRT 1–5, review your rating, and unlock OJT.'
	)
)

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
	if (!home.data?.is_staff && (crt.state === 'locked' || crt.state === 'empty')) return
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

<style scoped>
.il-home-banner {
	position: relative;
	display: flex;
	align-items: center;
	gap: 1.5rem;
	overflow: hidden;
	border-radius: 24px;
	background: var(--il-promo);
	padding: 1.75rem;
}

/* Soft IL-blue glow in the corner, echoing the student app's promo banner. */
.il-home-banner::after {
	content: '';
	position: absolute;
	right: -4rem;
	top: -4rem;
	width: 16rem;
	height: 16rem;
	border-radius: 999px;
	background: radial-gradient(circle, rgba(2, 123, 255, 0.55) 0%, rgba(2, 123, 255, 0) 70%);
}

.il-home-ring {
	--p: 0;
	position: relative;
	z-index: 1;
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 8.5rem;
	height: 8.5rem;
	border-radius: 999px;
	background: conic-gradient(#fcde5a calc(var(--p) * 1%), rgba(255, 255, 255, 0.16) 0);
}

.il-home-ring-inner {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	width: 6.9rem;
	height: 6.9rem;
	border-radius: 999px;
	background: #00254c;
}

.il-journey {
	display: flex;
	gap: 1rem;
	overflow-x: auto;
	padding: 0.25rem 0.25rem 0.75rem;
	margin: 0 -0.25rem;
}

.il-journey-step {
	display: flex;
	width: 7.5rem;
	flex-shrink: 0;
	flex-direction: column;
	align-items: center;
	gap: 0.35rem;
	text-align: center;
	transition: transform 0.15s ease;
}

.il-journey-step:not(:disabled):hover {
	transform: translateY(-2px);
}

.il-journey-step:disabled {
	cursor: not-allowed;
}

.il-journey-tile {
	display: grid;
	place-items: center;
	width: 7.5rem;
	height: 5.25rem;
	border-radius: 16px;
	background: var(--il-primary-95);
	color: var(--il-primary-50);
	transition: box-shadow 0.15s ease;
}

.il-journey-step:not(:disabled):hover .il-journey-tile {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.il-journey-label {
	max-width: 100%;
	overflow: hidden;
	color: var(--il-ink);
	font-size: 0.875rem;
	font-weight: 500;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.il-journey-state {
	border-radius: 999px;
	padding: 0.1rem 0.6rem;
	background: var(--il-neutral-95);
	color: var(--il-muted);
	font-size: 0.6875rem;
	font-weight: 600;
}

/* States */
.il-journey-step.is-completed .il-journey-tile {
	background: var(--il-success-95);
	color: var(--il-success-50);
}

.il-journey-step.is-completed .il-journey-state {
	background: var(--il-success-95);
	color: var(--il-success-50);
}

.il-journey-step.is-in_progress .il-journey-tile,
.il-journey-step.is-available .il-journey-tile {
	background: var(--il-primary-50);
	color: #ffffff;
	box-shadow: 0 6px 16px rgba(2, 123, 255, 0.35);
}

.il-journey-step.is-in_progress .il-journey-state,
.il-journey-step.is-available .il-journey-state {
	background: var(--il-primary-95);
	color: var(--il-primary-40);
}

.il-journey-step.is-amber .il-journey-tile {
	background: var(--il-warning-95);
	color: var(--il-warning-50);
}

.il-journey-step.is-green .il-journey-tile {
	background: var(--il-success-95);
	color: var(--il-success-50);
}

.il-journey-step.is-locked .il-journey-tile,
.il-journey-step.is-empty .il-journey-tile {
	background: var(--il-neutral-95);
	color: var(--il-neutral-60);
	box-shadow: none;
}

@media (max-width: 640px) {
	.il-home-banner {
		flex-direction: column-reverse;
		align-items: flex-start;
		padding: 1.25rem;
	}

	.il-home-ring {
		width: 6.5rem;
		height: 6.5rem;
	}

	.il-home-ring-inner {
		width: 5.25rem;
		height: 5.25rem;
	}
}
</style>
