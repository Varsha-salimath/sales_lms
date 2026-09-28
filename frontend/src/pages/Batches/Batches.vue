<template>
	<header
		class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<Dropdown
			v-if="canCreateBatch()"
			:options="[
				{
					label: __('New Batch'),
					icon: 'users',
					onClick() {
						showBatchModal = true
					},
				},
				{
					label: __('Import Batch'),
					icon: 'upload',
					onClick() {
						router.push({
							name: 'NewDataImport',
							params: { doctype: 'LMS Batch' },
						})
					},
				},
			]"
		>
			<template v-slot="{ open }">
				<Button variant="solid">
					<template #prefix>
						<Plus class="h-4 w-4 stroke-1.5" />
					</template>
					{{ __('Create') }}
					<template #suffix>
						<ChevronDown
							:class="[
								'w-4 h-4 stroke-1.5 ms-1 transform transition-transform',
								open ? 'rotate-180' : '',
							]"
						/>
					</template>
				</Button>
			</template>
		</Dropdown>
	</header>
	<div class="p-5 pb-10">
		<div
			class="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:items-center justify-between mb-5"
		>
			<div class="text-lg text-ink-gray-9 font-semibold">
				{{ pageHeading }}
			</div>
			<div
				v-if="!showStudentEnrolledLeaderboard"
				class="flex flex-col space-y-3 lg:space-y-0 lg:flex-row lg:items-center lg:gap-x-4"
			>
				<TabButtons
					v-if="user.data"
					:buttons="batchTabs"
					v-model="currentTab"
					class="w-fit"
				/>
				<div class="grid grid-cols-2 gap-2">
					<FormControl
						v-model="title"
						:placeholder="__('Search by Title')"
						type="text"
						class="min-w-40 lg:min-w-0 lg:w-32 xl:w-40"
						@input="updateBatches()"
					/>
					<div class="min-w-40 lg:min-w-0 lg:w-32 xl:w-40">
						<Select
							v-if="categories.length"
							v-model="currentCategory"
							:options="categories"
							:placeholder="__('Category')"
							@update:modelValue="updateBatches()"
						/>
					</div>
				</div>

				<Tooltip :text="__('Only show batches that offer a certificate')">
					<FormControl
						type="checkbox"
						v-model="certification"
						:label="__('Certification')"
						@change="updateBatches()"
					/>
				</Tooltip>
			</div>
			<TabButtons
				v-else-if="user.data"
				:buttons="batchTabs"
				v-model="currentTab"
				class="w-fit"
			/>
		</div>

		<!-- learner: enrolled tab with leaderboard on this page -->
		<div v-if="showStudentEnrolledLeaderboard" class="space-y-5 max-w-5xl">
			<div
				v-if="batches.data.length > 1"
				class="flex flex-wrap gap-2"
			>
				<Button
					v-for="batch in batches.data"
					:key="batch.name"
					:variant="selectedLeaderboardBatch === batch.name ? 'solid' : 'outline'"
					size="sm"
					@click="selectedLeaderboardBatch = batch.name"
				>
					{{ batch.title }}
				</Button>
			</div>
			<BatchLeaderboardPanel
				v-if="selectedLeaderboardBatch"
				:batch-name="selectedLeaderboardBatch"
				show-batch-details-link
			/>
		</div>

		<div
			v-else-if="batches.data?.length"
			class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
		>
			<BatchCard
				v-for="batch in batches.data"
				:key="batch.name"
				:batch="batch"
			/>
		</div>

		<!-- not enrolled empty state -->
		<div
			v-else-if="showStudentNotEnrolled && !batches.list.loading"
			class="flex min-h-[60vh] w-full flex-col items-center justify-center gap-4 px-4"
		>
			<EmptyStateLayout
				name="Batches"
				:title="__('You\'re not enrolled in any batch yet')"
				:description="
					__(
						'Browse available batches to join a cohort and see how you rank against your batchmates.'
					)
				"
				width="lg"
			/>
			<Button @click="browseBatches">
				{{ __('Browse Batches') }}
			</Button>
		</div>

		<EmptyStateLayout v-else-if="!batches.list.loading" name="Batches" />

		<div
			v-if="!showStudentEnrolledLeaderboard && !batches.list.loading && batches.hasNextPage"
			class="flex justify-center mt-5"
		>
			<Button @click="batches.next()">
				{{ __('Load More') }}
			</Button>
		</div>
	</div>
	<NewBatchModal
		v-if="showBatchModal"
		v-model="showBatchModal"
		:batches="batches"
	/>
