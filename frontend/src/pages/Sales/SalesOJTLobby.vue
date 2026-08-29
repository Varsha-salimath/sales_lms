<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div class="mx-auto max-w-4xl px-5 pt-8">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="$router.push({ name: 'StudentDashboard' })">
				← {{ __('Home') }}
			</button>

			<div v-if="state.loading" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Loading OJT…') }}
			</div>
			<div v-else-if="state.error" class="mt-10 text-sm text-[color:var(--genius-red)]">
				{{ state.error.messages?.[0] || __('Unable to load OJT.') }}
			</div>
			<section v-else-if="state.data?.locked" class="sales-card mt-8 p-8">
				<h1 class="text-2xl font-semibold text-[color:var(--il-ink)]">{{ __('OJT locked') }}</h1>
				<p class="mt-3 text-sm leading-6 text-[color:var(--il-ink)]">{{ state.data.reason }}</p>
			</section>
			<section v-else-if="state.data">
				<p class="mt-6 text-xs font-semibold uppercase tracking-[0.2em]" style="color: #0075ff">
					{{ __('On-the-job training') }}
				</p>
				<h1 class="mt-2 text-3xl font-semibold text-[color:var(--il-ink)]">
					{{ __('Live sales simulation') }}
				</h1>
				<p class="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--il-muted)]">
					{{
						__(
							'Speak with a simulated parent the way you would on a real CRT calling floor. Scored against the Audit Sample: Introduction, Rapport, Need Generation, Session Pitching, Closing.'
						)
					}}
				</p>

				<div class="mt-8 space-y-4">
					<article
						v-for="row in state.data.scenarios"
						:key="row.name"
						class="sales-card flex flex-wrap items-center justify-between gap-4 p-5"
					>
						<div>
							<p class="text-xs font-semibold" style="color: #0075ff">{{ row.source_crt }}</p>
							<h2 class="mt-1 text-lg font-semibold text-[color:var(--il-ink)]">{{ row.title }}</h2>
							<p class="mt-1 text-sm text-[color:var(--il-muted)]">
								{{ row.customer_name }} · {{ row.customer_role }}
							</p>
							<p class="mt-2 text-sm text-[color:var(--il-ink)]">{{ row.objective }}</p>
						</div>
						<button
							type="button"
							class="rounded-full px-5 py-2.5 text-sm font-semibold text-white"
							style="background: #0075ff"
							@click="$router.push({ name: 'SalesOJTSim', params: { scenarioKey: row.name } })"
						>
							{{ __('Start simulation') }}
						</button>
					</article>
				</div>

				<section v-if="state.data.attempts?.length" class="mt-10">
					<h2 class="text-lg font-semibold text-[color:var(--il-ink)]">{{ __('Your attempts') }}</h2>
					<ul class="mt-3 space-y-2">
						<li
							v-for="row in state.data.attempts"
							:key="row.name"
							class="flex flex-wrap items-center justify-between gap-2 rounded-2xl border px-4 py-3 text-sm"
							style="border-color: var(--il-border)"
						>
							<span>{{ row.scenario }} · {{ row.status }}</span>
							<span v-if="row.overall_score != null" class="font-semibold" style="color: #0075ff">
								{{ Math.round(row.overall_score) }}
							</span>
						</li>
					</ul>
				</section>
			</section>
		</div>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const state = createResource({
	url: 'lms.lms.sales_journey.get_ojt_state',
	auto: true,
	cache: ['sales-ojt-state'],
})
</script>
