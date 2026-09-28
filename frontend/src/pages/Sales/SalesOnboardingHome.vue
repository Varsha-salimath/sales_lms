<template>
	<div class="il-page min-h-full">
		<!-- Page header: program title + Home pill with quick actions -->
		<header class="flex flex-wrap items-center justify-end gap-3 pt-5 pb-2">
			<div class="flex flex-wrap items-center justify-end gap-2">
				<Tooltip :text="__('Search')" placement="bottom">
					<button
						type="button"
						class="il-header-icon-btn"
						:aria-label="__('Search')"
						@click="goSearch"
					>
						<Search class="h-5 w-5 stroke-[1.75]" />
					</button>
				</Tooltip>
				<Tooltip :text="__('Notifications')" placement="bottom">
					<button
						type="button"
						class="il-header-icon-btn relative"
						:aria-label="__('Notifications')"
						@click="goNotifications"
					>
						<Bell class="h-5 w-5 stroke-[1.75]" />
						<span
							v-if="unreadCount.data"
							class="absolute -top-0.5 -end-0.5 min-w-[1.125rem] rounded-full bg-[color:var(--il-error-50)] px-1 text-center text-[10px] font-semibold leading-4 text-white tabular-nums"
						>
							{{ unreadCount.data > 99 ? '99+' : unreadCount.data }}
						</span>
					</button>
				</Tooltip>
				<span class="il-pill text-sm sm:text-base">
					<Home class="h-5 w-5 stroke-[1.75]" />
					{{ __('Home') }}
				</span>
			</div>
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
			<!-- One banner: where you are and one button -->
			<section class="il-home-banner mt-4">
				<div class="relative z-[1] flex min-w-0 flex-1 flex-col gap-1.5">
					<p class="text-sm font-medium text-white/75">{{ greeting }}, {{ firstName }} 👋</p>
					<h2 class="text-2xl font-semibold leading-tight text-white sm:text-[1.75rem]">{{ bannerTitle }}</h2>
					<p class="text-sm leading-6 text-white/80">{{ bannerDetail }}</p>
					<p
						v-if="home.data?.learner?.training_manager?.full_name"
						class="text-sm text-white/75"
					>
						{{ __('Training Manager') }}:
						<span class="font-medium text-white">{{
							home.data.learner.training_manager.full_name
						}}</span>
					</p>
					<div v-if="primaryAction" class="mt-3">
						<button type="button" class="il-btn il-btn-light" @click="primaryAction.run">
							<component :is="primaryAction.icon" class="h-4 w-4" />
							{{ primaryAction.label }}
						</button>
					</div>
				</div>
				<div class="il-home-ring" :style="{ '--p': overall }" role="img" :aria-label="`${overall}% ${__('complete')}`">
					<div class="il-home-ring-inner">
						<span class="text-2xl font-semibold tabular-nums text-white">{{ overall }}%</span>
						<span class="text-[11px] font-medium uppercase tracking-wider text-white/70">{{ __('Done') }}</span>
					</div>
				</div>
			</section>

			<!-- Journey: one list, one current step -->
			<section class="il-card mt-6 p-2 sm:p-3">
				<div class="flex items-baseline justify-between gap-3 px-3 pb-2 pt-2">
					<h2 class="text-lg font-semibold text-[color:var(--il-ink)]">{{ __('Your journey') }}</h2>
					<span class="text-sm text-[color:var(--il-muted)]">{{ doneCount }} {{ __('of') }} {{ steps.length }} {{ __('done') }}</span>
				</div>
				<ol>
					<li v-for="step in steps" :key="step.key">
						<button
							type="button"
							class="jr-row"
							:class="`is-${step.kind}`"
							:disabled="!step.clickable"
							@click="step.open()"
						>
							<span class="jr-icon">
								<Check v-if="step.kind === 'done'" class="h-5 w-5" />
								<Lock v-else-if="step.kind === 'locked'" class="h-4 w-4" />
								<component :is="step.icon" v-else-if="step.icon" class="h-5 w-5" />
								<span v-else class="text-base font-semibold">{{ step.number }}</span>
							</span>
							<span class="min-w-0 flex-1 text-left">
								<span class="block truncate text-[15px] font-medium text-[color:var(--il-ink)]">{{ step.title }}</span>
								<span class="block truncate text-xs text-[color:var(--il-muted)]">{{ step.detail }}</span>
								<span v-if="step.kind === 'current' && step.progress != null" class="jr-bar">
									<span :style="{ width: `${Math.max(step.progress, 3)}%` }" />
								</span>
							</span>
							<span v-if="step.status" class="jr-pill">{{ step.status }}</span>
							<ChevronRight v-if="step.clickable" class="h-4 w-4 shrink-0 text-[color:var(--il-neutral-60)]" />
						</button>
					</li>
				</ol>
			</section>

			<!-- OJT locked notice (IL gold "Stuck on a problem?" card) -->
			<section
				v-if="home.data.ojt?.enabled && home.data.ojt?.locked && !home.data.is_staff"
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
import { createResource, Tooltip } from 'frappe-ui'
import {
	Bell,
	Check,
	ChevronRight,
	ClipboardList,
	Home,
	Lock,
	Mic,
	PhoneCall,
	PlayCircle,
	Search,
	Star,
} from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'

