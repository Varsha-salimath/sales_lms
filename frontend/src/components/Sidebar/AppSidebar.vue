<template>
	<div
		class="genius-sidebar flex h-screen min-h-full flex-col justify-between transition-all duration-300 ease-in-out border-e overflow-x-hidden"
		style="background: #0075ff"
		:class="sidebarStore.isSidebarCollapsed ? 'w-14' : 'w-64'"
	>
		<div
			class="flex flex-col overflow-y-auto overflow-x-hidden min-w-0"
			:class="sidebarStore.isSidebarCollapsed ? 'items-center' : ''"
		>
			<UserDropdown :isCollapsed="sidebarStore.isSidebarCollapsed" />
			<div class="flex flex-col" v-if="sidebarSettings.data">
				<div v-for="link in sidebarLinks" class="mx-2 my-2.5">
					<div
						v-if="!link.hideLabel"
						class="genius-sidebar-section-label mb-2 mt-3 flex cursor-pointer gap-1.5 border-b px-1 text-base font-medium transition-all duration-300 ease-in-out"
					>
						<span>{{ __(link.label) }}</span>
					</div>
					<nav class="space-y-1">
						<div v-for="item in link.items">
							<SidebarLink
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
				style="background: #0066ee"
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
						style="background: #ffd000"
						:style="{
							width: `${Math.min(100, (streakInfo.data?.current_streak || 0) * 10)}%`,
						}"
					/>
				</div>
			</div>
			<div
				v-if="readOnlyMode && !sidebarStore.isSidebarCollapsed"
				class="z-10 m-2 rounded-md py-2.5 px-3 text-xs leading-5 text-white"
				style="background: #0066ee"
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
				class="genius-sidebar-profile-card flex flex-col gap-3 rounded-md py-2.5 px-3 text-white shadow-sm"
				style="background: #0066ee"
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
			<TrialBanner
				v-if="
					userResource.data?.is_system_manager && userResource.data?.is_fc_site
				"
				:isSidebarCollapsed="sidebarStore.isSidebarCollapsed"
			/>
			<div class="genius-sidebar-getting-started">
				<GettingStartedBanner
					v-if="showOnboarding && !isOnboardingStepsCompleted && !isAdminUser"
					:isSidebarCollapsed="sidebarStore.isSidebarCollapsed"
					appName="learning"
				/>
			</div>

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
					<Tooltip
						v-if="showAppointmentIcon"
						:text="__('Book a free onboarding session with the Frappe team')"
					>
						<Phone
							class="size-4 stroke-1.5 text-white cursor-pointer"
							@click="redirectToAppointmentScreen()"
						/>
					</Tooltip>
					<Tooltip v-if="showOnboarding" :text="__('Help')">
						<CircleHelp
							class="size-4 stroke-1.5 text-white cursor-pointer"
							@click="
								() => {
									showHelpModal = minimize ? true : !showHelpModal
									minimize = !showHelpModal
								}
							"
						/>
					</Tooltip>
					<Tooltip :text="__('Infinity Learn Sales CRT')">
						<Zap
							class="size-4 stroke-1.5 text-white cursor-pointer"
							@click="redirectToWebsite()"
						/>
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
		<HelpModal
			data-testid="onboarding-help-modal"
			v-if="showOnboarding && showHelpModal"
			v-model="showHelpModal"
			v-model:articles="articles"
			appName="learning"
			title="Infinity Learn Sales CRT"
			:logo="LMSLogo"
			:afterSkip="(step) => capture('onboarding_step_skipped_' + step)"
			:afterSkipAll="() => capture('onboarding_steps_skipped')"
			:afterReset="(step) => capture('onboarding_step_reset_' + step)"
			:afterResetAll="() => capture('onboarding_steps_reset')"
			docsLink=""
		/>
		<IntermediateStepModal
			v-model="showIntermediateModal"
			:currentStep="currentStep"
		/>
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
import LMSLogo from '@/components/Icons/LMSLogo.vue'
import { useRouter } from 'vue-router'
import {
	ref,
	onMounted,
	inject,
	watch,
	reactive,
	markRaw,
	h,
	onUnmounted,
	computed,
} from 'vue'
import {
	BookOpen,
	CircleAlert,
	ChevronRight,
	ChevronsRight,
	CircleHelp,
	FolderTree,
	FileText,
	Phone,
	Plus,
	User,
	UserPlus,
	Users,
	BookText,
	Zap,
} from 'lucide-vue-next'
import {
	TrialBanner,
	HelpModal,
	GettingStartedBanner,
	useOnboarding,
	showHelpModal,
	minimize,
	IntermediateStepModal,
	useTelemetry,
} from 'frappe-ui/frappe'
import InviteIcon from '@/components/Icons/InviteIcon.vue'
import UserDropdown from '@/components/Sidebar/UserDropdown.vue'
import CollapseSidebar from '@/components/Icons/CollapseSidebar.vue'
import SidebarLink from '@/components/Sidebar/SidebarLink.vue'
import CommandPalette from '@/components/CommandPalette/CommandPalette.vue'

