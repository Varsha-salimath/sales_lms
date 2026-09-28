<template>
	<div
		class="genius-sidebar flex h-screen min-h-full flex-col justify-between transition-all duration-300 ease-in-out overflow-x-hidden"
		:class="sidebarStore.isSidebarCollapsed ? 'w-16' : 'w-64'"
	>
		<div
			class="flex flex-col overflow-x-hidden min-w-0 flex-1 min-h-0 overflow-y-hidden"
			:class="sidebarStore.isSidebarCollapsed ? 'items-center' : ''"
		>
			<UserDropdown :isCollapsed="sidebarStore.isSidebarCollapsed" />
			<div class="flex flex-col gap-0.5" v-if="sidebarSettings.data">
				<div v-for="link in sidebarLinks" class="mx-2 my-0.5">
					<div
						v-if="link.dividerBefore && !sidebarStore.isSidebarCollapsed"
						class="mb-2 mt-1 border-t"
						style="border-color: rgba(255, 255, 255, 0.15)"
					/>
					<div
						v-if="showGroupLabel(link) && !link.collapsible"
						class="genius-sidebar-section-label mb-2 mt-3 flex gap-1.5 border-b px-1 text-base font-medium transition-all duration-300 ease-in-out"
					>
						<span>{{ __(link.label) }}</span>
					</div>
					<div
						v-if="link.collapsible && !sidebarStore.isSidebarCollapsed"
						class="genius-sidebar-section-label mb-2 mt-3 flex cursor-pointer items-center gap-1.5 border-b px-1 text-base font-medium transition-all duration-300 ease-in-out"
						@click="toggleCollapsibleSection(link)"
					>
						<ChevronRight
							class="h-4 w-4 stroke-1.5 text-white transition-all duration-300 ease-in-out"
							:class="{
								'rotate-90': !isCollapsibleSectionCollapsed(link),
								'rtl:rotate-180': isCollapsibleSectionCollapsed(link),
							}"
						/>
						<span>{{ __(link.label) }}</span>
					</div>
					<Tooltip
						v-if="link.collapsible && sidebarStore.isSidebarCollapsed"
						:text="__(link.label)"
					>
						<button
							type="button"
							class="mx-auto mb-2 mt-2 flex h-8 w-8 items-center justify-center rounded-lg text-white transition-colors hover:bg-white/12"
							@click="toggleCollapsibleSection(link)"
						>
							<component
								:is="icons[link.icon]"
								v-if="link.icon && icons[link.icon]"
								class="h-4 w-4 stroke-1.5"
							/>
						</button>
					</Tooltip>
					<nav
						class="space-y-0.5 transition-all duration-300 ease-in-out"
						:class="
							link.collapsible &&
							(isCollapsibleSectionCollapsed(link) ||
								sidebarStore.isSidebarCollapsed)
								? 'hidden'
								: 'block'
						"
					>
						<div v-for="item in link.items" :key="item.label">
							<SidebarLearningMenu
								v-if="item.learningMenu"
								:menuItems="item.menuItems"
								:isCollapsed="sidebarStore.isSidebarCollapsed"
							/>
							<SidebarLink
								v-else
								:link="item"
								:isCollapsed="sidebarStore.isSidebarCollapsed"
							/>
						</div>
					</nav>
				</div>
			</div>
			<div
				v-if="sidebarSettings.data?.web_pages?.length || isModerator"
				class="mt-4"
			>
				<div
					class="flex items-center justify-between pe-2 cursor-pointer min-w-0"
					:class="sidebarStore.isSidebarCollapsed ? 'ps-3' : 'ps-4'"
					@click="toggleWebPages"
				>
					<div
						v-if="!sidebarStore.isSidebarCollapsed"
						class="flex items-center text-white my-1 min-w-0"
					>
						<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
							<ChevronRight
								class="h-4 w-4 stroke-1.5 text-white transition-all duration-300 ease-in-out"
								:class="{
									'rotate-90': sidebarStore.isWebpagesCollapsed,
									'rtl:rotate-180': !sidebarStore.isWebpagesCollapsed,
								}"
							/>
						</span>
						<span class="ms-2">
							{{ __('More') }}
						</span>
					</div>
					<Button
						v-if="isModerator && !readOnlyMode"
						variant="ghost"
						@click="openPageModal()"
					>
						<template #icon>
							<Plus class="h-4 w-4 text-white stroke-1.5" />
						</template>
					</Button>
				</div>
				<div
					v-if="sidebarSettings.data?.web_pages?.length"
					class="flex flex-col transition-all duration-300 ease-in-out"
					:class="!sidebarStore.isWebpagesCollapsed ? 'block' : 'hidden'"
				>
					<div
						v-for="link in sidebarSettings.data.web_pages"
						class="mx-2 my-0.5"
					>
						<SidebarLink
							:link="link"
							:isCollapsed="sidebarStore.isSidebarCollapsed"
							:showControls="isModerator ? true : false"
							@openModal="openPageModal"
							@deletePage="deletePage"
						/>
					</div>
				</div>
			</div>
		</div>
		<div class="m-2 flex flex-col gap-1">
			<div
				v-if="!sidebarStore.isSidebarCollapsed && !isAdminUser"
				class="mb-1 rounded-2xl px-3 py-2.5 text-white"
				style="background: rgba(255, 255, 255, 0.12)"
			>
				<div class="flex items-center justify-between text-xs text-white/75">
					<span>{{ __('Learning streak') }}</span>
					<span class="font-semibold text-white">
						{{ streakInfo.data?.current_streak ?? 0 }}
					</span>
				</div>
				<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-white/20">
					<div
						class="h-1.5 rounded-full"
						style="background: #fcde5a"
						:style="{
							width: `${Math.min(100, (streakInfo.data?.current_streak || 0) * 10)}%`,
						}"
					/>
				</div>
			</div>
			<div
				v-if="readOnlyMode && !sidebarStore.isSidebarCollapsed"
				class="z-10 m-2 rounded-2xl py-2.5 px-3 text-xs leading-5 text-white"
				style="background: rgba(255, 255, 255, 0.12)"
			>
				{{
					__(
						'This site is being updated. You will not be able to make any changes. Full access will be restored shortly.'
					)
				}}
			</div>
			<div
				v-if="
					isStudent && !profileIsComplete && !sidebarStore.isSidebarCollapsed
				"
				class="genius-sidebar-profile-card flex flex-col gap-3 rounded-2xl py-2.5 px-3 text-white"
				style="background: rgba(255, 255, 255, 0.12)"
			>
				<div class="flex flex-col text-p-sm gap-1">
					<div class="inline-flex gap-1">
						<User class="h-4 my-0.5 shrink-0 text-white" />
						<div class="font-medium">
							{{ __('Complete your profile') }}
						</div>
					</div>
					<div class="text-white/70 leading-5">
						{{ __('Highlight what makes you unique and show your skills.') }}
					</div>
				</div>
				<router-link
					:to="{
						name: 'Profile',
						params: {
							username: userResource.data?.username,
						},
					}"
				>
					<Button :label="__('My Profile')" class="w-full">
						<template #prefix>
							<ChevronsRight class="h-4 w-4 stroke-1.5 text-white" />
						</template>
					</Button>
				</router-link>
			</div>
			<Tooltip
				v-if="
					isStudent && !profileIsComplete && sidebarStore.isSidebarCollapsed
				"
				:text="__('Complete your profile')"
			>
				<router-link
					:to="{
						name: 'Profile',
						params: {
							username: userResource.data?.username,
						},
					}"
					class="flex items-center justify-center"
				>
					<User class="size-4 stroke-1.5 text-white cursor-pointer" />
				</router-link>
			</Tooltip>
			<div
				class="flex items-center mt-4"
				:class="
					sidebarStore.isSidebarCollapsed ? 'flex-col space-y-3' : 'flex-row'
				"
			>
				<div
					class="flex items-center flex-1 gap-3"
					:class="sidebarStore.isSidebarCollapsed ? 'flex-col' : 'flex-row'"
				>
					<Tooltip v-if="readOnlyMode && sidebarStore.isSidebarCollapsed">
						<CircleAlert
							class="size-4 stroke-1.5 text-white cursor-pointer"
						/>
						<template #body>
							<div
								class="max-w-[30ch] rounded bg-surface-gray-7 px-2 py-1 text-center text-p-xs text-ink-white shadow-xl"
							>
								{{
									__(
										'This site is being updated. You will not be able to make any changes. Full access will be restored shortly.'
									)
								}}
							</div>
						</template>
					</Tooltip>
				</div>
				<Tooltip
					:text="
						sidebarStore.isSidebarCollapsed ? __('Expand') : __('Collapse')
					"
				>
					<CollapseSidebar
						class="size-4 text-white duration-300 stroke-1.5 ease-in-out cursor-pointer"
						:style="{
							transform:
								isRtl !== sidebarStore.isSidebarCollapsed
									? 'rotateY(180deg)'
									: '',
						}"
						@click="toggleSidebar()"
					/>
				</Tooltip>
			</div>
		</div>
	</div>
	<CommandPalette v-model="settingsStore.isCommandPaletteOpen" />
	<PageModal
		v-model="showPageModal"
		v-model:reloadSidebar="sidebarSettings"
		:page="pageToEdit"
	/>