const user = inject('$user')
const { user: sessionUser } = sessionStore()
const router = useRouter()

const unreadCount = createResource({
	cache: 'Unread Notifications Count',
	url: 'frappe.client.get_count',
	makeParams() {
		return {
			doctype: 'Notification Log',
			filters: {
				for_user: sessionUser,
				read: 0,
			},
		}
	},
	auto: !!sessionUser,
})

function goSearch() {
	router.push({ name: 'Search' })
}

function goNotifications() {
	router.push({ name: 'Notifications' })
}

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
	// Past midnight is not morning: anyone here at 1am gets a plain hello.
	if (hour < 5) return __('Hello')
	if (hour < 12) return __('Good morning')
	if (hour < 17) return __('Good afternoon')
	return __('Good evening')
})

const crts = computed(() => home.data?.crts || [])
// Hello ILians joining form: step zero for learners, before Day 1.
const helloPending = computed(() => Boolean(home.data?.hello_ilians?.required && !home.data?.hello_ilians?.submitted))
const openHello = () => router.push({ name: 'HelloILians' })
const staff = computed(() => Boolean(home.data?.is_staff))
const crtsDone = computed(() => crts.value.length > 0 && crts.value.every((c) => c.state === 'completed'))
// The one step to work on now: the first CRT that is not finished.
const currentIndex = computed(() => crts.value.findIndex((c) => c.state !== 'completed'))
const evalStatus = computed(() => home.data?.evaluation?.status)
const evalDone = computed(() => crtsDone.value && evalStatus.value === 'Completed')
// OJT ("Go live") is switched off until it's built end to end (site_config sales_ojt_enabled).
const ojtEnabled = computed(() => Boolean(home.data?.ojt?.enabled))
const ojtOpen = computed(() => ojtEnabled.value && evalDone.value && Boolean(home.data?.ojt?.eligible))

const sessions = (c) => (c.lessons_total ? `${c.lessons_done} ${__('of')} ${c.lessons_total} ${__('sessions')}` : __('Content coming soon'))

// Day names come from the course's chapters (admins rename them in the course outline).
const crtTitle = (c) => `${__('Day')} ${c.day || c.crt_number} · ${c.title}`

const steps = computed(() => {
	const hello = home.data?.hello_ilians
	const helloStep = hello?.required
		? [
				{
					key: 'hello-ilians',
					icon: ClipboardList,
					title: __('Hello ILians'),
					detail: hello.submitted ? __('Joining form submitted') : __('Tell us about yourself · 2 minutes'),
					kind: hello.submitted ? 'done' : 'current',
					status: hello.submitted ? __('Done') : __('Start here'),
					clickable: true,
					open: openHello,
				},
		  ]
		: []
	const list = crts.value.map((c, i) => {
		let kind = 'locked'
		let status = __('Locked')
		if (c.state === 'completed') [kind, status] = ['done', __('Done')]
		else if (helloPending.value) [kind, status] = ['locked', i === 0 ? __('After the form') : __('Locked')]
		else if (i === currentIndex.value)
			[kind, status] = ['current', c.state === 'viva_pending' ? __('Voice viva') : __('Today')]
		else if (staff.value) [kind, status] = ['next', i === currentIndex.value + 1 ? __('Up next') : '']
		return {
			key: `crt-${c.crt_number}`,
			number: c.crt_number,
			title: crtTitle(c),
			detail: c.state === 'viva_pending' ? vivaDetail(c) : sessions(c),
			progress: c.progress,
			kind,
			status,
			clickable: kind !== 'locked' && c.state !== 'empty',
			open: () => openCrt(c),
		}
	})
	const evalKind = evalDone.value ? 'done' : crtsDone.value ? 'current' : staff.value ? 'next' : 'locked'
	list.push({
		key: 'evaluation',
		icon: Star,
		title: __('Final review'),
		detail: evalDone.value ? __('Your training rating is ready') : __('Your trainer rates your 5 days'),
		kind: evalKind,
		status: { done: __('Done'), current: __('Ready'), next: __('After Day 5'), locked: __('Locked') }[evalKind],
		clickable: evalKind !== 'locked',
		open: goEval,
	})
	if (ojtEnabled.value) {
		const ojtKind = ojtOpen.value ? 'current' : staff.value ? 'next' : 'locked'
		list.push({
			key: 'ojt',
			icon: PhoneCall,
			title: __('Go live · OJT'),
			detail: ojtOpen.value ? __('On-the-job calls with real leads') : __('Real calls with real leads, with your trainer'),
			kind: ojtKind,
			status: { current: __('Open'), next: __('After review'), locked: __('Locked') }[ojtKind],
			clickable: ojtKind !== 'locked',
			open: () => router.push({ name: 'SalesOJT' }),
		})
	}
	return [...helloStep, ...list]
})

