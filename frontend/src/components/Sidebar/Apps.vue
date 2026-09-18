<template>
	<Popover placement="right-start" trigger="click" class="flex w-full">
		<template #target>
			<button
				type="button"
				:class="[
					'group w-full flex h-7 items-center justify-between rounded px-2 text-base text-ink-gray-7 hover:bg-surface-gray-2',
				]"
			>
				<div class="flex gap-2">
					<LayoutGrid class="size-4 stroke-1.5" />
					<span class="whitespace-nowrap">
						{{ __('Apps') }}
					</span>
				</div>
				<ChevronRight class="h-4 w-4 stroke-1.5" />
			</button>
		</template>
		<template #body>
			<div
				class="grid grid-cols-3 justify-between mx-3 p-2 rounded-lg bg-surface-modal shadow-2xl ring-1 ring-black ring-opacity-5"
			>
				<button
					v-for="app in apps.data"
					:key="app.name"
					type="button"
					class="flex flex-col gap-1.5 rounded justify-center items-center py-2 px-3 hover:bg-surface-gray-2"
					@click="openApp(app)"
				>
					<img
						class="size-8 object-contain rounded"
						:src="app.logo"
						:alt="app.title"
					/>
					<span class="text-sm text-ink-gray-7">
						{{ app.title }}
					</span>
				</button>
			</div>
		</template>
	</Popover>
</template>
<script setup>
import { Popover, createResource } from 'frappe-ui'
import { LayoutGrid, ChevronRight } from 'lucide-vue-next'

const deskApp = {
	name: 'desk',
	logo: '/assets/frappe/images/frappe-framework-logo.png',
	title: __('Desk'),
	route: '/desk',
}

const apps = createResource({
	url: 'frappe.apps.get_apps',
	cache: 'apps',
	auto: true,
	transform: (data) => {
		const items = (data || [])
			.filter((app) => app.name !== 'lms')
			.map((app) => ({
				name: app.name,
				logo: app.logo,
				title: __(app.title),
				route: app.route,
			}))
		return [deskApp, ...items]
	},
})

function openApp(app) {
	const route = app?.route || '/desk'
	window.location.assign(route)
}
</script>
