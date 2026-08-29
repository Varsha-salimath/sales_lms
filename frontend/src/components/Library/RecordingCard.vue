<template>
	<div class="border rounded-lg bg-surface-white overflow-hidden flex flex-col">
		<div class="relative aspect-video bg-surface-gray-2">
			<img
				v-if="recording.thumbnail_url"
				:src="recording.thumbnail_url"
				:alt="recording.title"
				class="w-full h-full object-cover"
			/>
			<div
				v-else
				class="w-full h-full flex items-center justify-center text-ink-gray-5"
			>
				<Video class="w-10 h-10" />
			</div>
			<div
				v-if="recording.duration_minutes"
				class="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-0.5 text-xs text-white"
			>
				{{ formatDuration(recording.duration_minutes) }}
			</div>
		</div>

		<div class="p-4 flex flex-col flex-1">
			<div
				v-if="recording.session_number && recording.batch_title"
				class="text-xs text-ink-gray-5 mb-1"
			>
				{{
					__('Session {0} - Batch {1}').format(
						recording.session_number,
						recording.batch_title
					)
				}}
			</div>
			<div class="text-sm font-medium text-ink-gray-9 line-clamp-2 mb-2">
				{{ recording.title }}
			</div>
			<div class="text-xs text-ink-gray-5 mb-4">
				{{ formatDateTime(recording.recording_date, recording.recording_time) }}
			</div>

			<div
				v-if="canAssign"
				class="text-xs text-ink-gray-5 mb-3"
			>
				{{ __('{0} with access').format(recording.assigned_count || 0) }}
			</div>

			<div class="mt-auto space-y-2">
				<Button
					class="w-full"
					variant="solid"
					:disabled="!recording.watch_url || recording.is_unavailable"
					@click="openRecording"
				>
					<template #prefix>
						<Play class="w-4 h-4" />
					</template>
					{{
						recording.is_unavailable
							? __('Unavailable')
							: __('Watch')
					}}
				</Button>
				<Button
					v-if="canAssign"
					class="w-full"
					variant="outline"
					@click="$emit('assign', recording)"
				>
					<template #prefix>
						<UserPlus class="w-4 h-4" />
					</template>
					{{ __('Grant Access') }}
				</Button>
				<div
					v-if="recording.file_size_mb"
					class="text-xs text-ink-gray-5 text-center"
				>
					{{ formatFileSize(recording.file_size_mb) }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { Play, UserPlus, Video } from 'lucide-vue-next'
import dayjs from '@/utils/dayjs'

defineEmits(['assign'])

const props = defineProps({
	recording: {
		type: Object,
		required: true,
	},
	canAssign: {
		type: Boolean,
		default: false,
	},
})

const formatDuration = (minutes) => {
	if (!minutes) return ''
	if (minutes < 60) return `${minutes} min`
	const hours = Math.floor(minutes / 60)
	const remainder = minutes % 60
	return remainder ? `${hours}h ${remainder}m` : `${hours}h`
}

const formatDateTime = (date, time) => {
	if (!date) return ''
	const value = time ? `${date} ${time}` : date
	return dayjs(value).format('MMM D, YYYY • h:mm A')
}

const formatFileSize = (sizeMb) => {
	if (!sizeMb) return ''
	return `${Math.round(sizeMb)} MB`
}

const openRecording = () => {
	if (props.recording.watch_url && !props.recording.is_unavailable) {
		window.open(props.recording.watch_url, '_blank', 'noopener,noreferrer')
	}
}
</script>
