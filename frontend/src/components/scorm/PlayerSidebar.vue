<template>
	<aside
		class="flex h-full w-full flex-col border-r"
		style="
			background: var(--genius-surface-elevated);
			border-color: var(--genius-border);
		"
	>
		<div class="sticky top-0 z-10 border-b px-4 py-3" style="border-color: var(--genius-border); background: var(--genius-surface-elevated)">
			<div class="text-sm font-semibold text-[color:var(--genius-navy)]">
				{{ __('Course content') }}
			</div>
			<div class="mt-0.5 text-xs text-[color:var(--genius-muted)]">
				<template v-if="courseProgress > 0">
					{{ Math.round(courseProgress) }}% {{ __('complete') }}
					<span class="mx-1">·</span>
				</template>
				{{ completedCount }}/{{ lessons.length }} {{ __('completed') }}
			</div>
			<div
				v-if="courseProgress > 0"
				class="mt-2 h-1.5 overflow-hidden rounded-full"
				style="background: var(--genius-border)"
			>
				<div
					class="h-1.5 rounded-full transition-all duration-500"
					:style="{
						width: `${Math.min(100, courseProgress)}%`,
						background: 'var(--genius-primary)',
					}"
				/>
			</div>
		</div>
		<nav class="flex-1 overflow-y-auto p-2">
			<button
				v-for="(lesson, idx) in lessons"
				:key="lesson.key"
				type="button"
				class="mb-1 flex w-full items-start gap-2 rounded-xl px-3 py-2.5 text-left transition-colors"
				:class="
					lesson.key === activeKey
						? 'bg-[color:var(--genius-blue-light)] ring-1 ring-[color:var(--genius-primary)]'
						: lesson.locked
							? 'cursor-not-allowed opacity-50'
							: 'hover:bg-[color:var(--genius-bg)]'
				"
				:disabled="lesson.locked"
				@click="$emit('select-lesson', lesson)"
			>
				<span
					class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full text-[10px] font-semibold"
					:style="statusStyle(lesson)"
				>
					<span v-if="lesson.isComplete">✓</span>
					<span v-else>{{ idx + 1 }}</span>
				</span>
				<div class="min-w-0 flex-1">
					<div class="truncate text-sm font-medium text-[color:var(--genius-navy)]">
						{{ lesson.title }}
					</div>
					<div
						v-if="lesson.isComplete"
						class="text-[11px] font-medium text-[color:var(--genius-success)]"
					>
						{{ __('Completed') }}
					</div>
					<div
						v-else-if="lesson.partial || (lesson.key === activeKey && courseProgress > 0 && !lesson.isComplete)"
						class="text-[11px] text-[color:var(--genius-primary)]"
					>
						{{
							courseProgress > 0 && lesson.key === activeKey
								? `${Math.round(courseProgress)}% ${__('complete')}`
								: __('In progress')
						}}
					</div>
					<div
						v-else-if="lesson.locked"
						class="text-[11px] text-[color:var(--genius-muted)]"
					>
						{{ __('Locked') }}
					</div>
				</div>
			</button>
			<div
				v-if="!lessons.length"
				class="px-3 py-6 text-center text-sm text-[color:var(--genius-muted)]"
			>
				{{ __('No lessons yet') }}
			</div>
		</nav>
	</aside>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
	lessons: { type: Array, default: () => [] },
	activeKey: { type: String, default: '' },
	courseProgress: { type: Number, default: 0 },
})

defineEmits(['select-lesson'])

const completedCount = computed(
	() => props.lessons.filter((l) => l.isComplete).length
)

const statusStyle = (lesson) => {
	if (lesson.isComplete) {
		return { background: 'var(--genius-success)', color: '#fff' }
	}
	if (lesson.key === props.activeKey) {
		return { background: 'var(--genius-primary)', color: '#fff' }
	}
	return { background: 'var(--genius-border)', color: 'var(--genius-muted)' }
}
</script>
