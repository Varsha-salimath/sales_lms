<template>
	<div class="p-2 min-w-0" style="background: #0075ff">
		<Dropdown :options="userDropdownOptions">
			<template v-slot="{ open, close }">
				<button
					class="flex h-12 py-1.5 items-center rounded-2xl duration-300 ease-in-out min-w-0 overflow-hidden"
					:class="
						isCollapsed
							? 'px-0 w-auto justify-center'
							: open
							? 'bg-white/[0.14] shadow-sm px-2 w-full'
							: 'hover:bg-white/[0.12] px-2 w-full'
					"
				>
					<img
						:src="defaultLogo"
						alt="Sales LMS"
						class="flex-shrink-0 object-contain"
						:class="isCollapsed ? 'h-9 w-9' : 'h-10 w-auto max-w-[8.5rem]'"
					/>
					<div
						class="flex min-w-0 flex-1 flex-col text-start duration-300 ease-in-out"
						:class="
							isCollapsed
								? 'opacity-0 ms-0 w-0 overflow-hidden'
								: 'opacity-100 ms-2'
						"
					>
						<div class="text-sm font-semibold text-white leading-none truncate">
							Sales LMS
						</div>
						<div
							v-if="userResource.data"
							class="mt-1 text-xs text-white/85 leading-none truncate"
						>
							{{ convertToTitleCase(userResource.data?.full_name) }}
						</div>
					</div>
					<div
						class="duration-300 ease-in-out flex-shrink-0"
						:class="
							isCollapsed
								? 'opacity-0 ms-0 w-0 overflow-hidden'
								: 'opacity-100 ms-1.5'
						"
					>
						<ChevronDown class="h-4 w-4 text-white" />
					</div>
				</button>
			</template>
		</Dropdown>
	</div>
	<SettingsModal
		v-if="userResource.data?.is_moderator"
		v-model="showSettingsModal"
	/>
</template>

<script setup>
import { sessionStore } from '@/stores/session'
import { call, Dropdown, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { convertToTitleCase } from '@/utils'
import { applyTheme, toggleTheme, theme } from '@/utils/theme'
import { usersStore } from '@/stores/user'
import { useSettings } from '@/stores/settings'
import { markRaw, watch, ref, onMounted, computed } from 'vue'
import { createDialog } from '@/utils/dialogs'
import Apps from '@/components/Sidebar/Apps.vue'
import Configuration from '@/components/Sidebar/Configuration.vue'
import SettingsModal from '@/components/Settings/Settings.vue'
import defaultLogo from '@/assets/il-logo-white.svg'
import {
	ChevronDown,
	LayoutGrid,
	LogIn,
	LogOut,
	Moon,
	User,
	Settings,
	Sun,
	Trash2,
} from 'lucide-vue-next'

const router = useRouter()
const { logout, branding } = sessionStore()
let { userResource } = usersStore()
const settingsStore = useSettings()
let { isLoggedIn } = sessionStore()
const showSettingsModal = ref(false)
const $dialog = createDialog

const props = defineProps({
	isCollapsed: {
		type: Boolean,
		default: false,
	},
})

onMounted(() => {
	if (['light', 'dark'].includes(theme.value)) {
		applyTheme(theme.value)
	}
})

watch(
	() => settingsStore.isSettingsOpen,
	(value) => {
		showSettingsModal.value = value
	}
)

const userDropdownOptions = computed(() => {
	return [
		{
			group: '',
			items: [
				{
					icon: User,
					label: 'My Profile',
					onClick: () => {
						const username =
							userResource.data?.username ||
							userResource.data?.email ||
							userResource.data?.name
						if (!username) {
							toast.error(__('Profile is not available yet'))
							return
						}
						router.push(`/user/${encodeURIComponent(username)}`)
					},
					condition: () => {
						return isLoggedIn
					},
				},
				{
					icon: theme.value === 'light' ? Moon : Sun,
					label: 'Toggle Theme',
					onClick: () => {
						toggleTheme()
					},
				},
				{
					icon: LayoutGrid,
					label: 'Desk',
					onClick: () => {
						window.location.href = '/desk'
					},
					condition: () => canOpenDesk(),
				},
				{
					component: markRaw(Apps),
					condition: () => canOpenDesk(),
				},
				{
					icon: Settings,
					label: 'Settings',
					onClick: () => {
						settingsStore.isSettingsOpen = true
					},
					condition: () => {
						return userResource.data?.is_moderator
					},
				},
				{
					component: markRaw(Configuration),
					condition: () => {
						return userResource.data?.is_moderator
					},
				},
				{
					label: 'Clear Demo Data',
					icon: Trash2,
					onClick: () => {
						clearDemoDataConfirmation()
					},
					condition: () => {
						return (
							userResource.data?.is_moderator &&
							settingsStore.settings.data?.demo_data_present
						)
					},
				},
				{
					icon: LogOut,
					label: 'Log out',
					onClick: () => {
						logout.submit().finally(() => {
							window.location.href = '/login'
						})
					},
					condition: () => {
						return isLoggedIn
					},
				},
				{
					icon: LogIn,
					label: 'Log in',
					onClick: () => {
						window.location.href = '/login'
					},
					condition: () => {
						return !isLoggedIn
					},
				},
			],
		},
	]
})

const canOpenDesk = () => {
	const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
	if (cookies.get('system_user') === 'yes') return true
	const user = userResource.data
	return !!(
		user?.is_system_manager ||
		user?.is_moderator ||
		user?.is_instructor ||
		user?.is_evaluator
	)
}

const clearDemoDataConfirmation = () => {
	$dialog({
		title: __('Confirm clearing demo data?'),
		message: __(
			'Are you sure you want to clear the demo data? This would delete the sample demo course and associated demo data. This action cannot be undone.'
		),
		actions: [
			{
				label: __('Confirm'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					clearDemoData()
					close()
				},
			},
		],
	})
}

const clearDemoData = () => {
	call('lms.lms.api.clear_demo_data')
		.then(() => {
			window.location.href = '/dashboard'
			toast.success(__('Demo data cleared successfully'))
		})
		.catch((error) => {
			toast.error(__(error.message || 'Error clearing demo data'))
			console.error('Error clearing demo data:', error)
		})
}
</script>
