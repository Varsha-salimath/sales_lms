<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div v-if="!readOnlyMode" class="flex items-center gap-x-2">
			<Button variant="subtle" @click="openNewFolderDialog(null)">
				<template #prefix>
					<FolderPlus class="w-4 h-4" />
				</template>
				{{ __('New Folder') }}
			</Button>
			<Button variant="solid" @click="showForm = true">
				<template #prefix>
					<Plus class="w-4 h-4" />
				</template>
				{{ __('Create') }}
			</Button>
		</div>
	</header>
	<div class="flex h-[calc(100vh-52px)]">
		<div class="w-56 shrink-0 border-e bg-surface-white overflow-hidden">
			<QuizFolderTree
				:folders="folderTree.data?.folders || []"
				:selectedFolder="selectedFolder"
				:totalCount="folderTree.data?.total_count || 0"
				:unfiledCount="folderTree.data?.unfiled_count || 0"
				:readOnlyMode="readOnlyMode"
				@select="selectFolder"
				@createFolder="openNewFolderDialog"
				@renameFolder="openRenameFolderDialog"
				@deleteFolder="confirmDeleteFolder"
			/>
		</div>

		<div class="flex-1 flex flex-col overflow-hidden">
			<div class="pt-5 flex-1 flex flex-col overflow-hidden">
				<div class="flex items-center justify-between mb-5 mx-5">
					<div class="text-lg font-semibold text-ink-gray-9">
						{{ folderTitle }}
						<span class="text-ink-gray-5 font-normal text-base ml-1">
							({{ quizzes.data?.length || 0 }})
						</span>
					</div>
					<FormControl v-model="search" type="text" placeholder="Search">
						<template #prefix>
							<FeatherIcon name="search" class="size-4 text-ink-gray-5" />
						</template>
					</FormControl>
				</div>
				<ListView
					v-if="quizzes.data?.length"
					:columns="quizColumns"
					:rows="quizzes.data"
					row-key="name"
					:options="{ showTooltip: false, selectable: true }"
					class="flex-1 overflow-auto px-5"
				>
					<ListHeader
						class="mb-2 grid items-center rounded bg-surface-white border-b rounded-none p-2"
					>
						<ListHeaderItem :item="item" v-for="item in quizColumns">
							<template #prefix="{ item }">
								<FeatherIcon :name="item.icon?.toString()" class="h-4 w-4" />
							</template>
						</ListHeaderItem>
					</ListHeader>
					<ListRows>
						<router-link
							v-for="row in quizzes.data"
							:to="{
								name: 'QuizForm',
								params: {
									quizID: row.name,
								},
							}"
						>
							<ListRow :row="row" class="hover:bg-surface-gray-2">
								<template #default="{ column, item }">
									<ListRowItem :item="row[column.key]" :align="column.align">
										<div v-if="column.key == 'show_answers'">
											<FormControl
												type="checkbox"
												v-model="row[column.key]"
												:disabled="true"
											/>
										</div>
										<div
											v-else-if="column.key == 'modified'"
											class="text-sm text-ink-gray-5"
										>
											{{ row[column.key] }}
										</div>
										<div v-else>
											{{ row[column.key] }}
										</div>
									</ListRowItem>
								</template>
							</ListRow>
						</router-link>
					</ListRows>
					<ListSelectBanner class="bottom-50">
						<template #actions="{ unselectAll, selections }">
							<div class="flex gap-2">
								<Button
									variant="ghost"
									@click="openMoveDialog(selections)"
								>
									<FolderInput class="h-4 w-4 stroke-1.5" />
								</Button>
								<Button
									variant="ghost"
									@click="deleteQuiz(selections, unselectAll)"
								>
									<FeatherIcon name="trash-2" class="h-4 w-4 stroke-1.5" />
								</Button>
							</div>
						</template>
					</ListSelectBanner>
				</ListView>
				<div v-else class="flex-1 px-5">
					<EmptyStateLayout name="Quizzes" />
				</div>
				<div class="flex items-center justify-end gap-x-3 pt-3 border-t px-5 pb-3">
					<Button v-if="quizzes.hasNextPage" @click="quizzes.next()">
						{{ __('Load More') }}
					</Button>
					<div v-if="quizzes.hasNextPage" class="h-8 border-s"></div>
					<div class="text-ink-gray-5">
						{{ quizzes.data?.length }} {{ __('of') }} {{ totalQuizzes.data }}
					</div>
				</div>
			</div>
		</div>
	</div>

	<Dialog
		v-model="showForm"
		:options="{
			title: __('Create a Quiz'),
			size: 'sm',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick({ close }) {
						insertQuiz(close)
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="title"
					:label="__('Title')"
					type="text"
					autocomplete="off"
					@keydown.enter="insertQuiz(() => (showForm = false))"
				/>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model="showFolderDialog"
		:options="{
			title: folderDialogMode === 'rename' ? __('Rename Folder') : __('New Folder'),
			size: 'sm',
			actions: [
				{
					label: folderDialogMode === 'rename' ? __('Rename') : __('Create'),
					variant: 'solid',
					onClick({ close }) {
						folderDialogMode === 'rename' ? renameFolder(close) : createFolder(close)
					},
				},
			],
		}"
	>
		<template #body-content>
			<FormControl
				v-model="folderName"
				:label="__('Folder Name')"
				type="text"
				autocomplete="off"
				@keydown.enter="folderDialogMode === 'rename' ? renameFolder(() => (showFolderDialog = false)) : createFolder(() => (showFolderDialog = false))"
			/>
		</template>
	</Dialog>

	<MoveQuizToFolder
		v-model="showMoveDialog"
		:quizzes="quizzesToMove"
		:folders="folderTree.data?.folders || []"
		@moved="onQuizzesMoved"
	/>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	createListResource,
	createResource,
	Dialog,
	FeatherIcon,
	FormControl,
	ListView,
	ListRows,
	ListRow,
	ListRowItem,
	ListHeader,
	ListHeaderItem,
	ListSelectBanner,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { useRouter, useRoute } from 'vue-router'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { Plus, FolderPlus, FolderInput } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { sanitizeHTML } from '@/utils'
