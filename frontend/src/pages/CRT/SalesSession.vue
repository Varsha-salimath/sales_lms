<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<header class="border-b border-violet-100 bg-white">
			<div class="mx-auto flex max-w-3xl items-center justify-between px-5 py-3">
				<router-link :to="{ name: 'SalesSchedule' }" class="text-sm font-semibold text-[color:var(--il-violet)]">
					← {{ __('Back to schedule') }}
				</router-link>
			</div>
		</header>

		<div class="mx-auto max-w-3xl px-5 pt-10">
			<div v-if="session.loading" class="sales-card p-8 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading session…') }}
			</div>
			<article v-else-if="session.data" class="sales-card p-8">
				<div class="flex flex-wrap items-center gap-2">
					<span class="sales-chip" :class="`sales-chip-${session.data.session_type}`">
						{{ session.data.session_type }}
					</span>
					<span class="text-xs font-medium text-[color:var(--il-muted)]">
						{{ session.data.day_label }}
					</span>
				</div>
				<h1 class="mt-4 text-3xl font-semibold tracking-tight text-[color:var(--il-ink)]">
					{{ session.data.topic }}
				</h1>
				<div class="mt-4 flex flex-wrap gap-4 text-sm text-[color:var(--il-muted)]">
					<span v-if="session.data.time_label">{{ session.data.time_label }}</span>
					<span v-if="session.data.stakeholder">Owner: {{ session.data.stakeholder }}</span>
					<span v-if="session.data.duration_minutes">{{ session.data.duration_minutes }} mins</span>
				</div>
				<div
					v-if="session.data.description"
					class="prose mt-6 max-w-none text-[color:var(--il-ink)]"
					v-html="session.data.description"
				/>
				<div v-if="session.data.content_links?.length" class="mt-8">
					<h2 class="text-sm font-semibold uppercase tracking-wider text-[color:var(--il-magenta)]">
						{{ __('Resources') }}
					</h2>
					<div class="mt-3 grid gap-2">
						<a
							v-for="link in session.data.content_links"
							:key="link.url"
							:href="link.url"
							target="_blank"
							rel="noreferrer"
							class="rounded-2xl border border-violet-100 bg-violet-50 px-4 py-3 text-sm font-semibold text-[color:var(--il-violet)] hover:bg-violet-100"
						>
							{{ link.label }}
						</a>
					</div>
				</div>
				<router-link
					v-if="session.data.chapter_number && session.data.lesson_number"
					:to="{
						name: 'Lesson',
						params: {
							courseName: session.data.course,
							chapterNumber: session.data.chapter_number,
							lessonNumber: session.data.lesson_number,
						},
					}"
					class="mt-8 inline-flex rounded-full px-5 py-2.5 text-sm font-semibold text-white"
					style="background: var(--il-gradient)"
				>
					{{ __('Continue in LMS lesson') }}
				</router-link>
			</article>
		</div>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const props = defineProps({
	sessionKey: { type: String, required: true },
})

const session = createResource({
	url: 'lms.lms.sales_crt.get_session',
	makeParams: () => ({ session_key: props.sessionKey }),
	auto: true,
})
</script>
