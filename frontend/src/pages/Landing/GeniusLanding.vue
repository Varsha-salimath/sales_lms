<template>
	<div class="min-h-screen" style="background: var(--genius-bg)">
		<header
			class="relative z-10 flex items-center justify-between px-5 py-4 sm:px-8"
		>
			<div class="flex items-center gap-3">
				<img :src="logoSrc" alt="Genius" class="h-9 w-auto object-contain" />
				<span
					class="text-lg font-semibold tracking-tight"
					style="color: var(--genius-ink)"
				>
					Genius LMS
				</span>
			</div>
			<nav class="flex items-center gap-3 sm:gap-5">
				<router-link
					:to="{ name: 'Courses' }"
					class="text-sm font-medium text-[color:var(--genius-navy)] hover:text-[color:var(--genius-blue)]"
				>
					{{ __('Courses') }}
				</router-link>
				<a
					v-if="!user.data"
					href="/login"
					class="rounded-md px-3 py-1.5 text-sm font-semibold text-white"
					style="background: var(--genius-blue)"
				>
					{{ __('Sign in') }}
				</a>
				<router-link
					v-else
					:to="{ name: 'StudentDashboard' }"
					class="rounded-md px-3 py-1.5 text-sm font-semibold text-white"
					style="background: var(--genius-blue)"
				>
					{{ __('Dashboard') }}
				</router-link>
			</nav>
		</header>

		<section class="genius-hero-surface px-5 py-16 text-white sm:px-8 sm:py-24">
			<div class="relative z-10 mx-auto max-w-5xl">
				<img
					:src="logoSrc"
					alt="Genius"
					class="genius-fade-up mb-6 h-14 w-auto object-contain sm:h-16"
				/>
				<h1
					class="genius-fade-up text-4xl font-semibold tracking-tight text-white sm:text-5xl md:text-6xl"
					style="color: #fff !important"
				>
					{{ __('Learn with Genius') }}
				</h1>
				<p
					class="genius-fade-up-delay mt-4 max-w-xl text-base text-white/85 sm:text-lg"
				>
					{{
						__(
							'Professional learning experiences for educators — SCORM courses, progress tracking, and certificates in one place.'
						)
					}}
				</p>
				<div class="genius-fade-up-delay mt-8 flex flex-wrap gap-3">
					<router-link
						:to="{ name: 'Courses' }"
						class="rounded-md px-5 py-2.5 text-sm font-semibold"
						style="background: #fff; color: var(--genius-navy)"
					>
						{{ __('Explore courses') }}
					</router-link>
					<a
						v-if="!user.data"
						href="/login"
						class="rounded-md border border-white/40 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
					>
						{{ __('Sign in') }}
					</a>
					<router-link
						v-else
						:to="{ name: 'StudentDashboard' }"
						class="rounded-md border border-white/40 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
					>
						{{ __('Go to dashboard') }}
					</router-link>
				</div>
			</div>
		</section>

		<section class="mx-auto max-w-6xl px-5 py-14 sm:px-8">
			<div class="mb-8">
				<h2 class="text-2xl font-semibold" style="color: var(--genius-navy) !important">
					{{ __('Featured courses') }}
				</h2>
				<p class="mt-1 text-sm text-[color:var(--genius-muted)]">
					{{ __('Start with curated learning paths for educators.') }}
				</p>
			</div>
			<div
				v-if="featuredCourses.length"
				class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
			>
				<router-link
					v-for="course in featuredCourses"
					:key="course.name"
					:to="{ name: 'GeniusCourseDetail', params: { courseName: course.name } }"
					class="genius-card-hover block overflow-hidden rounded-lg border bg-white"
					style="border-color: var(--genius-border)"
				>
					<CourseCard :course="course" />
				</router-link>
			</div>
			<div v-else class="text-sm text-[color:var(--genius-muted)]">
				{{ __('Courses will appear here once published.') }}
			</div>
		</section>

		<section
			class="border-y px-5 py-14 sm:px-8"
			style="
				background: var(--genius-blue-light);
				border-color: var(--genius-border);
			"
		>
			<div class="mx-auto max-w-6xl">
				<h2 class="text-2xl font-semibold" style="color: var(--genius-navy) !important">
					{{ __('Why Genius') }}
				</h2>
				<p class="mt-2 max-w-2xl text-sm text-[color:var(--genius-muted)]">
					{{
						__(
							'Built for InfinityLearn educators — immersive SCORM playback, clear progress, and a calm learning workspace.'
						)
					}}
				</p>
				<div class="mt-8 grid gap-6 sm:grid-cols-3">
					<div
						v-for="item in highlights"
						:key="item.title"
						class="rounded-lg bg-white p-5"
						style="border: 1px solid var(--genius-border)"
					>
						<div
							class="mb-2 text-sm font-semibold"
							style="color: var(--genius-navy)"
						>
							{{ item.title }}
						</div>
						<p class="text-sm text-[color:var(--genius-muted)]">{{ item.body }}</p>
					</div>
				</div>
			</div>
		</section>

		<footer
			class="px-5 py-8 text-center text-xs text-[color:var(--genius-muted)] sm:px-8"
		>
			{{ __('© InfinityLearn Genius LMS') }}
		</footer>
	</div>
</template>
<script setup>
import { computed, inject } from 'vue'
import { createListResource, usePageMeta } from 'frappe-ui'
import CourseCard from '@/components/CourseCard.vue'
import logoSrc from '@/assets/genius-logo.svg'
import { sessionStore } from '@/stores/session'

const user = inject('$user')
const { brand } = sessionStore()

const courses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	filters: { published: 1, upcoming: 0, live: 1 },
	auto: true,
	cache: ['landing-courses'],
})

const featuredCourses = computed(() =>
	(courses.data || [])
		.filter((c) => {
			const title = (c.title || '').toLowerCase()
			return !title.includes('frappe learning')
		})
		.slice(0, 6)
)

const highlights = [
	{
		title: __('Interactive courses'),
		body: __('Play packaged courses with progress, score, and resume.'),
	},
	{
		title: __('Clear progress'),
		body: __('See where you left off and what to finish next.'),
	},
	{
		title: __('Educator focused'),
		body: __('A focused student experience designed around teaching excellence.'),
	},
]

usePageMeta(() => ({
	title: 'Genius',
	icon: brand.favicon,
}))
</script>