import { useTelemetry } from 'frappe-ui/frappe'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import QuizFolderTree from '@/components/QuizFolderTree.vue'
import MoveQuizToFolder from '@/components/Modals/MoveQuizToFolder.vue'

const { brand } = sessionStore()
const { capture } = useTelemetry()
const user = inject('$user')
const dayjs = inject('$dayjs')
const router = useRouter()
const route = useRoute()
const search = ref('')
const readOnlyMode = window.read_only_mode
const quizFilters = ref({})
const showForm = ref(false)
const title = ref('')

const selectedFolder = ref(null)
const showFolderDialog = ref(false)
const folderDialogMode = ref('create')
const folderName = ref('')
const folderDialogParent = ref(null)
const folderToRename = ref(null)
const showMoveDialog = ref(false)
const quizzesToMove = ref([])
const moveUnselectAll = ref(null)

onMounted(() => {
	if (
		!user.data?.is_moderator &&
		!user.data?.is_instructor &&
		!user.data?.is_evaluator
	) {
		router.push({ name: 'Courses' })
	}
	if (route.query.new === 'true') {
		showForm.value = true
	}
})

const folderTree = createResource({
	url: 'lms.lms.api.get_folder_tree',
	auto: true,
	cache: ['quiz_folder_tree'],
})

const folderTitle = computed(() => {
	if (selectedFolder.value === null) return __('All Quizzes')
	if (selectedFolder.value === '__unfiled__') return __('Unfiled')
	const found = findFolder(folderTree.data?.folders || [], selectedFolder.value)
	return found?.title || __('Quizzes')
})

function findFolder(folders, name) {
	for (const f of folders) {
		if (f.name === name) return f
		if (f.children?.length) {
			const found = findFolder(f.children, name)
			if (found) return found
		}
	}
	return null
}

function selectFolder(folder) {
	selectedFolder.value = folder
	updateQuizFilters()
}

function updateQuizFilters() {
	const filters = {}
	if (search.value) {
		filters.title = ['like', `%${search.value}%`]
	}
	if (selectedFolder.value === '__unfiled__') {
		filters.quiz_folder = ['is', 'not set']
	} else if (selectedFolder.value !== null) {
		filters.quiz_folder = selectedFolder.value
	}
	quizFilters.value = filters
	quizzes.update({ filters })
	quizzes.reload()
	totalQuizzes.update({
		params: { doctype: 'LMS Quiz', filters },
	})
	totalQuizzes.reload()
}

watch(search, () => {
	updateQuizFilters()
})

const quizzes = createListResource({
	doctype: 'LMS Quiz',
	filters: quizFilters,
	fields: [
		'name',
		'title',
		'passing_percentage',
		'total_marks',
		'show_answers',
		'max_attempts',
		'modified',
		'quiz_folder',
	],
	auto: true,
	cache: ['quizzes', user.data?.name],
	orderBy: 'modified desc',
	transform(data) {
		return data.map((quiz) => {
			return {
				...quiz,
				modified: dayjs(quiz.modified).format('DD MMM YYYY'),
			}
		})
	},
})

const totalQuizzes = createResource({
	url: 'frappe.client.get_count',
	params: {
		doctype: 'LMS Quiz',
		filters: quizFilters.value,
	},
	auto: true,
	cache: ['quizzes_count', user.data?.name],
	onError(err) {
		toast.error(err.messages?.[0] || err)
		console.error(err)
	},
})

const validateTitle = () => {
	title.value = sanitizeHTML(title.value.trim())
}

