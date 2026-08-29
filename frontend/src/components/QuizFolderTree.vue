<template>
	<div class="flex flex-col h-full overflow-y-auto py-2">
		<div
			class="flex items-center px-3 py-1.5 cursor-pointer rounded mx-1 text-sm font-medium"
			:class="selectedFolder === null ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
			@click="$emit('select', null)"
		>
			<component :is="icons.LayoutList" class="size-4 mr-2 shrink-0" />
			<span class="truncate">{{ __('All Quizzes') }}</span>
			<span class="ml-auto text-xs text-ink-gray-5">{{ totalCount }}</span>
		</div>
		<div
			class="flex items-center px-3 py-1.5 cursor-pointer rounded mx-1 text-sm font-medium"
			:class="selectedFolder === '__unfiled__' ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
			@click="$emit('select', '__unfiled__')"
		>
			<component :is="icons.FileQuestion" class="size-4 mr-2 shrink-0" />
			<span class="truncate">{{ __('Unfiled') }}</span>
			<span class="ml-auto text-xs text-ink-gray-5">{{ unfiledCount }}</span>
		</div>

		<div class="border-t my-2 mx-3"></div>

		<div class="flex items-center justify-between px-3 mb-1">
			<span class="text-xs font-semibold text-ink-gray-5 uppercase tracking-wide">{{ __('Folders') }}</span>
			<button
				v-if="!readOnlyMode"
				class="text-ink-gray-5 hover:text-ink-gray-9 p-0.5 rounded hover:bg-surface-gray-2"
				@click="$emit('createFolder', null)"
			>
				<component :is="icons.Plus" class="size-3.5" />
			</button>
		</div>

		<div v-if="folders.length === 0" class="px-3 py-2 text-xs text-ink-gray-5 italic">
			{{ __('No folders yet') }}
		</div>

		<FolderNode
			v-for="folder in folders"
			:key="folder.name"
			:folder="folder"
			:depth="0"
			:selectedFolder="selectedFolder"
			:readOnlyMode="readOnlyMode"
			@select="(f) => $emit('select', f)"
			@createSubfolder="(f) => $emit('createFolder', f)"
			@renameFolder="(f) => $emit('renameFolder', f)"
			@deleteFolder="(f) => $emit('deleteFolder', f)"
		/>
	</div>
</template>

<script setup>
import * as icons from 'lucide-vue-next'
import FolderNode from './QuizFolderNode.vue'

defineProps({
	folders: { type: Array, default: () => [] },
	selectedFolder: { default: null },
	totalCount: { type: Number, default: 0 },
	unfiledCount: { type: Number, default: 0 },
	readOnlyMode: { type: Boolean, default: false },
})

defineEmits(['select', 'createFolder', 'renameFolder', 'deleteFolder'])
</script>
