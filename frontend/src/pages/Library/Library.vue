<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
			<Button
				v-if="canSync"
				variant="outline"
				:loading="syncing"
				:disabled="!stats.data?.can_sync"
				@click="triggerSync"
			>
				<template #prefix>
					<RefreshCw class="w-4 h-4" />
				</template>
				{{ __('Sync Now') }}
			</Button>
		</header>

		<div class="p-5">
			<div class="flex flex-col gap-1 mb-5">
				<h1 class="text-[22px] font-semibold text-ink-gray-9">
					{{ __('Library') }}
				</h1>
				<div v-if="stats.data?.linked_email" class="text-sm text-ink-gray-6">
					{{ stats.data.linked_email }}
					<span v-if="stats.data.last_synced && stats.data.last_synced !== '{}'">
						• {{ __('Last synced') }} {{ formatRelativeTime(stats.data.last_synced) }}
					</span>
				</div>
				<div v-if="stats.data?.total_recordings != null" class="text-sm text-ink-gray-5">
					{{ __('{0} recordings found').format(stats.data.total_recordings) }}
				</div>
			</div>

			<div
				v-if="syncing"
				class="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
			>
				{{ __('Syncing recordings from Google Drive... This may take a moment.') }}
			</div>

			<div
				v-if="isStaff() && !stats.loading && !stats.data?.has_linked_account"
				class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
			>
				{{
					__(
						'No Google account linked. Connect Google in Desk to sync new recordings from Drive.'
					)
				}}
			</div>

			<template v-if="!stats.loading">
				<div class="flex flex-wrap items-end gap-3 mb-5">
					<FormControl
						v-model="search"
						type="text"
						:label="__('Search')"
						:placeholder="__('Search by title or batch')"
						class="min-w-[220px] flex-1"
					/>
					<FormControl
						v-model="selectedBatch"
						type="select"
						:label="__('Batch')"
						:options="batchOptions"
						class="min-w-[180px]"
					/>
					<FormControl
						v-model="dateFrom"
						type="date"
						:label="__('From')"
						class="min-w-[150px]"
					/>
					<FormControl
						v-model="dateTo"
						type="date"
						:label="__('To')"
						class="min-w-[150px]"
					/>
					<FormControl
						v-model="durationFilter"
						type="select"
						:label="__('Duration')"
						:options="durationOptions"
						class="min-w-[150px]"
					/>
					<FormControl
						v-model="sortOrder"
						type="select"
						:label="__('Sort')"
						:options="sortOptions"
						class="min-w-[150px]"
					/>
					<Button
						v-if="hasActiveFilters"
						variant="subtle"
						@click="clearFilters"
					>
						{{ __('Clear Filters') }}
					</Button>
				</div>

				<div
					v-if="recordings.loading"
					class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
				>
					<div
						v-for="index in 6"
						:key="index"
						class="border rounded-lg bg-surface-white overflow-hidden animate-pulse"
					>
						<div class="aspect-video bg-surface-gray-2" />
						<div class="p-4 space-y-3">
							<div class="h-3 bg-surface-gray-2 rounded w-1/2" />
							<div class="h-4 bg-surface-gray-2 rounded w-full" />
							<div class="h-4 bg-surface-gray-2 rounded w-2/3" />
							<div class="h-9 bg-surface-gray-2 rounded w-full mt-4" />
						</div>
					</div>
				</div>

				<div
					v-else-if="recordings.data?.recordings?.length"
					class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
				>
					<RecordingCard
						v-for="recording in recordings.data.recordings"
						:key="recording.name"
						:recording="recording"
						:canAssign="canAssign"
						@assign="openAssignModal"
					/>
				</div>

				<div
					v-else-if="hasActiveFilters"
					class="rounded-lg border bg-surface-white p-8 text-center text-sm text-ink-gray-6"
				>
					{{ emptyStateMessage }}
				</div>

				<div
					v-else
					class="rounded-lg border bg-surface-white p-8 text-center text-sm text-ink-gray-6"
				>
					{{
						isStaff()
							? __(
									'No recordings yet. Sync from Google Drive, then grant access for each recording.'
								)
							: __('No recordings have been assigned to you yet.')
					}}
				</div>

				<div
					v-if="totalPages > 1"
					class="flex items-center justify-between mt-6"
				>
					<Button
						variant="subtle"
						:disabled="page <= 1"
						@click="page -= 1"
					>
						{{ __('Previous') }}
					</Button>
					<div class="text-sm text-ink-gray-6">
						{{ __('Page {0} of {1}').format(page, totalPages) }}
					</div>
					<Button
						variant="subtle"
						:disabled="page >= totalPages"
						@click="page += 1"
					>
						{{ __('Next') }}
					</Button>
				</div>
			</template>
		</div>
	</div>
	<AssignRecordingModal
		v-model="showAssignModal"
		:recording="selectedRecording"
		@saved="onAssignmentsSaved"
	/>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	FormControl,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'
