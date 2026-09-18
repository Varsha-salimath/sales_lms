<template>
	<section class="rs-card">
		<header class="rs-head">
			<div class="min-w-0">
				<h2 class="rs-title">{{ title }}</h2>
				<p v-if="subtitle" class="rs-sub">{{ subtitle }}</p>
			</div>
			<slot name="action">
				<button v-if="action" type="button" class="rs-action" @click="$emit('action')">
					{{ action }}
					<ArrowRight class="h-4 w-4" />
				</button>
			</slot>
		</header>
		<div :class="flush ? '' : 'rs-body'">
			<slot />
		</div>
	</section>
</template>

<script setup>
import { ArrowRight } from 'lucide-vue-next'

// PTM-board section: light-blue header strip, title, optional "View details →" pill.
defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: '' },
	action: { type: String, default: '' },
	flush: { type: Boolean, default: false },
})
defineEmits(['action'])
</script>

<style scoped>
.rs-card {
	overflow: hidden;
	border: 1px solid #edf0f4;
	border-radius: 20px;
	background: #fff;
	box-shadow: 0 2px 10px rgba(0, 37, 76, 0.06);
}

.rs-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.9rem 1.25rem;
	background: #f4f9ff;
}

.rs-title {
	margin: 0;
	color: var(--il-ink);
	font-size: 1.125rem;
	font-weight: 400;
}

.rs-sub {
	margin-top: 0.15rem;
	color: var(--il-muted);
	font-size: 0.75rem;
}

.rs-action {
	display: inline-flex;
	flex-shrink: 0;
	align-items: center;
	gap: 0.4rem;
	height: 2.1rem;
	padding: 0 0.9rem;
	border: 1px solid #d9e9ff;
	border-radius: 999px;
	background: #fff;
	color: var(--il-primary-40);
	font-size: 0.875rem;
	font-weight: 500;
}

.rs-body {
	padding: 1.1rem 1.25rem 1.25rem;
}
</style>