const insertQuiz = (close) => {
	validateTitle()
	const doc = { title: title.value }
	if (selectedFolder.value && selectedFolder.value !== '__unfiled__') {
		doc.quiz_folder = selectedFolder.value
	}
	quizzes.insert.submit(doc, {
		onSuccess(data) {
			toast.success(__('Quiz created successfully'))
			close()
			title.value = ''
			capture('quiz_created')
			folderTree.reload()
			router.push({
				name: 'QuizForm',
				params: { quizID: data.name },
			})
		},
		onError(error) {
			toast.error(`${__('Error creating quiz:')} ${error.message}`)
		},
	})
}

const deleteQuiz = async (selections, unselectAll) => {
	const quizNames = Array.from(selections)
	if (!quizNames.length) return

	let failed = 0
	for (const quizName of quizNames) {
		try {
			await quizzes.delete.submit(quizName)
		} catch (err) {
			failed += 1
			const msg =
				err?.messages?.[0] ||
				err?.message ||
				__('Cannot delete this quiz because it is linked to other records.')
			toast.error(msg)
			console.error(err)
		}
	}

	unselectAll()
	folderTree.reload()

	if (!failed) {
		toast.success(__('Quizzes deleted successfully'))
	} else if (failed === quizNames.length) {
		toast.error(__('Could not delete selected quizzes'))
	} else {
		toast.error(__('Some quizzes could not be deleted'))
	}
}

function openNewFolderDialog(parentFolder) {
	folderDialogMode.value = 'create'
	folderName.value = ''
	folderDialogParent.value = parentFolder
	showFolderDialog.value = true
}

function openRenameFolderDialog(folder) {
	folderDialogMode.value = 'rename'
	folderName.value = folder.title
	folderToRename.value = folder
	showFolderDialog.value = true
}

const createFolderResource = createResource({
	url: 'frappe.client.insert',
})

const renameFolderResource = createResource({
	url: 'lms.lms.api.rename_quiz_folder',
})

function createFolder(close) {
	const name = folderName.value.trim()
	if (!name) {
		toast.error(__('Folder name is required'))
		return
	}
	createFolderResource.submit(
		{
			doc: {
				doctype: 'LMS Quiz Folder',
				title: name,
				parent_quiz_folder: folderDialogParent.value || null,
			},
		},
		{
			onSuccess() {
				toast.success(__('Folder created'))
				folderTree.reload()
				close()
			},
			onError(err) {
				toast.error(err.messages?.[0] || __('Error creating folder'))
			},
		}
	)
}

function renameFolder(close) {
	const name = folderName.value.trim()
	if (!name) {
		toast.error(__('Folder name is required'))
		return
	}
	renameFolderResource.submit(
		{ folder: folderToRename.value.name, new_title: name },
		{
			onSuccess() {
				toast.success(__('Folder renamed'))
				folderTree.reload()
				close()
			},
			onError(err) {
				toast.error(err.messages?.[0] || __('Error renaming folder'))
			},
		}
	)
}

const deleteFolderResource = createResource({
	url: 'frappe.client.delete',
})

function confirmDeleteFolder(folder) {
	deleteFolderResource.submit(
		{ doctype: 'LMS Quiz Folder', name: folder.name },
		{
			onSuccess() {
				toast.success(__('Folder deleted'))
				if (selectedFolder.value === folder.name) {
					selectedFolder.value = null
					updateQuizFilters()
				}
				folderTree.reload()
			},
			onError(err) {
				toast.error(err.messages?.[0] || __('Cannot delete folder'))
			},
		}
	)
}

function openMoveDialog(selections) {
	quizzesToMove.value = Array.from(selections)
	showMoveDialog.value = true
}

function onQuizzesMoved() {
	quizzes.reload()
	folderTree.reload()
}

const quizColumns = computed(() => {
	return [
		{
			label: __('Title'),
			key: 'title',
			width: 2,
			icon: 'file-text',
		},
		{
			label: __('Total Marks'),
			key: 'total_marks',
			width: 0.5,
			align: 'center',
			icon: 'hash',
		},
		{
			label: __('Passing Percentage'),
			key: 'passing_percentage',
			width: 1,
			align: 'center',
			icon: 'percent',
		},
		{
			label: __('Max Attempts'),
			key: 'max_attempts',
			width: 0.5,
			align: 'center',
			icon: 'repeat',
		},
		{
			label: __('Show Answers'),
			key: 'show_answers',
			width: 0.5,
			align: 'center',
			icon: 'eye',
		},
		{
			label: __('Updated On'),
			key: 'modified',
			width: 1,
			align: 'right',
			icon: 'clock',
		},
	]
})

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Quizzes'),
			route: {
				name: 'Quizzes',
			},
		},
	]
})

usePageMeta(() => {
	return {
		title: __('Quizzes'),
		icon: brand.favicon,
	}
})
</script>