const { user } = sessionStore()
const { userResource } = usersStore()
let sidebarStore = useSidebar()
const socket = inject('$socket')
const unreadCount = ref(0)
const sidebarLinks = ref(null)
const { capture } = useTelemetry()
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
const showOnboarding = ref(false)
const showIntermediateModal = ref(false)
const currentStep = ref({})
const router = useRouter()
let onboardingDetails
let isOnboardingStepsCompleted = false
const readOnlyMode = window.read_only_mode
const isRtl = document.documentElement.dir === 'rtl'
const iconProps = {
	strokeWidth: 1.5,
	width: 16,
	height: 16,
}

onMounted(() => {
	setUpOnboarding()
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
							link.items = link.items.filter(
								(item) => item.label.toLowerCase().split(' ').join('_') !== key
							)
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

const getFirstCourse = async () => {
	let firstCourse = localStorage.getItem('firstCourse')
	if (firstCourse) return firstCourse
	return await call('lms.lms.onboarding.get_first_course')
}

const getFirstBatch = async () => {
	let firstBatch = localStorage.getItem('firstBatch')
	if (firstBatch) return firstBatch
	return await call('lms.lms.onboarding.get_first_batch')
}

const steps = reactive([
	{
		name: 'create_first_course',
		title: __('Create your first course'),
		icon: markRaw(h(BookOpen, iconProps)),
		completed: false,
		onClick: () => {
			minimize.value = true
			router.push({
				name: 'Courses',
			})
		},
	},
	{
		name: 'create_first_chapter',
		title: __('Add your first chapter'),
		icon: markRaw(h(FolderTree, iconProps)),
		completed: false,
		dependsOn: 'create_first_course',
		onClick: async () => {
			minimize.value = true
			let course = await getFirstCourse()
			if (course) {
				router.push({
					name: 'CourseDetail',
					params: { courseName: course },
					hash: '#settings',
				})
			} else {
				router.push({ name: 'Courses', query: { newCourse: '1' } })
			}
		},
	},
	{
		name: 'create_first_lesson',
		title: __('Add your first lesson'),
		icon: markRaw(h(FileText, iconProps)),
		completed: false,
		dependsOn: 'create_first_chapter',
		onClick: async () => {
			minimize.value = true
			let course = await getFirstCourse()
			if (course) {
				router.push({
					name: 'CourseDetail',
					params: { courseName: course },
					hash: '#settings',
				})
			} else {
				router.push({ name: 'Courses', query: { newCourse: '1' } })
			}
		},
	},
	{
		name: 'create_first_quiz',
		title: __('Create your first quiz'),
		icon: markRaw(h(CircleHelp, iconProps)),
		completed: false,
		dependsOn: 'create_first_course',
		onClick: () => {
			minimize.value = true
			router.push({ name: 'Quizzes' })
		},
	},
	{
		name: 'invite_students',
		title: __('Invite your team and students'),
		icon: markRaw(h(InviteIcon, iconProps)),
		completed: false,
		onClick: () => {
			minimize.value = true
			activeTab.value = 'Members'
			isSettingsOpen.value = true
		},
	},
	{
		name: 'create_first_batch',
		title: __('Create your first batch'),
		icon: markRaw(h(Users, iconProps)),
		completed: false,
		onClick: () => {
			minimize.value = true
			router.push({ name: 'Batches' })
		},
	},
	{
		name: 'add_batch_student',
		title: __('Add students to your batch'),
		icon: markRaw(h(UserPlus, iconProps)),
		completed: false,
		dependsOn: 'create_first_batch',
		onClick: async () => {
			minimize.value = true
			let batch = await getFirstBatch()
			if (batch) {
				router.push({
					name: 'Batch',
					params: {
						batchName: batch,
					},
				})
			} else {
				router.push({ name: 'Batch' })
			}
		},
	},
	{
		name: 'add_batch_course',
		title: __('Add courses to your batch'),
		icon: markRaw(h(BookText, iconProps)),
		completed: false,
		dependsOn: 'create_first_batch',
		onClick: async () => {
			minimize.value = true
			let batch = await getFirstBatch()
			if (batch) {
				router.push({
					name: 'Batch',
					params: {
						batchName: batch,
					},
					hash: '#courses',
				})
			} else {
				router.push({ name: 'Batch' })
			}
		},
	},
])

const articles = ref([
	{
		title: __('Introduction'),
		opened: false,
		subArticles: [
			{ name: 'introduction', title: __('Introduction') },
			{ name: 'setting-up', title: __('Setting up') },
		],
	},
	{
		title: __('Creating a course'),
		opened: false,
		subArticles: [
			{ name: 'create-a-course', title: __('Create a course') },
			{ name: 'add-a-chapter', title: __('Add a chapter') },
			{ name: 'add-a-lesson', title: __('Add a lesson') },
		],
	},
	{
		title: __('Creating a batch'),
		opened: false,
		subArticles: [
			{ name: 'create-a-batch', title: __('Create a batch') },
			{ name: 'create-a-live-class', title: __('Create a live class') },
		],
	},
	{
		title: __('Learning Paths'),
		opened: false,
		subArticles: [{ name: 'add-a-program', title: __('Add a program') }],
	},
	{
		title: __('Assessments'),
		opened: false,
		subArticles: [
			{ name: 'quizzes', title: __('Quizzes') },
			{ name: 'assignments', title: __('Assignments') },
		],
	},
	{
		title: __('Certification'),
		opened: false,
		subArticles: [
			{ name: 'issue-a-certificate', title: __('Issue a Certificate') },
			{
				name: 'custom-certificate-templates',
				title: __('Custom Certificate Templates'),
			},
		],
	},
	{
		title: __('Monetization'),
		opened: false,
		subArticles: [
			{
				name: 'setting-up-payment-gateway',
				title: __('Setting up payment gateway'),
			},
		],
	},
	{
		title: __('Settings'),
		opened: false,
		subArticles: [{ name: 'roles', title: __('Roles') }],
	},
])

const setUpOnboarding = () => {
	if (userResource.data?.is_system_manager) {
		onboardingDetails = useOnboarding('learning')
		onboardingDetails.setUp(steps)
		isOnboardingStepsCompleted = onboardingDetails.isOnboardingStepsCompleted
		showOnboarding.value = true
	}
}

watch(userResource, async () => {
	await userResource.promise
	if (userResource.data) {
		isModerator.value = userResource.data.is_moderator
		isInstructor.value = userResource.data.is_instructor
		await programs.reload()
		setUpOnboarding()
	}
	updateSidebarLinks()
})

watch(settingsStore.settings, () => {
	updateSidebarLinks()
})

const updateSidebarLinks = () => {
	sidebarLinks.value = getSidebarLinks()
	updateSidebarLinksVisibility()
	updateUnreadCount()
}

const redirectToWebsite = () => {
	window.open('https://infinitylearn.com', '_blank')
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

const showAppointmentIcon = computed(() => {
	let isTrialPlan = userResource.data?.site_info?.plan?.is_trial_plan
	let trialEndDate = calculateTrialEndDays(
		userResource.data?.site_info?.trial_end_date
	)
	return (
		userResource.data?.is_system_manager &&
		userResource.data?.is_fc_site &&
		isTrialPlan &&
		trialEndDate > 0
	)
})

const calculateTrialEndDays = (trialEndDate) => {
	if (!trialEndDate) return 0

	trialEndDate = new Date(trialEndDate)
	const today = new Date()
	const diffTime = trialEndDate - today
	const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
	return diffDays
}

const redirectToAppointmentScreen = () => {
	window.open(
		'https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ0c7Z3XIpW1WgbeIuktSaoX6qudoYuSdRbIlJty5TW7p4IZaOk5viHQGwTNi6HpNVqzOZOTHcle',
		'_blank'
	)
}

onUnmounted(() => {
	socket.off('publish_lms_notifications')
})
</script>

<style scoped>
.genius-sidebar {
	background-color: #0075ff !important;
	border-color: #0066ee !important;
	overflow-x: hidden !important;
}

.genius-sidebar-section-label {
	color: #ffffff !important;
	border-color: rgba(255, 255, 255, 0.15) !important;
}

.genius-sidebar :deep(.sidebar-nav-link) {
	color: #ffffff !important;
}

.genius-sidebar :deep(.sidebar-nav-link svg),
.genius-sidebar :deep(.sidebar-nav-link__icon) {
	color: #ffffff !important;
	stroke: #ffffff !important;
}

.genius-sidebar :deep(.sidebar-nav-link:hover) {
	background-color: rgba(255, 255, 255, 0.12) !important;
	color: #ffffff !important;
}

.genius-sidebar :deep(.sidebar-nav-link--active),
.genius-sidebar :deep(.sidebar-nav-link--active:hover) {
	background-color: #ffffff !important;
	color: #0075ff !important;
	box-shadow: inset 3px 0 0 #ffd000;
	border-radius: 999px;
}

.genius-sidebar :deep(.sidebar-nav-link--active svg),
.genius-sidebar :deep(.sidebar-nav-link--active .sidebar-nav-link__icon) {
	color: #0075ff !important;
	stroke: #0075ff !important;
}

.genius-sidebar-getting-started :deep(.bg-surface-modal) {
	background: rgba(255, 255, 255, 0.1) !important;
	color: #ffffff !important;
}

.genius-sidebar-getting-started :deep(.text-ink-gray-9),
.genius-sidebar-getting-started :deep(.text-ink-gray-7),
.genius-sidebar-getting-started :deep(.font-medium),
.genius-sidebar-getting-started :deep(.text-p-sm) {
	color: #ffffff !important;
}

.genius-sidebar-getting-started :deep(svg) {
	color: #ffffff !important;
}

.genius-sidebar-getting-started :deep(button) {
	background-color: #ffd000 !important;
	color: #12263f !important;
	border-radius: 12px !important;
}

.genius-sidebar-profile-card :deep(button) {
	background-color: #ffd000 !important;
	color: #12263f !important;
	border-radius: 12px !important;
}
</style>
