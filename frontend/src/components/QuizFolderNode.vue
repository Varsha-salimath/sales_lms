<template>
	<div>
		<div
			class="flex items-center px-3 py-1.5 cursor-pointer rounded mx-1 group text-sm"
			:class="selectedFolder === folder.name ? 'bg-surface-gray-3 text-ink-gray-9 font-medium' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
			:style="{ paddingLeft: `${(depth * 16) + 12}px` }"
			@click="$emit('select', folder.name)"
		>
			<button
				class="p-0.5 shrink-0 mr-0.5"
				@click.stop="expanded = !expanded"
			>
				<component
					:is="icons.ChevronRight"
					class="size-3.5 transition-transform duration-150"
					:class="{
						'rotate-90': expanded,
						'opacity-0': !folder.children?.length,
					}"
				/>
			</button>
			<component
				:is="expanded ? icons.FolderOpen : icons.Folder"
				class="size-4 mr-2 shrink-0 text-ink-gray-5"
			/>
			<span class="truncate">{{ folder.title }}</span>
			<span class="ml-auto text-xs text-ink-gray-5 mr-1">{{ folder.quiz_count || '' }}</span>
			<Dropdown
				v-if="!readOnlyMode"
				:options="folderActions"
				class="shrink-0 opacity-0 group-hover:opacity-100"
			>
				<button
					class="p-0.5 rounded hover:bg-surface-gray-3"
					@click.stop
				>
					<component :is="icons.MoreHorizontal" class="size-3.5 text-ink-gray-5" />
				</button>
			</Dropdown>
		</div>
		<div v-if="expanded && folder.children?.length">
			<QuizFolderSubtree
				v-for="child in folder.children"
				:key="child.name"
				:folder="child"
				:depth="depth + 1"
				:selectedFolder="selectedFolder"
				:readOnlyMode="readOnlyMode"
				@select="(f) => $emit('select', f)"
				@createSubfolder="(f) => $emit('createSubfolder', f)"
				@renameFolder="(f) => $emit('renameFolder', f)"
				@deleteFolder="(f) => $emit('deleteFolder', f)"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Dropdown } from 'frappe-ui'
import * as icons from 'lucide-vue-next'
import QuizFolderSubtree from './QuizFolderNode.vue'

const props = defineProps({
	folder: { type: Object, required: true },
	depth: { type: Number, default: 0 },
	selectedFolder: { default: null },
	readOnlyMode: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'createSubfolder', 'renameFolder', 'deleteFolder'])

const expanded = ref(false)

const folderActions = computed(() => [
	{
		label: __('New Subfolder'),
		icon: 'folder-plus',
		onClick: () => emit('createSubfolder', props.folder.name),
	},
	{
		label: __('Rename'),
		icon: 'pencil',
		onClick: () => emit('renameFolder', props.folder),
	},
	{
		label: __('Delete'),
		icon: 'trash-2',
		onClick: () => emit('deleteFolder', props.folder),
	},
])
</script>
