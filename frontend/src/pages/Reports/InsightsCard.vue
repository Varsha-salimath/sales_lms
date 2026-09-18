<template>
	<div class="ic-card">
		<Sparkles class="ic-deco" />
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex items-center gap-2.5">
				<span class="ic-badge"><Sparkles class="h-4 w-4" /></span>
				<span class="text-sm font-medium text-[#5B3FD6]">{{ title }}</span>
			</div>
			<span v-if="chip" class="ic-chip" :class="`is-${chipTone}`">{{ chip }}</span>
		</div>
		<ul class="mt-2.5 space-y-1.5">
			<li v-for="(line, i) in items" :key="i" class="ic-li">
				<strong v-if="line.lead">{{ line.lead }}</strong>
				{{ line.text ?? line }}
			</li>
			<li v-if="!items.length" class="ic-li text-[color:var(--il-muted)]">{{ empty }}</li>
		</ul>
		<slot />
	</div>
</template>

<script setup>
import { Sparkles } from 'lucide-vue-next'

// Lavender "Insights" card from the PTM board. Items are strings or { lead, text }.
defineProps({
	title: { type: String, default: 'Insights' },
	items: { type: Array, default: () => [] },
	chip: { type: String, default: '' },
	chipTone: { type: String, default: 'good' },
	empty: { type: String, default: 'Insights appear once there are scores.' },
})
</script>

<style scoped>
.ic-card {
	position: relative;
	overflow: hidden;
	border-radius: 16px;
	padding: 1rem 1.25rem;
	background: linear-gradient(100deg, #ffffff 0%, #f5f1ff 50%, #e8e1ff 100%);
}

.ic-deco {
	position: absolute;
	top: 0.6rem;
	right: 0.8rem;
	width: 2.2rem;
	height: 2.2rem;
	color: #c9bcff;
	opacity: 0.6;
}

.ic-badge {
	display: grid;
	place-items: center;
	width: 2rem;
	height: 2rem;
	border-radius: 999px;
	background: linear-gradient(135deg, #7c5cff, #027bff);
	color: #fff;
}

.ic-chip {
	position: relative;
	z-index: 1;
	border: 1px solid;
	border-radius: 999px;
	padding: 0.15rem 0.7rem;
	font-size: 0.7rem;
	font-weight: 500;
}

.ic-chip.is-good {
	border-color: #35c759;
	background: #e7f8ec;
	color: #146c31;
}

.ic-chip.is-warn {
	border-color: #ffab00;
	background: #fff8e6;
	color: #8a5a00;
}

.ic-chip.is-bad {
	border-color: #f03e3e;
	background: #fff1f1;
	color: #b42323;
}

.ic-li {
	position: relative;
	padding-left: 0.9rem;
	color: var(--il-ink);
	font-size: 0.8125rem;
	line-height: 1.3rem;
}

.ic-li::before {
	content: '';
	position: absolute;
	left: 0;
	top: 0.55rem;
	width: 0.3rem;
	height: 0.3rem;
	border-radius: 999px;
	background: var(--il-ink);
}
</style>
