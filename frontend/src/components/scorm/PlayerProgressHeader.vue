<template>
	<header
		class="sticky top-0 z-20 flex items-center justify-between gap-4 border-b px-4 py-3 sm:px-5"
		style="
			background: var(--genius-surface-elevated);
			border-color: var(--genius-border);
		"
	>
		<div class="min-w-0 flex-1">
			<nav class="mb-1 flex flex-wrap items-center gap-1 text-xs text-[color:var(--genius-muted)]">
				<template v-for="(crumb, idx) in breadcrumbs" :key="idx">
					<router-link
						v-if="crumb.route"
						:to="crumb.route"
						class="hover:text-[color:var(--genius-blue)]"
					>
						{{ crumb.label }}
					</router-link>
					<span v-else>{{ crumb.label }}</span>
					<span v-if="idx < breadcrumbs.length - 1">/</span>
				</template>
			</nav>
			<h1
				class="truncate text-base font-semibold sm:text-lg"
				style="color: var(--genius-navy) !important"
			>
				{{ title }}
			</h1>
			<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[color:var(--genius-muted)]">
				<span v-if="currentLesson">
					{{ __('Now') }}: {{ currentLesson }}
				</span>
				<span v-if="durationLabel">{{ durationLabel }}</span>
			</div>
		</div>
		<div class="flex shrink-0 items-center gap-3">
			<div class="hidden text-right sm:block">
				<div class="text-xs text-[color:var(--genius-muted)]">
					{{ __('Progress') }}
				</div>
				<div class="text-sm font-semibold tabular-nums text-[color:var(--genius-navy)]">
					{{ Math.round(progress || 0) }}%
				</div>
			</div>
			<div
				class="relative grid size-12 place-items-center rounded-full transition-all duration-500"
				:class="{ 'scale-110': celebrate }"
				:style="ringStyle"
				:title="`${Math.round(progress || 0)}%`"
			>
				<div
					class="grid size-9 place-items-center rounded-full text-xs font-semibold"
					style="
						background: var(--genius-surface-elevated);
						color: var(--genius-navy);
					"
				>
					{{ Math.round(progress || 0) }}
				</div>
			</div>
			<button
				type="button"
				class="rounded-xl border px-3 py-2 text-sm font-semibold text-[color:var(--genius-navy)] hover:bg-[color:var(--genius-bg)]"
				style="border-color: var(--genius-border)"
				@click="$emit('exit')"
			>
				{{ __('Exit Course') }}
			</button>
		</div>
	</header>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
	title: { type: String, default: '' },
	progress: { type: Number, default: 0 },
	breadcrumbs: { type: Array, default: () => [] },
	currentLesson: { type: String, default: '' },
	durationLabel: { type: String, default: '' },
	celebrate: { type: Boolean, default: false },
})

defineEmits(['exit'])

const ringStyle = computed(() => {
	const pct = Math.min(100, Math.max(0, props.progress || 0))
	return {
		background: `conic-gradient(var(--genius-primary) ${pct * 3.6}deg, var(--genius-border) 0deg)`,
	}
})
</script>