</template>

<script setup>
import { getSidebarLinks } from '@/utils'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'
import { useSidebar } from '@/stores/sidebar'
import { useSettings } from '@/stores/settings'
import { Button, call, createResource, Tooltip, toast } from 'frappe-ui'
import PageModal from '@/components/Modals/PageModal.vue'
import {
	ref,
	onMounted,
	inject,
	watch,
	onUnmounted,
	computed,
} from 'vue'
import { useRoute } from 'vue-router'
import {
	CircleAlert,
	ChevronRight,
	ChevronsRight,
	Plus,
	User,
} from 'lucide-vue-next'
import * as icons from 'lucide-vue-next'
import UserDropdown from '@/components/Sidebar/UserDropdown.vue'
import CollapseSidebar from '@/components/Icons/CollapseSidebar.vue'
import SidebarLink from '@/components/Sidebar/SidebarLink.vue'
import SidebarLearningMenu from '@/components/Sidebar/SidebarLearningMenu.vue'
import CommandPalette from '@/components/CommandPalette/CommandPalette.vue'

const { user } = sessionStore()
const { userResource } = usersStore()
let sidebarStore = useSidebar()
const route = useRoute()
const socket = inject('$socket')
const unreadCount = ref(0)
const sidebarLinks = ref(null)
const showPageModal = ref(false)
const isModerator = ref(false)
const isInstructor = ref(false)
const isAdminUser = computed(
	() =>
		!!(
			isModerator.value ||
			userResource.data?.is_system_manager ||
			userResource.data?.is_moderator
		)
)
const pageToEdit = ref(null)
const { sidebarSettings, activeTab, isSettingsOpen, programs } = useSettings()
const settingsStore = useSettings()
const readOnlyMode = window.read_only_mode
const isRtl = document.documentElement.dir === 'rtl'

