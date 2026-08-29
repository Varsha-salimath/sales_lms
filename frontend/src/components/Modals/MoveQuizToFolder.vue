<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Move to Folder'),
			size: 'sm',
			actions: [
				{
					label: __('Move'),
					variant: 'solid',
					onClick: (close) => moveQuizzes(close),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-1 max-h-64 overflow-y-auto">
				<div
					class="flex items-center px-3 py-2 rounded cursor-pointer text-sm"
					:class="targetFolder === '__unfiled__' ? 'bg-surface-gray-3 font-medium' : 'hover:bg-surface-gray-2'"
					@click="targetFolder = '__unfiled__'"
				>
					<component :is="icons.FileQuestion" class="size-4 mr-2 text-ink-gray-5" />
					{{ __('Unfiled (Root)') }}
				</div>
				<div
					v-for="row in flatFolderRows"
					:key="row.name"
					class="flex items-center px-3 py-2 rounded cursor-pointer text-sm"
					:class="targetFolder === row.name ? 'bg-surface-gray-3 font-medium' : 'hover:bg-surface-gray-2'"
					:style="{ paddingLeft: `${12 + row.depth * 16}px` }"
					@click="targetFolder = row.name"
				>
					<component :is="icons.Folder" class="size-4 mr-2 shrink-0 text-ink-gray-5" />
					<span class="truncate">{{ row.title }}</span>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Dialog, createResource, toast } from 'frappe-ui'
import * as icons from 'lucide-vue-next'

const show = defineModel()

const props = defineProps({
	quizzes: { type: Array, default: () => [] },
	folders: { type: Array, default: () => [] },
})

const emit = defineEmits(['moved'])

const targetFolder = ref('__unfiled__')

watch(show, (val) => {
	if (val) targetFolder.value = '__unfiled__'
})

function walkFolderTree(nodes, depth, acc) {
	for (const node of nodes || []) {
		acc.push({ name: node.name, title: node.title, depth })
		if (node.children?.length) {
			walkFolderTree(node.children, depth + 1, acc)
		}
	}
	return acc
}

const flatFolderRows = computed(() => walkFolderTree(props.folders, 0, []))

const moveResource = createResource({
	url: 'lms.lms.api.move_quiz_to_folder',
})

const moveQuizzes = async (close) => {
	const folder = targetFolder.value === '__unfiled__' ? null : targetFolder.value
	try {
		for (const quiz of props.quizzes) {
			await moveResource.submit({ quiz, folder })
		}
		toast.success(__('Quizzes moved successfully'))
		emit('moved')
		close()
	} catch (err) {
		toast.error(err.messages?.[0] || __('Error moving quizzes'))
	}
}
</script>
