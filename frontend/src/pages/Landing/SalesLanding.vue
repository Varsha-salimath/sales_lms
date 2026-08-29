<template>
	<div class="min-h-screen" style="background: #0075ff">
		<header class="relative z-20 flex items-center justify-between px-5 py-4 sm:px-10">
			<img
				:src="logoSrc"
				alt="Infinity Learn by Sri Chaitanya"
				class="h-11 w-auto object-contain sm:h-12"
			/>
			<nav class="flex items-center gap-4 sm:gap-6">
				<a
					href="tel:7996668865"
					class="hidden items-center gap-2 text-sm font-medium text-white sm:inline-flex"
				>
					<span
						class="inline-flex size-8 items-center justify-center rounded-full"
						style="background: #ffd000; color: #12263f"
					>
						☎
					</span>
					<span class="lowercase">need help? talk to experts</span>
				</a>
				<router-link
					:to="{ name: 'Courses' }"
					class="text-sm font-medium lowercase text-white"
				>
					{{ __('courses') }}
				</router-link>
				<a
					v-if="!user.data"
					href="/login"
					class="rounded-full bg-white px-5 py-2 text-sm font-semibold lowercase"
					style="color: #0075ff"
				>
					{{ __('sign in') }}
				</a>
				<router-link
					v-else
					:to="{ name: 'StudentDashboard' }"
					class="rounded-full bg-white px-5 py-2 text-sm font-semibold lowercase"
					style="color: #0075ff"
				>
					{{ __('dashboard') }}
				</router-link>
			</nav>
		</header>

		<section class="px-5 pb-16 pt-6 sm:px-10 sm:pb-20 sm:pt-8">
			<div class="mx-auto max-w-6xl">
				<div
					class="mb-5 inline-flex items-center rounded-full px-4 py-1.5 text-sm font-semibold"
					style="background: #ffd000; color: #12263f"
				>
					{{ __('Interactive live CRT') }}
				</div>
				<h1
					class="max-w-3xl text-4xl font-extrabold lowercase leading-[1.12] tracking-tight text-white sm:text-5xl md:text-6xl"
					style="color: #fff !important"
				>
					{{ __('power up your sales crt journey with infinity learn') }}
				</h1>
				<p class="mt-5 max-w-xl text-base text-white sm:text-lg">
					{{
						__(
							'Classroom Readiness Training for Academic Counsellors — products, call flow, demo conduction, LSQ and live calling across 5 days.'
						)
					}}
				</p>
				<div class="mt-8 flex flex-wrap gap-3">
					<router-link
						:to="crtRoute"
						class="rounded-full bg-white px-6 py-3 text-sm font-bold lowercase"
						style="color: #0075ff"
					>
						{{ __('open crt course') }}
					</router-link>
					<a
						v-if="!user.data"
						href="/login"
						class="rounded-full border-2 border-white px-6 py-3 text-sm font-bold lowercase text-white"
					>
						{{ __('sign in') }}
					</a>
					<router-link
						v-else
						:to="{ name: 'StudentDashboard' }"
						class="rounded-full border-2 border-white px-6 py-3 text-sm font-bold lowercase text-white"
					>
						{{ __('go to dashboard') }}
					</router-link>
				</div>

				<div class="mt-14 grid grid-cols-2 gap-6 sm:grid-cols-4">
					<div v-for="stat in heroStats" :key="stat.label">
						<div class="text-3xl font-extrabold text-white sm:text-4xl">
							{{ stat.value }}
						</div>
						<div class="mt-1 text-sm font-medium lowercase text-white">
							{{ stat.label }}
						</div>
					</div>
				</div>
			</div>
		</section>

		<section class="bg-white px-5 py-14 sm:px-10">
			<div class="mx-auto max-w-6xl">
				<div class="mb-8 flex flex-wrap items-end justify-between gap-4">
					<div>
						<h2
							class="text-2xl font-extrabold lowercase"
							style="color: #12263f !important"
						>
							{{ __('featured course') }}
						</h2>
						<p class="mt-1 text-sm" style="color: #5b6b82">
							{{ __('CRT is organised as 5 days — open a day, then the session.') }}
						</p>
					</div>
					<router-link
						v-if="canImport"
						:to="{ name: 'SalesImport' }"
						class="rounded-full px-4 py-2 text-sm font-semibold text-white"
						style="background: #0075ff"
					>
						{{ __('import schedule') }}
					</router-link>
				</div>

				<div
					v-if="featuredCourses.length"
					class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
				>
					<router-link
						v-for="course in featuredCourses"
						:key="course.name"
						:to="{
							name: 'GeniusCourseDetail',
							params: { courseName: course.name },
						}"
						class="genius-card-hover block overflow-hidden rounded-[20px] border bg-white"
						style="border-color: #d7e4f7"
					>
						<CourseCard :course="course" />
					</router-link>
				</div>
				<div
					v-else
					class="rounded-[20px] border p-8 text-sm"
					style="border-color: #d7e4f7; color: #5b6b82"
				>
					{{
						__(
							'The CRT course will appear here once the schedule Excel is imported. Course content is not bundled in the Docker image.'
						)
					}}
				</div>
			</div>
		</section>

		<section class="px-5 py-14 sm:px-10" style="background: #f4f8ff">
			<div class="mx-auto max-w-6xl">
				<h2
					class="text-2xl font-extrabold lowercase"
					style="color: #12263f !important"
				>
					{{ __('why this crt') }}
				</h2>
				<div class="mt-8 grid gap-6 sm:grid-cols-3">
					<div
						v-for="item in highlights"
						:key="item.title"
						class="rounded-[20px] bg-white p-5"
						style="border: 1px solid #d7e4f7"
					>
						<div class="mb-2 text-sm font-bold" style="color: #12263f">
							{{ item.title }}
						</div>
						<p class="text-sm" style="color: #5b6b82">{{ item.body }}</p>
					</div>
				</div>
			</div>
		</section>

		<footer class="bg-white px-5 py-8 text-center text-xs sm:px-10" style="color: #5b6b82">
			{{ __('© Infinity Learn by Sri Chaitanya · Sales CRT') }}
		</footer>
	</div>