onMounted(() => {
	addKeyboardShortcut()
	updateSidebarLinks()
	socket.on('publish_lms_notifications', (data) => {
		unreadNotifications.reload()
	})
})

const updateSidebarLinksVisibility = () => {
	sidebarSettings.reload(
		{},
		{
			onSuccess(data) {
				Object.keys(data).forEach((key) => {
					if (!parseInt(data[key])) {
						sidebarLinks.value.forEach((link) => {
							link.items = link.items.filter((item) => {
								if (item.learningMenu && item.menuItems) {
									item.menuItems = item.menuItems.filter(
										(entry) =>
											entry.label.toLowerCase().split(' ').join('_') !== key
									)
									return item.menuItems.length > 0
								}
								return (
									item.label.toLowerCase().split(' ').join('_') !== key
								)
							})
						})
					}
				})
			},
		}
	)
}

const addKeyboardShortcut = () => {
	window.addEventListener('keydown', (e) => {
		if (
			e.key === 'k' &&
			(e.ctrlKey || e.metaKey) &&
			!e.target.classList.contains('ProseMirror')
		) {
			toggleCommandPalette()
			e.preventDefault()
		}
	})
}

const toggleCommandPalette = () => {
	settingsStore.isCommandPaletteOpen = !settingsStore.isCommandPaletteOpen
}

const unreadNotifications = createResource({
	cache: 'Unread Notifications Count',
	url: 'frappe.client.get_count',
	makeParams(values) {
		return {
			doctype: 'Notification Log',
			filters: {
				for_user: user,
				read: 0,
			},
		}
	},
	onSuccess(data) {
		unreadCount.value = data
		updateUnreadCount()
	},
	auto: user ? true : false,
})

const streakInfo = createResource({
	url: 'lms.lms.api.get_streak_info',
	auto: !!user,
	cache: ['sidebar-streak', user],
})

const updateUnreadCount = () => {
	sidebarLinks.value?.forEach((link) => {
		link.items.forEach((item) => {
			if (item.label === 'Notifications') {
				item.count = unreadCount.value || 0
			}
		})
	})
}

const openPageModal = (link) => {
	showPageModal.value = true
	pageToEdit.value = link
}

