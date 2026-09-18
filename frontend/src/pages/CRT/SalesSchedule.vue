<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<header class="sticky top-0 z-20 border-b border-violet-100 bg-white/90 backdrop-blur">
			<div class="mx-auto flex max-w-6xl items-center justify-between px-5 py-3 sm:px-8">
				<router-link :to="{ name: 'Home' }" class="flex items-center gap-3">
					<img :src="logoSrc" alt="Sales LMS" class="h-9 w-auto" />
				</router-link>
				<div class="flex items-center gap-2">
					<router-link
						v-if="schedule.data?.course"
						:to="{ name: 'CourseDetail', params: { courseName: schedule.data.course } }"
						class="hidden rounded-full px-3 py-1.5 text-sm font-medium text-[color:var(--il-violet)] sm:inline"
					>
						{{ __('Course outline') }}
					</router-link>
					<router-link
						v-if="canImport"
						:to="{ name: 'SalesImport' }"
						class="rounded-full px-3 py-1.5 text-sm font-semibold text-white"
						style="background: var(--il-violet)"
					>
						{{ __('Import') }}
					</router-link>
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-6xl px-5 pt-8 sm:px-8">
			<p class="text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--il-magenta)]">
				Sales CRT
			</p>
			<h1 class="mt-2 text-3xl font-semibold tracking-tight text-[color:var(--il-ink)] sm:text-4xl">
				{{ schedule.data?.title || __('Classroom Readiness Training') }}
			</h1>
			<p class="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--il-muted)]">
				{{
					schedule.data?.short_introduction ||
					__('Day-by-day CRT schedule imported from Excel into Frappe.')
				}}
			</p>

			<div v-if="days.length" class="mt-8 flex gap-2 overflow-x-auto pb-2">
				<button
					v-for="day in days"
					:key="day.day_number"
					class="shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition"
					:class="
						selectedDay === day.day_number
							? 'text-white shadow-md'
							: 'bg-white text-[color:var(--il-ink)] border border-violet-100'
					"
					:style="selectedDay === day.day_number ? { background: 'var(--il-gradient)' } : {}"
					@click="selectedDay = day.day_number"
				>
					{{ day.day_label }}
				</button>
			</div>

			<div v-if="schedule.loading" class="sales-card mt-8 p-8 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading schedule…') }}
			</div>
			<div v-else-if="schedule.data?.empty" class="sales-card mt-8 p-10 text-center">
				<p class="text-lg font-semibold">{{ __('No CRT sessions yet') }}</p>
				<p class="mt-2 text-sm text-[color:var(--il-muted)]">
					Import the CRT Excel to create the course, chapters, and this schedule.
				</p>
			</div>

			<div v-else-if="activeDay" class="mt-8 grid gap-8 lg:grid-cols-[220px_1fr]">
				<aside class="sales-card h-fit p-5">
					<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ activeDay.day_label }}</div>
					<div class="mt-3 space-y-2 text-xs text-[color:var(--il-muted)]">
						<div>{{ activeDay.learning_count }} learning blocks</div>
						<div>{{ activeDay.session_count }} total slots</div>
						<div v-if="activeDay.total_minutes">{{ activeDay.total_minutes }} minutes</div>
					</div>
				</aside>

				<ol class="relative space-y-4 border-s-2 border-violet-100 ps-6">
					<li v-for="session in activeDay.sessions" :key="session.session_key" class="relative">
						<span
							class="absolute -start-[31px] top-5 h-3.5 w-3.5 rounded-full border-2 border-white"
							:style="{ background: dotColor(session.session_type) }"
						/>
						<article class="sales-card sales-card-hover p-5">
							<div class="flex flex-wrap items-center gap-2">
								<span class="sales-chip" :class="`sales-chip-${session.session_type}`">
									{{ session.session_type }}
								</span>
								<span v-if="session.time_label" class="text-xs font-medium text-[color:var(--il-muted)]">
									{{ session.time_label }}
								</span>
								<span v-if="session.stakeholder" class="text-xs text-[color:var(--il-violet)]">
									{{ session.stakeholder }}
								</span>
							</div>
							<h3 class="mt-3 text-lg font-semibold text-[color:var(--il-ink)]">
								{{ session.topic }}
							</h3>
							<div
								v-if="session.description"
								class="prose prose-sm mt-2 max-w-none text-[color:var(--il-muted)]"
								v-html="session.description"
							/>
							<div v-if="session.content_links?.length" class="mt-4 flex flex-wrap gap-2">
								<a
									v-for="link in session.content_links"
									:key="link.url"
									:href="link.url"
									target="_blank"
									rel="noreferrer"
									class="rounded-full border border-violet-100 bg-violet-50 px-3 py-1 text-xs font-semibold text-[color:var(--il-violet)] hover:bg-violet-100"
								>
									{{ link.label }}
								</a>
							</div>
							<div class="mt-4 flex flex-wrap gap-2">
								<router-link
									:to="{ name: 'SalesSession', params: { sessionKey: session.session_key } }"
									class="rounded-full px-3 py-1.5 text-xs font-semibold text-white"
									style="background: var(--il-violet)"
								>
									{{ __('Open session') }}
								</router-link>
								<router-link
									v-if="session.chapter_number && session.lesson_number && schedule.data?.course"
									:to="{
										name: 'Lesson',
										params: {
											courseName: schedule.data.course,
											chapterNumber: session.chapter_number,
											lessonNumber: session.lesson_number,
										},
									}"
									class="rounded-full border border-violet-200 px-3 py-1.5 text-xs font-semibold text-[color:var(--il-violet)]"
								>
									{{ __('LMS lesson') }}
								</router-link>
							</div>
						</article>
					</li>
				</ol>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createResource } from 'frappe-ui'
import { usersStore } from '@/stores/user'
import logoSrc from '@/assets/sales-logo.svg'

const route = useRoute()
const { userResource: user } = usersStore()
const selectedDay = ref(Number(route.query.day || 1))

const schedule = createResource({
	url: 'lms.lms.sales_crt.get_schedule',
	auto: true,
	cache: 'sales-crt-schedule',
})

const canImport = computed(
	() =>
		!!(
			user.data?.is_moderator ||
			user.data?.is_instructor ||
			user.data?.is_system_manager
		)
)

const days = computed(() => schedule.data?.days || [])
const activeDay = computed(
	() => days.value.find((d) => d.day_number === selectedDay.value) || days.value[0]
)

watch(
	() => route.query.day,
	(day) => {
		if (day) selectedDay.value = Number(day)
	}
)

watch(days, (list) => {
	if (list.length && !list.some((d) => d.day_number === selectedDay.value)) {
		selectedDay.value = list[0].day_number
	}
})

const dotColor = (type) =>
	({
		session: '#6d28d9',
		assessment: '#db2777',
		activity: '#f97316',
		calling: '#0ea5e9',
		break: '#94a3b8',
		lunch: '#64748b',
	})[type] || '#6d28d9'
</script>
