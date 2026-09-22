<template>
	<div class="genius-dashboard min-h-full w-full px-4 pb-12 pt-4 sm:px-6 lg:px-8">
		<!-- SECTION 1: Hero -->
		<section
			class="genius-hero-surface genius-fade-up relative mb-6 overflow-hidden rounded-[20px] px-6 py-8 text-white sm:px-8 sm:py-10"
		>
			<div class="relative z-10 grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-center">
				<div>
					<p class="mb-2 text-sm font-medium text-white/80">
						{{ greeting }}
					</p>
					<h1
						class="text-3xl font-semibold tracking-tight sm:text-4xl"
						style="color: #fff !important"
					>
						{{ __('Welcome') }}{{ user.data?.full_name ? `, ${firstName}` : '' }}
					</h1>
					<p class="mt-3 max-w-xl text-sm leading-6 text-white/85 sm:text-base">
						{{
							continueCourse
								? __('Pick up your CRT day and keep going.')
								: __('Open the Sales CRT course — 5 days of classroom readiness training.')
						}}
					</p>
					<div class="mt-6 flex flex-wrap items-center gap-3">
						<router-link
							v-if="continueCourse"
							:to="continueRoute(continueCourse)"
							class="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold"
							style="color: #0075ff"
						>
							{{ __('Continue Learning') }}
						</router-link>
						<router-link
							v-else
							:to="{ name: 'GeniusCourseDetail', params: { courseName: 'sales-crt' } }"
							class="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold"
							style="color: #0075ff"
						>
							{{ __('Open CRT course') }}
						</router-link>
						<div class="text-sm text-white/80">
							{{ enrolledCount }} {{ __('enrolled') }} ·
							{{ Math.round(overallProgress) }}% {{ __('avg progress') }}
						</div>
					</div>
				</div>
				<div
					class="rounded-[20px] p-5"
					style="background: #0066ee"
				>
					<div class="mb-2 flex items-center justify-between text-sm text-white/80">
						<span>{{ __('Learning progress') }}</span>
						<span class="font-semibold text-white">
							{{ Math.round(overallProgress) }}%
						</span>
					</div>
					<div class="h-3 overflow-hidden rounded-full bg-white/20">
						<div
							class="h-3 rounded-full bg-white transition-all duration-500"
							:style="{ width: `${Math.min(100, overallProgress)}%` }"
						/>
					</div>
					<div class="mt-4 grid grid-cols-2 gap-3 text-sm">
						<div>
							<div class="text-white/70">{{ __('Streak') }}</div>
							<div class="text-lg font-semibold">
								{{ streakInfo.data?.current_streak ?? 0 }} {{ __('days') }}
							</div>
						</div>
						<div>
							<div class="text-white/70">{{ __('Active time') }}</div>
							<div class="text-lg font-semibold">
								{{ totalActiveDisplay }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- SECTION 2: Stats -->
		<section class="genius-fade-up-delay mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
			<div
				v-for="stat in stats"
				:key="stat.label"
				class="genius-card genius-card-hover p-5"
			>
				<div
					class="mb-3 inline-flex size-10 items-center justify-center rounded-xl"
					:style="{ background: stat.bg, color: stat.color }"
				>
					<component :is="stat.icon" class="size-5" />
				</div>
				<div class="text-2xl font-semibold tabular-nums text-[color:var(--genius-ink)]">
					{{ stat.value }}
				</div>
				<div class="mt-1 text-sm text-[color:var(--genius-muted)]">
					{{ stat.label }}
				</div>
			</div>
		</section>

		<!-- SECTION 3: Continue Learning -->
		<section class="mb-8">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-xl font-semibold" style="color: var(--genius-navy) !important">
					{{ __('Continue Learning') }}
				</h2>
				<router-link
					:to="{ name: 'Courses', query: { tab: 'enrolled' } }"
					class="text-sm font-medium text-[color:var(--genius-primary)]"
				>
					{{ __('View all') }}
				</router-link>
			</div>
			<div v-if="continueList.length" class="space-y-4">
				<div
					v-for="course in continueList"
					:key="course.name"
					class="genius-card genius-card-hover flex flex-col gap-4 p-4 sm:flex-row sm:items-center"
				>
					<div
						class="h-28 w-full shrink-0 overflow-hidden rounded-2xl sm:h-24 sm:w-40"
						:style="courseThumbStyle(course)"
					>
						<div
							v-if="!course.image"
							class="flex h-full items-center justify-center px-3 text-center text-sm font-semibold text-white"
						>
							{{ course.title }}
						</div>
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-2">
							<h3 class="truncate text-lg font-semibold text-[color:var(--genius-ink)]">
								{{ course.title }}
							</h3>
						</div>
						<p class="mt-1 line-clamp-2 text-sm text-[color:var(--genius-muted)]">
							{{ course.short_introduction }}
						</p>
						<div class="mt-3">
							<div class="mb-1 flex justify-between text-xs text-[color:var(--genius-muted)]">
								<span>{{ __('Progress') }}</span>
								<span>{{ Math.round(course.membership?.progress || 0) }}%</span>
							</div>
							<div
								class="h-2 overflow-hidden rounded-full"
								style="background: var(--genius-border)"
							>
								<div
									class="progress-bar-fill h-2 rounded-full"
									:style="{
										width: `${Math.min(100, course.membership?.progress || 0)}%`,
									}"
								/>
							</div>
						</div>
					</div>
					<router-link
						:to="continueRoute(course)"
						class="inline-flex shrink-0 items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold text-white"
						style="background: var(--genius-primary)"
					>
						{{ __('Resume') }}
					</router-link>
				</div>
			</div>
			<div v-else class="genius-card p-6 text-sm text-[color:var(--genius-muted)]">
				{{ __('No enrolled courses yet.') }}
				<router-link
					:to="{ name: 'Courses' }"
					class="ms-1 font-medium text-[color:var(--genius-primary)] underline"
				>
					{{ __('Browse catalog') }}
				</router-link>
			</div>
		</section>

		<div class="mb-8 grid gap-6 xl:grid-cols-2">
			<!-- Recent Activity -->
			<section class="genius-card p-5">
				<h2 class="mb-4 text-lg font-semibold" style="color: var(--genius-navy) !important">
					{{ __('Recent Activity') }}
				</h2>
				<ol v-if="activityItems.length" class="space-y-4">
					<li
						v-for="(item, idx) in activityItems"
						:key="idx"
						class="relative flex gap-3 ps-4"
					>
						<span
							class="absolute start-0 top-1.5 size-2.5 rounded-full"
							:style="{ background: item.color }"
						/>
						<div>
							<div class="text-sm font-medium text-[color:var(--genius-ink)]">
								{{ item.title }}
							</div>
							<div class="text-xs text-[color:var(--genius-muted)]">
								{{ item.meta }}
							</div>
						</div>
					</li>
				</ol>
				<div v-else class="text-sm text-[color:var(--genius-muted)]">
					{{ __('Your recent learning activity will show up here.') }}
				</div>
			</section>

			<!-- Achievements -->
			<section class="genius-card p-5">
				<h2 class="mb-4 text-lg font-semibold" style="color: var(--genius-navy) !important">
					{{ __('Achievements & Certificates') }}
				</h2>
				<div v-if="certificates.data?.length" class="space-y-2">
					<button
						v-for="cert in certificates.data.slice(0, 5)"
						:key="cert.name"
						type="button"
						class="genius-card-hover flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left"
						style="border-color: var(--genius-border)"
						@click="openCertificate(cert)"
					>
						<div>
							<div class="text-sm font-medium text-[color:var(--genius-ink)]">
								{{ cert.course_title || cert.batch_title || cert.name }}
							</div>
							<div class="text-xs text-[color:var(--genius-muted)]">
								{{ dayjs(cert.issue_date).format('DD MMM YYYY') }}
							</div>
						</div>
						<Award class="size-4 text-[color:var(--genius-primary)]" />
					</button>
				</div>
				<div v-else class="space-y-3">
					<div
						class="rounded-xl px-3 py-3 text-sm"
						style="background: var(--genius-blue-light); color: var(--genius-primary)"
					>
						{{ __('Complete a course to unlock your first certificate.') }}
					</div>
					<div class="text-sm text-[color:var(--genius-muted)]">
						{{ __('Streak') }}:
						<span class="font-semibold text-[color:var(--genius-ink)]">
							{{ streakInfo.data?.current_streak ?? 0 }}
						</span>
					</div>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, markRaw } from 'vue'