const deletePage = (link) => {
	call('lms.lms.api.delete_documents', {
		doctype: 'LMS Sidebar Item',
		documents: [link.name],
	}).then(() => {
		sidebarSettings.reload()
		toast.success(__('Page deleted successfully'))
	})
}

const toggleSidebar = () => {
	sidebarStore.isSidebarCollapsed = !sidebarStore.isSidebarCollapsed
	localStorage.setItem(
		'isSidebarCollapsed',
		JSON.stringify(sidebarStore.isSidebarCollapsed)
	)
}

const toggleWebPages = () => {
	sidebarStore.isWebpagesCollapsed = !sidebarStore.isWebpagesCollapsed
	localStorage.setItem(
		'isWebpagesCollapsed',
		JSON.stringify(sidebarStore.isWebpagesCollapsed)
	)
}

const togglePracticeHub = () => {
	sidebarStore.isPracticeHubCollapsed = !sidebarStore.isPracticeHubCollapsed
	localStorage.setItem(
		'isPracticeHubCollapsed',
		JSON.stringify(sidebarStore.isPracticeHubCollapsed)
	)
}

const toggleLearning = () => {
	sidebarStore.isLearningCollapsed = !sidebarStore.isLearningCollapsed
	localStorage.setItem(
		'isLearningCollapsed',
		JSON.stringify(sidebarStore.isLearningCollapsed)
	)
}

function isCollapsibleSectionCollapsed(link) {
	const key = link?.collapsibleKey || 'practiceHub'
	if (key === 'learning') {
		return sidebarStore.isLearningCollapsed
	}
	return sidebarStore.isPracticeHubCollapsed
}

function toggleCollapsibleSection(link) {
	const key = link?.collapsibleKey || 'practiceHub'
	if (key === 'learning') {
		toggleLearning()
		return
	}
	togglePracticeHub()
}

watch(userResource, async () => {
	await userResource.promise
	if (userResource.data) {
		isModerator.value = userResource.data.is_moderator
		isInstructor.value = userResource.data.is_instructor
		await programs.reload()
	}
	updateSidebarLinks()
})

watch(settingsStore.settings, () => {
	updateSidebarLinks()
})

const showGroupLabel = (link) => {
	if (link.hideLabel || sidebarStore.isSidebarCollapsed) return false
	return true
}

const updateSidebarLinks = () => {
	sidebarLinks.value = getSidebarLinks()
	updateSidebarLinksVisibility()
	updateUnreadCount()
}

const isStudent = computed(() => {
	return userResource.data?.is_student
})

const profileIsComplete = computed(() => {
	return (
		userResource.data?.user_image &&
		userResource.data?.headline &&
		userResource.data?.bio
	)
})

onUnmounted(() => {
	socket.off('publish_lms_notifications')
})
</script>

<style scoped>
/* Infinity Learn rail: transparent on the blue chrome, white pill for the active item. */
.genius-sidebar {
	background: transparent !important;
	overflow-x: hidden !important;
	color: #f2f2f2;
}

.genius-sidebar-section-label {
	color: rgba(255, 255, 255, 0.72) !important;
	border-color: rgba(255, 255, 255, 0.16) !important;
	font-size: 0.75rem !important;
	font-weight: 600 !important;
	letter-spacing: 0.08em;
	text-transform: uppercase;
}

.genius-sidebar :deep(.sidebar-nav-link) {
	height: 2.5rem;
	border-radius: 999px;
	color: #f2f2f2 !important;
	font-weight: 500;
}

.genius-sidebar :deep(.sidebar-nav-link .text-sm) {
	font-size: 0.875rem;
}

.genius-sidebar :deep(.sidebar-nav-link svg),
.genius-sidebar :deep(.sidebar-nav-link__icon) {
	color: #f2f2f2 !important;
	stroke: #f2f2f2 !important;
}

.genius-sidebar :deep(.sidebar-nav-link:hover) {
	background-color: rgba(255, 255, 255, 0.14) !important;
	color: #ffffff !important;
}

.genius-sidebar :deep(.sidebar-nav-link--active),
.genius-sidebar :deep(.sidebar-nav-link--active:hover) {
	background-color: #ffffff !important;
	color: #0062cc !important;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.16) !important;
}

.genius-sidebar :deep(.sidebar-nav-link--active svg),
.genius-sidebar :deep(.sidebar-nav-link--active .sidebar-nav-link__icon) {
	color: #0062cc !important;
	stroke: #0062cc !important;
}

.genius-sidebar-profile-card :deep(button) {
	background-color: #ffffff !important;
	color: #0062cc !important;
	border-radius: 999px !important;
}
</style>
