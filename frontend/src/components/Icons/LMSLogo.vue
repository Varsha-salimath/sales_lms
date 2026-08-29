<template>
	<img
		:src="logoSrc"
		alt="Infinity Learn by Sri Chaitanya"
		class="h-8 w-auto object-contain object-left"
		:class="imgClass"
	/>
</template>
<script setup>
import logoSrc from '@/assets/il-logo.png'

defineProps({
	imgClass: {
		type: String,
		default: '',
	},
})
</script>
