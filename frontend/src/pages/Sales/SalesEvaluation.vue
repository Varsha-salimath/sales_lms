<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div class="mx-auto max-w-4xl px-5 pt-8">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="$router.push({ name: 'StudentDashboard' })">
				← {{ __('Home') }}
			</button>

			<div v-if="page.loading" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading evaluation…') }}
			</div>
			<div v-else-if="page.error" class="mt-10 text-sm text-[color:var(--genius-red)]">
				{{ page.error.messages?.[0] || __('Unable to load evaluation.') }}
			</div>
			<section v-else-if="page.data?.locked" class="sales-card mt-8 p-8">
				<h1 class="text-2xl font-semibold text-[color:var(--il-ink)]">
					{{ __('Training evaluation locked') }}
				</h1>
				<p class="mt-3 text-sm text-[color:var(--il-muted)]">{{ page.data.reason }}</p>
			</section>
			<section v-else class="mt-6">
				<p class="text-xs font-semibold uppercase tracking-[0.2em]" style="color: #0075ff">
					{{ __('After CRT 5') }}
				</p>
				<h1 class="mt-2 text-3xl font-semibold text-[color:var(--il-ink)]">
					{{ __('Sales training performance') }}
				</h1>
				<p class="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--il-muted)]">
					{{
						__(
							'You have completed your classroom/CRT onboarding. Here is your Sales training performance, scored from the sessions you finished — not a random rating.'
						)
					}}
				</p>

				<div v-if="!evaluation" class="sales-card mt-8 p-6">
					<p class="text-sm text-[color:var(--il-ink)]">
						{{ __('Generate your rating from CRT 1–5 completion.') }}
					</p>
					<button
						type="button"
						class="mt-4 rounded-full px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
						style="background: #0075ff"
						:disabled="saving"
						@click="runEval"
					>
						{{ saving ? __('Scoring…') : __('Generate training evaluation') }}
					</button>
					<p v-if="saveError" class="mt-3 text-sm text-[color:var(--genius-red)]">{{ saveError }}</p>
				</div>

				<div v-else>
					<div class="sales-card mt-8 grid gap-6 p-6 sm:grid-cols-[160px_1fr]">
						<div class="text-center">
							<div class="text-5xl font-semibold tabular-nums" style="color: #0075ff">
								{{ Math.round(evaluation.overall_score || 0) }}
							</div>
							<div class="mt-1 text-xs uppercase tracking-wide text-[color:var(--il-muted)]">
								{{ __('Overall') }}
							</div>
						</div>
						<div>
							<div class="text-lg font-semibold text-[color:var(--il-ink)]">{{ evaluation.readiness }}</div>
							<p class="mt-2 text-sm text-[color:var(--il-ink)]">
								<strong>{{ __('Strengths') }}:</strong> {{ evaluation.strengths }}
							</p>
							<p class="mt-2 text-sm text-[color:var(--il-ink)]">
								<strong>{{ __('Improve') }}:</strong> {{ evaluation.improvements }}
							</p>
							<p class="mt-2 text-sm text-[color:var(--il-muted)]">{{ evaluation.next_step }}</p>
							<button
								type="button"
								class="mt-4 text-sm font-semibold"
								style="color: #0075ff"
								:disabled="saving"
								@click="runEval"
							>
								{{ __('Refresh from latest CRT progress') }}
							</button>
						</div>
					</div>

					<div class="mt-6 space-y-3">
						<div
							v-for="row in evaluation.scores"
							:key="row.criterion"
							class="sales-card p-4"
						>
							<div class="flex items-center justify-between gap-3">
								<div class="text-sm font-semibold text-[color:var(--il-ink)]">{{ row.criterion }}</div>
								<div class="text-sm font-semibold tabular-nums" style="color: #0075ff">
									{{ Math.round(row.score) }}
								</div>
							</div>
							<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-[#e8f2ff]">
								<div class="h-full rounded-full" style="background: #0075ff" :style="{ width: `${row.score}%` }" />
							</div>
							<p class="mt-2 text-xs text-[color:var(--il-muted)]">{{ row.source }}</p>
						</div>
					</div>

					<button
						type="button"
						class="mt-8 rounded-full px-5 py-2.5 text-sm font-semibold text-white"
						style="background: #0075ff"
						@click="$router.push({ name: 'SalesOJT' })"
					>
						{{ __('Continue to OJT') }}
					</button>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { call, createResource } from 'frappe-ui'

const page = createResource({
	url: 'lms.lms.sales_journey.get_evaluation',
	auto: true,
	cache: ['sales-evaluation'],
})

const evaluation = computed(() => page.data?.evaluation)
const saving = ref(false)
const saveError = ref('')

const runEval = async () => {
	saving.value = true
	saveError.value = ''
	try {
		const data = await call('lms.lms.sales_journey.complete_evaluation')
		page.data = data
	} catch (e) {
		saveError.value = e.messages?.[0] || e.message || __('Could not generate evaluation.')
	} finally {
		saving.value = false
	}
}
</script>
