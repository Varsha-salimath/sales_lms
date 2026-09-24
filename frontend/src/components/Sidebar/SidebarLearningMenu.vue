<template>
	<Popover
		placement="right-start"
		trigger="click"
		:leaveDelay="0.05"
		class="flex w-full"
	>
		<template #target="{ togglePopover, isOpen }">
			<button
				type="button"
				class="sidebar-nav-link flex w-full h-7 cursor-pointer items-center rounded duration-300 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="[
					isActive || isOpen ? 'sidebar-nav-link--active shadow-sm' : '',
				]"
				@click="togglePopover()"
			>
				<div
					class="flex items-center w-full duration-300 ease-in-out"
					:class="isCollapsed ? 'p-1 relative justify-center' : 'px-2 py-1'"
				>
					<Tooltip :text="__('Curriculum')" placement="right">
						<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
							<BookOpen class="sidebar-nav-link__icon h-4 w-4 stroke-1.5" />
						</span>
					</Tooltip>
					<span
						v-if="!isCollapsed"
						class="ms-2 flex flex-1 items-center justify-between text-sm"
					>
						<span>{{ __('Curriculum') }}</span>
						<ChevronRight
							class="h-4 w-4 stroke-1.5 opacity-80 transition-transform"
							:class="{ 'rotate-90': isOpen }"
						/>
					</span>
				</div>
			</button>
		</template>
		<template #body="{ close }">
			<div
				class="min-w-[220px] rounded-xl bg-surface-modal p-2 shadow-2xl ring-1 ring-black ring-opacity-5"
			>
				<div class="px-2 pb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
					{{ __('Curriculum') }}
				</div>
				<nav class="flex flex-col gap-0.5">
					<button
						v-for="entry in menuItems"
						:key="entry.label"
						type="button"
						class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						:class="
							isMenuItemActive(entry)
								? 'bg-surface-gray-2 font-medium text-ink-gray-9'
								: ''
						"
						@click="goTo(entry, close)"
					>
						<component
							:is="icons[entry.icon]"
							v-if="entry.icon && icons[entry.icon]"
							class="h-4 w-4 shrink-0 stroke-1.5 text-ink-gray-6"
						/>
						<span>{{ __(entry.label) }}</span>
					</button>
				</nav>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { Popover, Tooltip } from 'frappe-ui'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, ChevronRight } from 'lucide-vue-next'
import * as icons from 'lucide-vue-next'

const props = defineProps({
	menuItems: {
		type: Array,
		default: () => [],
	},
	isCollapsed: {
		type: Boolean,
		default: false,
	},
})

const router = useRouter()
const route = useRoute()

const isMenuItemActive = (entry) => {
	const routeName = route.name
	return (
		entry.to === routeName || entry.activeFor?.includes(routeName)
	)
}

const isActive = computed(() => {
	return props.menuItems.some((entry) => isMenuItemActive(entry))
})

function goTo(entry, close) {
	if (entry.to && router.hasRoute(entry.to)) {
		router.push({ name: entry.to })
	}
	close?.()
}
</script>

<style scoped>
.sidebar-nav-link {
	color: #fff !important;
	background-color: transparent !important;
}

.sidebar-nav-link:hover {
	background-color: rgba(255, 255, 255, 0.12) !important;
	color: #fff !important;
}

.sidebar-nav-link--active,
.sidebar-nav-link--active:hover {
	background-color: rgba(255, 255, 255, 0.18) !important;
	color: #fff !important;
	box-shadow: inset 3px 0 0 #fcde5a;
	border-radius: 12px;
}

.sidebar-nav-link--active .sidebar-nav-link__icon,
.sidebar-nav-link--active svg {
	color: #fff !important;
	stroke: #fff !important;
}

.sidebar-nav-link__icon {
	color: rgba(255, 255, 255, 0.85) !important;
	stroke: rgba(255, 255, 255, 0.85) !important;
}
</style>
