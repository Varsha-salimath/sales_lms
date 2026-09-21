<template>
	<div>
		<div class="mx-auto max-w-5xl px-5 pt-4 pb-5">
			<div class="mb-4 flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<h1 class="text-2xl font-semibold text-ink-gray-9">
						{{ __('Newsletter') }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-6">
						{{
							isAdmin
								? __('Share important updates with your LMS learners.')
								: __('Published updates from your training team.')
						}}
					</p>
				</div>
				<Button
					v-if="isAdmin"
					variant="solid"
					@click="router.push({ name: 'NewspaperCreate' })"
				>
					<template #prefix>
						<Plus class="h-4 w-4" />
					</template>
					{{ __('Add Newsletter') }}
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
					{{
						isAdmin
							? __('No newsletter updates have been sent yet.')
							: __('No newsletters have been published yet.')
					}}
				</p>
				<Button
					v-if="isAdmin"
					class="mt-4"
					variant="solid"
					@click="router.push({ name: 'NewspaperCreate' })"
				>
					{{ __('Add Newsletter') }}
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
								<div v-if="isAdmin">
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
								<div v-if="isAdmin">
									<span class="font-medium text-ink-gray-7"
										>{{ __('Recipients') }}:</span
									>
									{{ item.recipient_count }}
								</div>
								<div v-if="isAdmin">
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
							<div class="mt-4 flex flex-wrap gap-2">
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
								<Button
									v-if="isAdmin"
									variant="outline"
									theme="red"
									:loading="deleting === item.name"
									@click="confirmDelete(item)"
								>
									{{ __('Delete') }}
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
import { Button, call, createResource, toast, usePageMeta } from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Newspaper, Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()
const isAdmin = computed(() => {
	const user = userResource.data
	return !!(
		user?.is_moderator ||
		user?.is_instructor ||
		user?.is_evaluator ||
		user?.is_system_manager
	)
})

const deleting = ref(null)

const newspapers = createResource({
	url: 'lms.lms.newspaper.get_newspapers',
	auto: true,
})

const confirmDelete = (item) => {
	if (
		!window.confirm(
			__('Delete this newsletter permanently? Comments will also be removed.')
		)
	) {
		return
	}
	deleteNewsletter(item.name)
}

const deleteNewsletter = async (name) => {
	deleting.value = name
	try {
		await call('lms.lms.newspaper.delete_newspaper', { name })
		toast.success(__('Newsletter deleted'))
		newspapers.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Could not delete newsletter'))
	} finally {
		deleting.value = null
	}
}

usePageMeta(() => ({
	title: __('Newsletter'),
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
