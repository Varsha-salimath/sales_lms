<template>
	<section
		class="shrink-0 border-t px-4 py-3 sm:px-5"
		style="
			background: var(--genius-surface-elevated);
			border-color: var(--genius-border);
		"
	>
		<div
			class="grid grid-cols-1 gap-3 rounded-xl border bg-white p-3 sm:grid-cols-2 lg:grid-cols-[minmax(140px,1.2fr)_90px_110px_minmax(180px,1.4fr)_minmax(150px,1fr)] lg:items-start lg:gap-4 lg:p-4"
			style="border-color: var(--genius-border)"
		>
			<div class="min-w-0">
				<div class="text-xs text-[color:var(--genius-muted)]">
					{{ __('Current lesson') }}
				</div>
				<div
					class="mt-0.5 truncate text-sm font-semibold text-[color:var(--genius-navy)]"
					:title="lastLesson || ''"
				>
					{{ lastLesson || '—' }}
				</div>
			</div>

			<div>
				<div class="text-xs text-[color:var(--genius-muted)]">
					{{ __('Score') }}
				</div>
				<div
					class="mt-0.5 text-lg font-semibold tabular-nums text-[color:var(--genius-navy)]"
				>
					{{ score != null && score !== '' ? score : '—' }}
				</div>
			</div>

			<div>
				<div class="text-xs text-[color:var(--genius-muted)]">
					{{ __('Time in lesson') }}
				</div>
				<div
					class="mt-0.5 text-sm font-semibold tabular-nums text-[color:var(--genius-navy)]"
				>
					{{ formatSeconds(totalTime) }}
				</div>
			</div>

			<div class="min-w-0">
				<div class="mb-1 text-xs font-medium text-[color:var(--genius-muted)]">
					{{ __('Notes') }}
				</div>
				<textarea
					v-model="localNotes"
					rows="2"
					class="w-full resize-none rounded-lg border px-2.5 py-1.5 text-sm outline-none focus:border-[color:var(--genius-blue)]"
					style="border-color: var(--genius-border)"
					:placeholder="__('Jot down key takeaways…')"
					@input="persistNotes"
				/>
			</div>

			<div class="min-w-0">
				<div class="mb-1 text-xs font-medium text-[color:var(--genius-muted)]">
					{{ __('Resources') }}
				</div>
				<ul class="space-y-1 text-sm">
					<li>
						<router-link
							:to="{ name: 'GeniusCourseDetail', params: { courseName } }"
							class="text-[color:var(--genius-blue)] hover:underline"
						>
							{{ __('Course overview') }}
						</router-link>
					</li>
					<li v-if="launchFile">
						<a
							:href="launchFile"
							target="_blank"
							rel="noopener"
							class="text-[color:var(--genius-blue)] hover:underline"
						>
							{{ __('Open lesson in new tab') }}
						</a>
					</li>
				</ul>
			</div>
		</div>
	</section>
</template>
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
	courseName: { type: String, required: true },
	score: { type: [Number, String], default: null },
	totalTime: { type: [Number, String], default: null },
	launchFile: { type: String, default: '' },
	storageKey: { type: String, default: '' },
	lastLesson: { type: String, default: '' },
})

const localNotes = ref('')

watch(
	() => props.storageKey,
	(key) => {
		if (!key) {
			localNotes.value = ''
			return
		}
		localNotes.value = localStorage.getItem(key) || ''
	},
	{ immediate: true }
)

const persistNotes = () => {
	if (!props.storageKey) return
	localStorage.setItem(props.storageKey, localNotes.value)
}

const formatSeconds = (value) => {
	if (value == null || value === '') return '—'
	const total = Math.max(0, Math.floor(Number(value) || 0))
	const h = Math.floor(total / 3600)
	const m = Math.floor((total % 3600) / 60)
	const s = total % 60
	if (h) return `${h}h ${m}m`
	if (m) return `${m}m ${s}s`
	return `${s}s`
}
</script>
