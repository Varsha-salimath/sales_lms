<template>
	<div class="p-8 text-center text-sm text-ink-gray-6">
		{{ __('Opening Genius SCORM player…') }}
	</div>
</template>
<script setup>
import { onBeforeMount } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
	courseName: { type: String, required: true },
	chapterName: { type: String, required: true },
})

const router = useRouter()

onBeforeMount(() => {
	router.replace({
		name: 'GeniusScormPlayer',
		params: { courseName: props.courseName },
		query: { chapter: props.chapterName },
	})
})
</script>
