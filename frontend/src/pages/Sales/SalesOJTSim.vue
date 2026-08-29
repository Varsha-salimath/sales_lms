<template>
	<div class="min-h-screen pb-10" style="background: var(--il-paper)">
		<div class="mx-auto max-w-6xl px-4 pt-6">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="$router.push({ name: 'SalesOJT' })">
				← {{ __('OJT lobby') }}
			</button>

			<div v-if="bootError" class="mt-8 text-sm text-[color:var(--genius-red)]">{{ bootError }}</div>
			<div v-else-if="loading" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Connecting the live simulation…') }}
			</div>
			<div v-else-if="payload" class="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
				<section class="sales-card p-5 sm:p-7">
					<p class="text-xs font-semibold uppercase tracking-[0.18em]" style="color: #0075ff">
						{{ payload.scenario.source_crt }}
					</p>
					<h1 class="mt-2 text-2xl font-semibold text-[color:var(--il-ink)]">
						{{ payload.scenario.title }}
					</h1>
					<dl class="mt-5 space-y-4 text-sm">
						<div>
							<dt class="text-xs uppercase tracking-wide text-[color:var(--il-muted)]">{{ __('Customer') }}</dt>
							<dd class="mt-1 font-semibold text-[color:var(--il-ink)]">
								{{ payload.scenario.customer_name }} · {{ payload.scenario.customer_role }}
							</dd>
						</div>
						<div>
							<dt class="text-xs uppercase tracking-wide text-[color:var(--il-muted)]">{{ __('Objective') }}</dt>
							<dd class="mt-1 leading-6 text-[color:var(--il-ink)]">{{ payload.scenario.objective }}</dd>
						</div>
						<div>
							<dt class="text-xs uppercase tracking-wide text-[color:var(--il-muted)]">{{ __('Context') }}</dt>
							<dd class="mt-1 leading-6 text-[color:var(--il-muted)]">{{ payload.scenario.context }}</dd>
						</div>
						<div>
							<dt class="text-xs uppercase tracking-wide text-[color:var(--il-muted)]">{{ __('Instructions') }}</dt>
							<dd class="mt-1 leading-6 text-[color:var(--il-ink)]">{{ payload.scenario.instructions }}</dd>
						</div>
					</dl>
					<p v-if="hint" class="mt-6 rounded-2xl bg-[#fff7e0] px-4 py-3 text-sm text-[color:var(--il-ink)]">
						{{ hint }}
					</p>
					<div v-if="payload.attempt.status === 'Completed'" class="mt-6 rounded-2xl bg-[#e8f2ff] p-4">
						<div class="text-3xl font-semibold" style="color: #0075ff">
							{{ Math.round(payload.attempt.overall_score || 0) }}
						</div>
						<p class="mt-2 text-sm"><strong>{{ __('Strengths') }}:</strong> {{ payload.attempt.strengths }}</p>
						<p class="mt-1 text-sm"><strong>{{ __('Improve') }}:</strong> {{ payload.attempt.improvements }}</p>
						<ul class="mt-3 space-y-1 text-xs text-[color:var(--il-muted)]">
							<li v-for="row in payload.attempt.scores" :key="row.criterion">
								{{ row.criterion }} — {{ Math.round(row.score) }}
							</li>
						</ul>
						<button
							type="button"
							class="mt-4 rounded-full px-4 py-2 text-sm font-semibold text-white"
							style="background: #0075ff"
							@click="$router.push({ name: 'SalesCertificate' })"
						>
							{{ __('Certificate') }}
						</button>
					</div>
				</section>

				<aside class="sales-sim-panel">
					<div class="sales-sim-orb" :class="{ live: payload.attempt.status !== 'Completed', speaking }" />
					<p class="mt-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
						{{ __('Live sales simulation') }}
					</p>
					<p class="mt-1 text-center text-sm font-semibold text-white">
						{{ payload.scenario.customer_name }}
					</p>
					<div ref="threadEl" class="sales-sim-thread">
						<div
							v-for="(msg, idx) in payload.attempt.messages"
							:key="idx"
							class="sales-sim-bubble"
							:class="msg.role"
						>
							{{ msg.content }}
						</div>
					</div>
					<form v-if="payload.attempt.status !== 'Completed'" class="sales-sim-composer" @submit.prevent="sendTurn">
						<input
							v-model="draft"
							type="text"
							class="sales-sim-input"
							:placeholder="__('Reply to the parent…')"
							:disabled="sending"
						/>
						<button type="submit" class="sales-sim-send" :disabled="sending || !draft.trim()">
							{{ sending ? '…' : __('Send') }}
						</button>
					</form>
					<button
						v-if="payload.attempt.status !== 'Completed'"
						type="button"
						class="mt-3 w-full text-center text-xs text-white/70"
						@click="endEarly"
					>
						{{ __('End and score this call') }}
					</button>
				</aside>
			</div>
		</div>
	</div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'

const route = useRoute()
const loading = ref(true)
const bootError = ref('')
const payload = ref(null)
const draft = ref('')
const sending = ref(false)
const hint = ref('')
const speaking = ref(false)
const threadEl = ref(null)

const scrollThread = async () => {
	await nextTick()
	if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
}

const boot = async () => {
	loading.value = true
	bootError.value = ''
	try {
		payload.value = await call('lms.lms.sales_journey.start_ojt', {
			scenario: route.params.scenarioKey,
		})
		await scrollThread()
	} catch (e) {
		bootError.value = e.messages?.[0] || e.message || __('OJT is not available yet.')
	} finally {
		loading.value = false
	}
}

const sendTurn = async () => {
	if (!draft.value.trim() || !payload.value) return
	sending.value = true
	speaking.value = true
	try {
		const data = await call('lms.lms.sales_journey.send_ojt_turn', {
			attempt: payload.value.attempt.name,
			message: draft.value.trim(),
		})
		payload.value = data
		hint.value = data.hint || ''
		draft.value = ''
		await scrollThread()
	} catch (e) {
		hint.value = e.messages?.[0] || e.message || __('Could not send that reply.')
	} finally {
		sending.value = false
		setTimeout(() => {
			speaking.value = false
		}, 600)
	}
}

const endEarly = async () => {
	if (!payload.value) return
	sending.value = true
	try {
		payload.value = await call('lms.lms.sales_journey.finish_ojt', {
			attempt: payload.value.attempt.name,
		})
	} finally {
		sending.value = false
	}
}

onMounted(boot)
watch(() => route.params.scenarioKey, boot)
</script>