import { createListResource, createResource, usePageMeta } from 'frappe-ui'
import { Award, BookOpen, Clock3, Flame, GraduationCap } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { openCertificatePreview } from '@/utils/certificate'

const user = inject('$user')
const dayjs = inject('$dayjs')
const { brand } = sessionStore()

const myCourses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	filters: { enrolled: 1 },
	auto: !!user.data,
	cache: ['dashboard-enrolled', user.data?.name],
})

const summary = createResource({
	url: 'lms.tracking.get_my_summary',
	auto: !!user.data,
	cache: ['dashboard-summary', user.data?.name],
})

const streakInfo = createResource({
	url: 'lms.lms.api.get_streak_info',
	auto: !!user.data,
	cache: ['dashboard-streak', user.data?.name],
})

const certificates = createListResource({
	doctype: 'LMS Certificate',
	fields: ['name', 'course_title', 'batch_title', 'issue_date', 'template'],
	filters: { member: user.data?.name },
	auto: !!user.data?.name,
	cache: ['dashboard-certs', user.data?.name],
})

const firstName = computed(() => {
	const full = user.data?.full_name || ''
	return full.split(' ')[0] || full
})

const greeting = computed(() => {
	const hour = dayjs().hour()
	// Past midnight is not morning: anyone here at 1am gets a plain hello.
	if (hour < 5) return __('Hello')
	if (hour < 12) return __('Good morning')
	if (hour < 17) return __('Good afternoon')
	return __('Good evening')
})

