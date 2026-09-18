<template>
	<div>
		<div class="mx-auto max-w-5xl px-5 pt-4 pb-5">
			<div class="mb-4 flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<h1 class="text-2xl font-semibold text-ink-gray-9">
						{{ __('NEWSPAPER') }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-6">
						{{ __('Share important updates with your LMS learners.') }}
					</p>
				</div>
				<Button variant="solid" @click="router.push({ name: 'NewspaperCreate' })">
					<template #prefix>
						<Plus class="h-4 w-4" />
					</template>
					{{ __('Add Newspaper') }}
				</Button>
			</div>

			<div v-if="newspapers.loading" class="text-sm text-ink-gray-5">
				{{ __('Loading published updates...') }}
			</div>

			<div
				v-else-if="!newspapers.data?.length"
				class="rounded-xl border border-dashed bg-surface-gray-2 p-10 text-center"
			>
				<Newspaper class="mx-auto mb-3 h-10 w-10 text-ink-gray-5" />
				<p class="text-sm text-ink-gray-6">
					{{ __('No newspaper updates have been sent yet.') }}
				</p>
				<Button
					class="mt-4"
					variant="solid"
					@click="router.push({ name: 'NewspaperCreate' })"
				>
					{{ __('Add Newspaper') }}
				</Button>
			</div>

			<div v-else class="space-y-4">
				<h2 class="text-base font-semibold text-ink-gray-8">
					{{ __('Published Updates') }}
				</h2>
				<div
					v-for="item in newspapers.data"
					:key="item.name"
					class="rounded-xl border bg-surface-white p-5 shadow-sm transition hover:border-outline-gray-3"
				>
					<div class="flex gap-4">
						<div
							v-if="item.image"
							class="hidden h-20 w-20 flex-shrink-0 overflow-hidden rounded-lg border sm:block"
						>
							<img
								:src="item.image"
								:alt="item.title"
								class="h-full w-full object-cover"
							/>
						</div>
						<div class="min-w-0 flex-1">
							<div class="flex items-start gap-2">
								<Newspaper class="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-blue-3" />
								<h3 class="text-lg font-semibold text-ink-gray-9">
									{{ item.title }}
								</h3>
							</div>
							<p
								v-if="item.content_preview"
								class="mt-2 line-clamp-2 text-sm text-ink-gray-6"
							>
								{{ item.content_preview }}
							</p>
							<div class="mt-4 grid gap-1 text-sm text-ink-gray-6 sm:grid-cols-2">
								<div>
									<span class="font-medium text-ink-gray-7"
										>{{ __('Sent to') }}:</span
									>
									{{ item.target_label }}
								</div>
								<div>
									<span class="font-medium text-ink-gray-7"
										>{{ __('Published') }}:</span
									>
									{{ formatDateTime(item.published_at) }}
								</div>
								<div>
									<span class="font-medium text-ink-gray-7"
										>{{ __('Recipients') }}:</span
									>
									{{ item.recipient_count }}
								</div>
								<div>
									<span class="font-medium text-ink-gray-7"
										>{{ __('Status') }}:</span
									>
									<span
										:class="
											item.status === 'Sent'
												? 'text-ink-green-3'
												: item.status === 'Failed'
													? 'text-ink-red-3'
													: 'text-ink-orange-3'
										"
									>
										{{ statusLabel(item.status) }}
									</span>
								</div>
							</div>
							<div class="mt-4">
								<Button
									variant="outline"
									@click="
										router.push({
											name: 'NewspaperDetail',
											params: { name: item.name },
										})
									"
								>
									{{ __('View') }}
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, createResource, usePageMeta } from 'frappe-ui'
import { watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { Newspaper, Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()

watchEffect(() => {
	if (userResource.data?.is_student) {
		router.replace({ name: 'StudentDashboard' })
	}
})

const newspapers = createResource({
	url: 'lms.lms.newspaper.get_newspapers',
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
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	})
}

const statusLabel = (status) => {
	if (status === 'Sent') return `✓ ${__('Sent')}`
	if (status === 'Sending') return __('Sending')
	if (status === 'Failed') return __('Failed')
	return status
}
</script>
