<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div class="mx-auto max-w-4xl px-5 pt-8">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="$router.push({ name: 'StudentDashboard' })">
				← {{ __('Home') }}
			</button>

			<div v-if="detail.loading" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading CRT…') }}
			</div>
			<div v-else-if="detail.error" class="mt-10 text-sm text-[color:var(--genius-red)]">
				{{ detail.error.messages?.[0] || __('This CRT could not be loaded.') }}
			</div>
			<div v-else-if="crt" class="mt-6">
				<p class="text-xs font-semibold uppercase tracking-[0.2em]" style="color: #0075ff">
					{{ __('Classroom readiness') }}
				</p>
				<div class="mt-2 flex flex-wrap items-end justify-between gap-3">
					<h1 class="text-3xl font-semibold text-[color:var(--il-ink)]">{{ crt.title }}</h1>
					<span class="rounded-full px-3 py-1 text-xs font-semibold" :class="badgeClass">
						{{ stateLabel(crt.state) }}
					</span>
				</div>
				<p class="mt-2 text-sm text-[color:var(--il-muted)]">
					{{ crt.lessons_done }}/{{ crt.lessons_total }} {{ __('sessions complete') }} ·
					{{ crt.progress }}%
				</p>

				<div
					v-if="crt.state === 'locked'"
					class="sales-card mt-6 p-6 text-sm text-[color:var(--il-ink)]"
				>
					{{ __('Complete the previous CRT before this one unlocks.') }}
				</div>
				<div
					v-else-if="!crt.lessons_total"
					class="sales-card mt-6 p-6 text-sm text-[color:var(--il-muted)]"
				>
					{{ __('No sessions have been imported for this CRT yet.') }}
				</div>
				<ol v-else class="mt-6 space-y-3">
					<li
						v-for="lesson in crt.lessons"
						:key="lesson.name"
						class="sales-card flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6"
					>
						<div>
							<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ lesson.title }}</div>
							<div class="text-xs text-[color:var(--il-muted)]">
								{{ sessionMeta(lesson) }}
							</div>
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
						<span v-else class="text-xs font-semibold text-[color:var(--il-muted)]">
							{{ __('Locked') }}
						</span>
					</li>
				</ol>

				<div v-if="crt.viva?.required || crt.viva?.can_try" class="viva-card mt-6" :class="{ 'is-ready': vivaReady }">
					<div class="viva-icon"><Mic class="h-5 w-5" /></div>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ __('Voice viva') }}</div>
						<div class="text-xs text-[color:var(--il-muted)]">{{ vivaLine }}</div>
					</div>
					<button
						v-if="crt.viva.passed || vivaReady || crt.viva.history?.length"
						type="button"
						class="rounded-full px-4 py-2 text-xs font-semibold"
						:class="vivaReady ? 'text-white' : 'border'"
						:style="vivaReady ? 'background: #0075ff' : 'border-color: #d7e4f7; color: #0075ff'"
						@click="$router.push({ name: 'SalesViva', params: { crtNumber: String(crt.crt_number) } })"
					>
						{{ vivaReady ? (crt.viva?.can_try ? __('Try the viva') : __('Start viva')) : __('View') }}
					</button>
				</div>

				<div class="mt-8 flex flex-wrap gap-3">
					<button
						v-if="crt.crt_number < 5"
						type="button"
						class="rounded-full border px-4 py-2 text-sm font-semibold"
						style="border-color: #d7e4f7"
						@click="$router.push({ name: 'SalesCRT', params: { crtNumber: String(crt.crt_number + 1) } })"
					>
						{{ __('Next CRT') }}
					</button>
					<button
						v-else
						type="button"
						class="rounded-full px-4 py-2 text-sm font-semibold text-white"
						style="background: #0075ff"
						@click="$router.push({ name: 'SalesEvaluation' })"
					>
						{{ __('Training evaluation') }}
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

const detail = createResource({
	url: 'lms.lms.sales_journey.get_crt_detail',
	makeParams: () => ({ crt_number: route.params.crtNumber }),
	auto: true,
})

watch(
	() => route.params.crtNumber,
	() => detail.reload()
)

const crt = computed(() => detail.data?.crt)

const badgeClass = computed(() => {
	const state = crt.value?.state
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
	() => (crt.value?.state === 'viva_pending' && !crt.value?.viva?.blocked) || Boolean(crt.value?.viva?.can_try && !crt.value?.viva?.passed)
)

const vivaLine = computed(() => {
	const c = crt.value
	const v = c?.viva || {}
	if (v.passed) return __('Passed · this day is complete')
	if (v.can_try) return __('Staff preview · try this day’s viva any time (learners get it after the sessions)')
	if (v.blocked) return __('All attempts used · your Training Manager can unlock more')
	if (c?.state === 'viva_pending') return `${__('A 3–4 minute spoken check on today’s content')} · ${v.attempts_left ?? 3} ${__('attempts left')}`
	return __('Unlocks when all sessions above are done')
})

const sessionMeta = (lesson) => {
	const row = (detail.data?.sessions || []).find((s) => s.lesson === lesson.name)
	if (!row) return lesson.complete ? __('Completed') : __('Session')
	return [row.time_label, row.stakeholder].filter(Boolean).join(' · ')
}

const openLesson = (lesson) => {
	const [chapterNumber, lessonNumber] = String(lesson.number).split('-')
	router.push({
		name: 'Lesson',
		params: {
			courseName: detail.data.course,
			chapterNumber,
			lessonNumber,
		},
	})
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
