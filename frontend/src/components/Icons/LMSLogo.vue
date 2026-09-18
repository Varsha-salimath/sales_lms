<template>
	<img
		:src="logoSrc"
		alt="LMS"
		class="h-8 w-auto object-contain object-left"
		:class="imgClass"
	/>
</template>
<script setup>
import logoSrc from '@/assets/il-logo-white.svg'

defineProps({
	imgClass: {
		type: String,
		default: '',
	},
})
</script>