</template>
<script setup>
import {
	Breadcrumbs,
	Button,
	createListResource,
	Dropdown,
	FormControl,
	Select,
	Tooltip,
	TabButtons,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import BatchCard from '@/pages/Batches/components/BatchCard.vue'
import BatchLeaderboardPanel from '@/pages/Batches/components/BatchLeaderboardPanel.vue'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import NewBatchModal from '@/pages/Batches/components/NewBatchModal.vue'

const user = inject('$user')
const dayjs = inject('$dayjs')
const { brand } = sessionStore()
const start = ref(0)
const pageLength = ref(20)
const categories = ref([])
const currentCategory = ref(null)
const title = ref('')
const certification = ref(false)
const filters = ref({})
const is_student = computed(() => user.data?.is_student)
const isLearnerOnly = computed(() => {
	const u = user.data
	if (!u?.is_student) return false
	return !u.is_moderator && !u.is_instructor && !u.is_evaluator && !u.is_system_manager
})
const currentTab = ref('all')
const selectedLeaderboardBatch = ref(null)
const orderBy = ref('start_date')
const readOnlyMode = window.read_only_mode
const router = useRouter()
const showBatchModal = ref(false)

onMounted(() => {
	setFiltersFromQuery()
	if (isLearnerOnly.value) {
		currentTab.value = 'enrolled'
	}
	updateBatches()
	categories.value = [
		{
			label: '',
			value: null,
		},
	]
})

watch(
	() => user.data,
	(u) => {
		if (u && isLearnerOnly.value && currentTab.value === 'all') {
			currentTab.value = 'enrolled'
			updateBatches()
		}
	}
)

watch(
	() => batches.data,
	(data) => {
		if (!data?.length) {
			selectedLeaderboardBatch.value = null
			return
		}
		const stillValid = data.some((b) => b.name === selectedLeaderboardBatch.value)
		if (!stillValid) {
			selectedLeaderboardBatch.value = data[0].name
		}
	}
)

const setFiltersFromQuery = () => {
	let queries = new URLSearchParams(location.search)
	title.value = queries.get('title') || ''
	currentCategory.value = queries.get('category') || null
	certification.value = queries.get('certification') || false
}

const batches = createListResource({
	doctype: 'LMS Batch',
	url: 'lms.lms.utils.get_batches',
	cache: ['batches', user.data?.name],
	pageLength: pageLength.value,
	start: start.value,
})

const setCategories = (data) => {
	let allCategories = data.map((batch) => batch.category)
	allCategories = allCategories.filter(
		(category, index) => allCategories.indexOf(category) === index && category
	)
	if (categories.value.length <= allCategories.length) {
		updateCategories(data)
	}
}

const updateBatches = () => {
	updateFilters()
	batches.update({
		filters: filters.value,
		orderBy: orderBy.value,
	})
	batches.reload().then((data) => {
		setCategories(data)
	})
}

const updateFilters = () => {
	updateCategoryFilter()
	updateTitleFilter()
	updateCertificationFilter()
	updateTabFilter()
	updateStudentFilter()
	setQueryParams()
}

const updateCategoryFilter = () => {
	if (currentCategory.value) {
		filters.value['category'] = currentCategory.value
	} else {
		delete filters.value['category']
	}
}

const updateTitleFilter = () => {
	if (title.value) {
		filters.value['title'] = ['like', `%${title.value}%`]
	} else {
		delete filters.value['title']
	}
}

const updateCertificationFilter = () => {
	if (certification.value) {
		filters.value['certification'] = 1
	} else {
		delete filters.value['certification']
	}
}

const updateTabFilter = () => {
	orderBy.value = 'start_date'
	if (!user.data) {
		return
	}
	if (currentTab.value == 'enrolled' && is_student.value) {
		filters.value['enrolled'] = 1
		delete filters.value['start_date']
		delete filters.value['published']
		delete filters.value['student_all']
		orderBy.value = 'start_date desc'
	} else if (is_student.value) {
		delete filters.value['enrolled']
		delete filters.value['student_all']
	} else {
		delete filters.value['start_date']
		delete filters.value['published']
		orderBy.value = 'start_date desc'
		if (currentTab.value == 'upcoming') {
			filters.value['start_date'] = ['>=', dayjs().format('YYYY-MM-DD')]
			filters.value['published'] = 1
			orderBy.value = 'start_date'
		} else if (currentTab.value == 'archived') {
			filters.value['start_date'] = ['<=', dayjs().format('YYYY-MM-DD')]
		} else if (currentTab.value == 'unpublished') {
			filters.value['published'] = 0
		}
	}
}

const updateStudentFilter = () => {
	if (!user.data) {
		return
	}
	if (is_student.value && currentTab.value === 'enrolled') {
		return
	}
	if (is_student.value && currentTab.value === 'all') {
		filters.value['student_all'] = 1
		delete filters.value['start_date']
		delete filters.value['published']
		return
	}
	if (is_student.value) {
		filters.value['start_date'] = ['>=', dayjs().format('YYYY-MM-DD')]
		filters.value['published'] = 1
		delete filters.value['student_all']
	}
}

const setQueryParams = () => {
	let queries = new URLSearchParams(location.search)
	let filterKeys = {
		title: title.value,
		category: currentCategory.value,
		certification: certification.value,
	}

	Object.keys(filterKeys).forEach((key) => {
		if (filterKeys[key]) {
			queries.set(key, filterKeys[key])
		} else {
			queries.delete(key)
		}
	})

	history.replaceState(
		{},
		'',
		`${location.pathname}${queries.size > 0 ? `?${queries.toString()}` : ''}`
	)
}

const updateCategories = (data) => {
	data.forEach((batch) => {
		if (
			batch.category &&
			!categories.value.find((category) => category.value === batch.category)
		)
			categories.value.push({
				label: batch.category,
				value: batch.category,
			})
	})
}

watch(currentTab, () => {
	updateBatches()
})

const batchTabs = computed(() => {
	let tabs = [
		{
			label: __('All'),
			value: 'all',
		},
	]

	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	) {
		tabs.push({ label: __('Upcoming'), value: 'upcoming' })
		tabs.push({ label: __('Archived'), value: 'archived' })
		tabs.push({ label: __('Unpublished'), value: 'unpublished' })
	} else if (user.data) {
		tabs.push({ label: __('Enrolled'), value: 'enrolled' })
	}
	return tabs
})

const isStudentEnrolledTab = computed(
	() => is_student.value && currentTab.value === 'enrolled'
)

const showStudentEnrolledLeaderboard = computed(
	() =>
		isStudentEnrolledTab.value &&
		!batches.list.loading &&
		(batches.data?.length || 0) > 0
)

const showStudentNotEnrolled = computed(
	() => isStudentEnrolledTab.value && !batches.data?.length
)

const pageHeading = computed(() => {
	if (showStudentEnrolledLeaderboard.value) return __('Your Batch Leaderboard')
	if (isStudentEnrolledTab.value) return __('Your Batches')
	return __('All Batches')
})

const browseBatches = () => {
	currentTab.value = 'all'
}

const canCreateBatch = () => {
	if (readOnlyMode) return false
	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
		return true
	return false
}

const breadcrumbs = computed(() => [
	{
		label: __('Batches'),
		route: { name: 'Batches' },
	},
])

usePageMeta(() => {
	return {
		title: __('Batches'),
		icon: brand.favicon,
	}
})
</script>