import { computed, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import AssignRecordingModal from '@/components/Library/AssignRecordingModal.vue'
import RecordingCard from '@/components/Library/RecordingCard.vue'
import { usersStore } from '@/stores/user'
import dayjs from '@/utils/dayjs'

const router = useRouter()
const { userResource } = usersStore()

const breadcrumbs = [{ label: __('Library') }]
const search = ref('')
const debouncedSearch = ref('')
const selectedBatch = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const durationFilter = ref('')
const sortOrder = ref('desc')
const page = ref(1)
const syncing = ref(false)
const showAssignModal = ref(false)
const selectedRecording = ref(null)
let searchTimer = null

const isStaff = () => {
	const { userResource } = usersStore()
	return (
		userResource?.data?.is_instructor ||
		userResource?.data?.is_moderator ||
		userResource?.data?.is_evaluator
	)
}

const canSync = computed(() => isStaff())
const canAssign = computed(() => isStaff())

const openAssignModal = (recording) => {
	selectedRecording.value = recording
	showAssignModal.value = true
}

const onAssignmentsSaved = () => {
	stats.reload()
	recordings.reload()
}

const durationOptions = [
	{ label: __('All durations'), value: '' },
	{ label: __('Short (under 30 min)'), value: 'short' },
	{ label: __('Medium (30-60 min)'), value: 'medium' },
	{ label: __('Long (over 60 min)'), value: 'long' },
]

const sortOptions = [
	{ label: __('Newest first'), value: 'desc' },
	{ label: __('Oldest first'), value: 'asc' },
]

const stats = createResource({
	url: 'lms.lms.library_api.get_library_stats',
	auto: true,
})

const batchFilters = createResource({
	url: 'lms.lms.library_api.get_batch_filter_options',
	auto: true,
})

const batchOptions = computed(() => {
	const options = [{ label: __('All batches'), value: '' }]
	for (const batch of batchFilters.data || []) {
		options.push({ label: batch.title, value: batch.name })
	}
	return options
})

const recordings = createResource({
	url: 'lms.lms.library_api.get_recordings',
	makeParams() {
		return {
			batch_id: selectedBatch.value || undefined,
			search: debouncedSearch.value || undefined,
			date_from: dateFrom.value || undefined,
			date_to: dateTo.value || undefined,
			duration: durationFilter.value || undefined,
			sort_order: sortOrder.value,
			page: page.value,
			page_size: 20,
		}
	},
	auto: false,
})

let reloadTimer = null
const loadRecordings = () => {
	if (reloadTimer) clearTimeout(reloadTimer)
	reloadTimer = setTimeout(() => {
		reloadTimer = null
		recordings.reload()
	}, 50)
}

watch(search, (value) => {
	clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		if (!value || value.length >= 2) {
			debouncedSearch.value = value
			page.value = 1
			loadRecordings()
		} else if (!value) {
			debouncedSearch.value = ''
			page.value = 1
			loadRecordings()
		}
	}, 300)
})

watch([selectedBatch, dateFrom, dateTo, durationFilter, sortOrder, page], () => {
	loadRecordings()
})

watch(
	() => stats.data,
	(data) => {
		if (data) loadRecordings()
	},
	{ immediate: true }
)

const totalPages = computed(() => {
	const total = recordings.data?.total || 0
	return Math.max(1, Math.ceil(total / 20))
})

const hasActiveFilters = computed(() => {
	return Boolean(
		search.value ||
			selectedBatch.value ||
			dateFrom.value ||
			dateTo.value ||
			durationFilter.value
	)
})

const emptyStateMessage = computed(() => {
	if (
		selectedBatch.value &&
		!search.value &&
		!dateFrom.value &&
		!dateTo.value &&
		!durationFilter.value
	) {
		return __('No recordings found for this batch yet.')
	}

	return __('No recordings match your search. Try a different batch name or date.')
})

const clearFilters = () => {
	search.value = ''
	debouncedSearch.value = ''
	selectedBatch.value = ''
	dateFrom.value = ''
	dateTo.value = ''
	durationFilter.value = ''
	page.value = 1
	loadRecordings()
}

const formatRelativeTime = (value) => dayjs(value).fromNow()

const triggerSync = async () => {
	syncing.value = true
	try {
		await call('lms.lms.library_api.sync_recordings')
		toast.success(__('Recordings synced successfully.'))
		stats.reload()
		batchFilters.reload()
		recordings.reload()
	} catch (error) {
		toast.error(error?.messages?.[0] || __('Failed to sync recordings.'))
	} finally {
		syncing.value = false
	}
}

watchEffect(() => {
	if (!userResource.data) return
	if (!isStaff() && !userResource.data?.is_student) {
		router.replace({ name: 'Home' })
	}
})

usePageMeta(() => ({
	title: __('Library'),
}))
</script>