</template>
<script setup>
import { computed, inject } from 'vue'
import { createListResource, usePageMeta } from 'frappe-ui'
import CourseCard from '@/components/CourseCard.vue'
import logoSrc from '@/assets/il-logo.png'
import { sessionStore } from '@/stores/session'

const user = inject('$user')
const { brand } = sessionStore()

const crtRoute = {
	name: 'GeniusCourseDetail',
	params: { courseName: 'sales-crt' },
}

const courses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	filters: { published: 1, upcoming: 0, live: 1 },
	auto: true,
	cache: ['landing-courses'],
})

const featuredCourses = computed(() => {
	const list = (courses.data || []).filter((c) => {
		const title = (c.title || '').toLowerCase()
		return !title.includes('frappe learning')
	})
	const crt = list.filter(
		(c) => c.name === 'sales-crt' || (c.title || '').toLowerCase().includes('crt')
	)
	return (crt.length ? crt : list).slice(0, 6)
})

const canImport = computed(
	() =>
		!!(
			user.data?.is_moderator ||
			user.data?.is_instructor ||
			user.data?.is_system_manager
		)
)

const heroStats = [
	{ label: 'crt days', value: '5' },
	{ label: 'learners', value: '7M+' },
	{ label: 'enrolled', value: '50K+' },
	{ label: 'average rating', value: '4.9' },
]

const highlights = [
	{
		title: __('5-day classroom path'),
		body: __('Each day is a course module. Sessions inside a day open as lessons from the dashboard.'),
	},
	{
		title: __('Live calling & demos'),
		body: __('Products, call flow, demo conduction and LSQ, taken from the official CRT Excel schedule.'),
	},
	{
		title: __('Progress that sticks'),
		body: __('Sign in, open dashboard, continue CRT, and pick up the next session where you left off.'),
	},
]

usePageMeta(() => ({
	title: 'Infinity Learn Sales CRT',
	icon: brand.favicon,
}))
</script>