const enrolledCount = computed(() => (myCourses.data || []).length)

const overallProgress = computed(() => {
	const list = myCourses.data || []
	if (!list.length) return 0
	const total = list.reduce((sum, c) => sum + Number(c.membership?.progress || 0), 0)
	return total / list.length
})

const totalActiveDisplay = computed(() => {
	const cards = summary.data?.summary_cards || []
	const total = cards.find((c) => c.key === 'total')
	return total?.display || '0m'
})

const hoursLearned = computed(() => {
	const cards = summary.data?.summary_cards || []
	const total = cards.find((c) => c.key === 'total')
	const minutes = Number(total?.minutes || 0)
	if (!minutes) return '0h'
	const hours = minutes / 60
	return hours >= 10 ? `${Math.round(hours)}h` : `${hours.toFixed(1)}h`
})

const stats = computed(() => [
	{
		label: __('Courses Enrolled'),
		value: enrolledCount.value,
		icon: markRaw(BookOpen),
		bg: '#eff6ff',
		color: '#1d4ed8',
	},
	{
		label: __('Hours Learned'),
		value: hoursLearned.value,
		icon: markRaw(Clock3),
		bg: '#ecfeff',
		color: '#06b6d4',
	},
	{
		label: __('Certificates Earned'),
		value: certificates.data?.length || 0,
		icon: markRaw(GraduationCap),
		bg: '#ecfdf5',
		color: '#10b981',
	},
	{
		label: __('Learning Streak'),
		value: streakInfo.data?.current_streak ?? 0,
		icon: markRaw(Flame),
		bg: '#fff7ed',
		color: '#ea580c',
	},
])

const continueList = computed(() => {
	const list = myCourses.data || []
	return list
		.filter((c) => (c.membership?.progress || 0) < 100)
		.slice(0, 3)
		.concat(list.filter((c) => (c.membership?.progress || 0) >= 100).slice(0, 1))
		.slice(0, 3)
})

const activityItems = computed(() => {
	const items = []
	for (const course of (myCourses.data || []).slice(0, 4)) {
		const progress = Math.round(course.membership?.progress || 0)
		items.push({
			title: course.title,
			meta:
				progress > 0
					? __('{0}% complete').format(progress)
					: __('Enrolled — ready to start'),
			color: course.has_scorm ? '#06b6d4' : '#1d4ed8',
		})
	}
	for (const day of (summary.data?.heatmap || []).slice(-3).reverse()) {
		if (!day.minutes) continue
		items.push({
			title: __('Active learning session'),
			meta: `${day.date} · ${day.minutes}m`,
			color: '#10b981',
		})
	}
	return items.slice(0, 6)
})

const courseThumbStyle = (course) => {
	if (course.image) {
		return {
			backgroundImage: `url('${encodeURI(course.image)}')`,
			backgroundSize: 'cover',
			backgroundPosition: 'center',
		}
	}
	return {
		background: 'var(--genius-gradient)',
	}
}

const continueRoute = (course) => {
	if (course.has_scorm) {
		return {
			name: 'GeniusScormPlayer',
			params: { courseName: course.name },
		}
	}
	const current = course.membership?.current_lesson || course.current_lesson
	const parts = String(current || '1-1').split('-')
	return {
		name: 'Lesson',
		params: {
			courseName: course.name,
			chapterNumber: parts[0] || 1,
			lessonNumber: parts[1] || 1,
		},
	}
}

const openCertificate = (certificate) => {
	openCertificatePreview(certificate)
}

usePageMeta(() => ({
	title: __('Dashboard'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.genius-dashboard {
	background: var(--genius-gradient-soft);
}
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>
