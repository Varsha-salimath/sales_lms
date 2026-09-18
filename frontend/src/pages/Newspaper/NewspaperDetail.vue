<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
			<Button @click="router.push({ name: 'Newspaper' })">
				{{ __('Back to History') }}
			</Button>
		</header>

		<div class="mx-auto max-w-3xl p-5">
			<div v-if="detail.loading" class="text-sm text-ink-gray-5">
				{{ __('Loading newspaper...') }}
			</div>

			<div v-else-if="detail.data" class="space-y-6">
				<div>
					<h1 class="text-2xl font-semibold text-ink-gray-9">
						{{ detail.data.title }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-5">{{ __('NEWSPAPER') }}</p>
				</div>

				<img
					v-if="detail.data.image"
					:src="detail.data.image"
					class="max-h-80 w-full rounded-xl border object-cover"
					:alt="detail.data.title"
				/>

				<div
					class="prose prose-sm max-w-none rounded-xl border bg-surface-white p-5 text-ink-gray-8"
					v-html="detail.data.content"
				/>

				<div class="grid gap-3 rounded-xl border bg-surface-gray-2 p-5 text-sm">
					<div>
						<span class="font-medium text-ink-gray-7">{{ __('Target') }}:</span>
						{{ detail.data.target_label }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Recipients') }}:</span
						>
						{{ detail.data.recipient_count }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Published by') }}:</span
						>
						{{ detail.data.published_by_name || detail.data.published_by }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Published') }}:</span
						>
						{{ formatDateTime(detail.data.published_at) }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7">{{ __('Status') }}:</span>
						<span
							:class="
								detail.data.status === 'Sent'
									? 'text-ink-green-3'
									: detail.data.status === 'Failed'
										? 'text-ink-red-3'
										: 'text-ink-orange-3'
							"
						>
							{{ detail.data.status }}
						</span>
					</div>
					<div
						v-if="detail.data.email_sent_count || detail.data.email_failed_count"
					>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Email delivery') }}:</span
						>
						{{ __('Sent') }} {{ detail.data.email_sent_count || 0 }},
						{{ __('Failed') }} {{ detail.data.email_failed_count || 0 }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Breadcrumbs, Button, createResource, usePageMeta } from 'frappe-ui'
import { computed, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()

watchEffect(() => {
	if (userResource.data?.is_student) {
		router.replace({ name: 'StudentDashboard' })
	}
})

const breadcrumbs = computed(() => [
	{ label: __('Newspaper'), route: { name: 'Newspaper' } },
	{ label: props.name, route: { name: 'NewspaperDetail', params: { name: props.name } } },
])

const detail = createResource({
	url: 'lms.lms.newspaper.get_newspaper',
	makeParams() {
		return { name: props.name }
	},
	auto: true,
})

usePageMeta(() => ({
	title: __('Newspaper'),
	icon: brand.favicon,
}))

const formatDateTime = (value) => {
	if (!value) return '—'
	return new Date(value).toLocaleString(undefined, {
		day: '2-digit',
		month: 'long',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	})
}
</script>
