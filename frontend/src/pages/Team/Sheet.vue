<template>
	<Teleport to="body">
		<div v-if="modelValue" class="sh-backdrop" @mousedown.self="close">
			<div class="sh-panel" role="dialog" aria-modal="true" :aria-label="title">
				<header class="sh-head">
					<div class="min-w-0">
						<h2 class="truncate text-lg font-semibold text-[color:var(--il-ink)]">{{ title }}</h2>
						<p v-if="subtitle" class="truncate text-xs text-[color:var(--il-muted)]">{{ subtitle }}</p>
					</div>
					<button type="button" class="sh-close" :aria-label="__('Close')" @click="close"><X class="h-5 w-5" /></button>
				</header>
				<div class="sh-body"><slot /></div>
				<footer v-if="$slots.footer" class="sh-foot"><slot name="footer" /></footer>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { X } from 'lucide-vue-next'

// Small IL-styled modal: centred on desktop, bottom sheet on phones.
const props = defineProps({
	modelValue: { type: Boolean, default: false },
	title: { type: String, default: '' },
	subtitle: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const close = () => emit('update:modelValue', false)
const onKey = (e) => e.key === 'Escape' && close()
watch(
	() => props.modelValue,
	(open) => (open ? window.addEventListener('keydown', onKey) : window.removeEventListener('keydown', onKey))
)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.sh-backdrop {
	position: fixed;
	inset: 0;
	z-index: 60;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 1rem;
	background: rgba(0, 20, 45, 0.45);
}

.sh-panel {
	display: flex;
	width: 100%;
	max-width: 36rem;
	max-height: calc(100vh - 2rem);
	flex-direction: column;
	border-radius: 24px;
	background: #fff;
	box-shadow: 0 20px 60px rgba(0, 37, 76, 0.3);
}

.sh-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	border-radius: 24px 24px 0 0;
	padding: 1rem 1.25rem;
	background: #f4f9ff;
}

.sh-close {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 2.25rem;
	height: 2.25rem;
	border-radius: 999px;
	color: var(--il-muted);
}

.sh-close:hover {
	background: #fff;
}

.sh-body {
	overflow-y: auto;
	padding: 1.1rem 1.25rem;
}

.sh-foot {
	display: flex;
	justify-content: flex-end;
	gap: 0.6rem;
	border-top: 1px solid var(--il-neutral-95);
	padding: 0.85rem 1.25rem;
}

@media (max-width: 640px) {
	.sh-backdrop {
		align-items: flex-end;
		padding: 0;
	}

	.sh-panel {
		max-width: none;
		max-height: 92vh;
		border-radius: 24px 24px 0 0;
	}
}
</style>