const doneCount = computed(() => steps.value.filter((s) => s.kind === 'done').length)

const currentCrt = computed(() => crts.value[currentIndex.value])

const bannerTitle = computed(() => {
	if (helloPending.value) return __('First, say Hello ILians 👋')
	if (ojtOpen.value) return __("You're ready for OJT")
	if (crtsDone.value) return __('Classroom training complete')
	if (currentCrt.value) return `${__('Up next')}: ${crtTitle(currentCrt.value)}`
	return __('Your Sales onboarding')
})

const vivaDetail = (c) => {
	const v = c.viva || {}
	if (v.blocked) return __('All attempts used · your Training Manager can unlock more')
	return `${__('Sessions done · voice viva to finish the day')} · ${v.attempts_left ?? 3} ${__('attempts left')}`
}

const bannerDetail = computed(() => {
	if (helloPending.value) return __('Fill your 2-minute joining form. Day 1 opens as soon as you submit.')
	const c = currentCrt.value
	if (c?.state === 'viva_pending') return vivaDetail(c)
	if (c?.current_lesson?.title) return `${c.current_lesson.title} · ${sessions(c)}`
	if (crtsDone.value && !evalDone.value) return __('Your final review is next.')
	return __('5 days of classroom training, a final review, then live calls.')
})

const primaryAction = computed(() => {
	if (helloPending.value) return { label: __('Fill the form'), icon: ClipboardList, run: openHello }
	if (currentCrt.value?.state === 'viva_pending')
		return { label: __('Take the voice viva'), icon: Mic, run: () => openViva(currentCrt.value) }
	if (currentCrt.value && currentCrt.value.state !== 'empty')
		return { label: currentCrt.value.lessons_done ? __('Continue learning') : __('Start learning'), icon: PlayCircle, run: continueLearning }
	if (ojtOpen.value) return { label: __('Enter OJT'), icon: PhoneCall, run: () => router.push({ name: 'SalesOJT' }) }
	if (crtsDone.value) return { label: __('View final review'), icon: Star, run: goEval }
	return null
})

const course = computed(() => home.data?.course || 'sales-crt')
const openViva = (crt) => router.push({ name: 'DayViva', params: { courseName: course.value, day: crt.slug || String(crt.crt_number) } })

const openCrt = (crt) => {
	if (!home.data?.is_staff && (crt.state === 'locked' || crt.state === 'empty')) return
	if (crt.state === 'viva_pending') return openViva(crt)
	router.push({ name: 'DayDetail', params: { courseName: course.value, day: crt.slug || String(crt.crt_number) } })
}

const goEval = () => router.push({ name: 'SalesEvaluation' })

const continueLearning = () => {
	const target = currentCrt.value || current.value
	const lesson = target?.current_lesson
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
	openCrt(target)
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

.jr-row {
	display: flex;
	width: 100%;
	align-items: center;
	gap: 0.85rem;
	border: 1px solid transparent;
	border-radius: 16px;
	padding: 0.7rem 0.75rem;
	text-align: left;
	transition: background 0.15s ease;
}

.jr-row:not(:disabled):hover {
	background: #f7fbff;
}

.jr-row:disabled {
	cursor: default;
}

.jr-icon {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 2.5rem;
	height: 2.5rem;
	border-radius: 999px;
	background: var(--il-neutral-95);
	color: var(--il-neutral-60);
}

.jr-pill {
	flex-shrink: 0;
	border-radius: 999px;
	padding: 0.2rem 0.65rem;
	background: var(--il-neutral-95);
	color: var(--il-muted);
	font-size: 0.75rem;
	font-weight: 600;
	white-space: nowrap;
}

.jr-bar {
	display: block;
	height: 0.3rem;
	margin-top: 0.45rem;
	overflow: hidden;
	border-radius: 999px;
	background: var(--il-primary-95);
}

.jr-bar span {
	display: block;
	height: 100%;
	border-radius: 999px;
	background: var(--il-primary-50);
}

.jr-row.is-done .jr-icon {
	background: var(--il-success-95);
	color: var(--il-success-50);
}

.jr-row.is-done .jr-pill {
	background: var(--il-success-95);
	color: var(--il-success-50);
}

.jr-row.is-current {
	border-color: #cfe5ff;
	background: #f4f9ff;
}

.jr-row.is-current .jr-icon {
	background: var(--il-primary-50);
	color: #fff;
	box-shadow: 0 4px 12px rgba(2, 123, 255, 0.35);
}

.jr-row.is-current .jr-pill {
	background: var(--il-primary-50);
	color: #fff;
}

.jr-row.is-next .jr-icon {
	background: var(--il-primary-95);
	color: var(--il-primary-40);
}

.jr-row.is-locked {
	opacity: 0.7;
}

li + li .jr-row {
	margin-top: 0.15rem;
}

.il-header-icon-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 2.5rem;
	height: 2.5rem;
	border-radius: 999px;
	background: #ffffff;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.16);
	color: var(--il-primary-40);
	transition: background-color 0.15s ease;
}

.il-header-icon-btn:hover {
	background: var(--il-primary-95);
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
