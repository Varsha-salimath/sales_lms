<template>
	<div class="min-h-screen pb-16" style="background: var(--il-paper)">
		<div class="mx-auto max-w-3xl px-5 pt-8">
			<button class="text-sm font-semibold" style="color: #0075ff" @click="$router.push({ name: 'StudentDashboard' })">
				← {{ __('Home') }}
			</button>

			<div v-if="state.loading" class="mt-10 text-sm text-[color:var(--il-muted)]">
				{{ __('Checking certificate eligibility…') }}
			</div>
			<div v-else-if="state.error" class="mt-10 text-sm text-[color:var(--genius-red)]">
				{{ state.error.messages?.[0] || __('Unable to load certificate status.') }}
			</div>
			<section v-else-if="state.data" class="sales-card mt-8 p-8">
				<p class="text-xs font-semibold uppercase tracking-[0.2em]" style="color: #0075ff">
					{{ __('Sales CRT') }}
				</p>
				<h1 class="mt-2 text-3xl font-semibold text-[color:var(--il-ink)]">
					{{ __('Certificate') }}
				</h1>
				<p class="mt-3 text-sm leading-6 text-[color:var(--il-muted)]">
					{{
						__(
							'Eligibility is calculated in Frappe from CRT completion, training evaluation, and one finished OJT simulation. Course feedback is not required.'
						)
					}}
				</p>

				<div v-if="state.data.certificate" class="mt-6">
					<p class="text-sm font-semibold text-green-700">{{ __('Your certificate is ready.') }}</p>
					<button
						type="button"
						class="mt-4 rounded-full px-5 py-2.5 text-sm font-semibold text-white"
						style="background: #0075ff"
						@click="openCert"
					>
						{{ __('View certificate') }}
					</button>
				</div>
				<div v-else-if="state.data.eligible" class="mt-6">
					<button
						type="button"
						class="rounded-full px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
						style="background: #0075ff"
						:disabled="claiming"
						@click="claim"
					>
						{{ claiming ? __('Issuing…') : __('Claim certificate') }}
					</button>
					<p v-if="claimError" class="mt-3 text-sm text-[color:var(--genius-red)]">{{ claimError }}</p>
				</div>
				<div v-else class="mt-6 rounded-2xl bg-[#fff7e0] px-4 py-3 text-sm text-[color:var(--il-ink)]">
					<strong>{{ __('Not eligible yet.') }}</strong>
					{{ state.data.reason }}
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { call, createResource } from 'frappe-ui'
import { openCertificatePreview } from '@/utils/certificate'

const state = createResource({
	url: 'lms.lms.sales_journey.get_certificate_state',
	auto: true,
	cache: ['sales-certificate'],
})

const claiming = ref(false)
const claimError = ref('')

const claim = async () => {
	claiming.value = true
	claimError.value = ''
	try {
		const data = await call('lms.lms.sales_journey.claim_certificate')
		state.data = data
		if (data.certificate) openCertificatePreview(data.certificate)
	} catch (e) {
		claimError.value = e.messages?.[0] || e.message || __('Could not issue the certificate.')
	} finally {
		claiming.value = false
	}
}

const openCert = () => {
	if (state.data?.certificate) openCertificatePreview(state.data.certificate)
}
</script>
