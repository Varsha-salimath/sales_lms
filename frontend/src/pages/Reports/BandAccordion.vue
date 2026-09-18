<template>
	<div class="ba" :style="{ background: tone.row, borderColor: tone.rowBorder }">
		<button type="button" class="ba-head" :aria-expanded="open" @click="open = !open">
			<div class="ba-name">
				<div class="text-lg text-[color:var(--il-ink)]">{{ title }}</div>
				<span class="ba-chip" :style="{ background: tone.solid }">{{ tone.label }}</span>
			</div>
			<div class="ba-box ba-main">
				<div class="text-xs text-[color:var(--il-muted)]">{{ mainLabel }}</div>
				<div class="mt-0.5 text-lg text-[color:var(--il-ink)]">{{ mainValue }}</div>
				<div v-if="mainSub" class="text-[11px] text-[color:var(--il-muted)]">{{ mainSub }}</div>
			</div>
			<div class="ba-box ba-dist">
				<div v-for="d in distribution" :key="d.key">
					<div class="text-xs text-[color:var(--il-muted)]">{{ d.label }}</div>
					<div class="mt-0.5 text-lg text-[color:var(--il-ink)]">{{ d.pct }}%</div>
					<div class="text-[11px] text-[color:var(--il-muted)]">{{ d.count }} {{ unit }}</div>
				</div>
			</div>
			<ChevronDown class="ba-chev" :class="{ 'rotate-180': open }" />
		</button>
		<div v-if="open" class="ba-body">
			<slot />
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { bandStyle } from './reportUtils'

// "Subject wise performance" row from the PTM board, reused per test / metric.
const props = defineProps({
	title: { type: String, required: true },
	band: { type: String, default: null },
	mainLabel: { type: String, default: 'Average' },
	mainValue: { type: String, default: '—' },
	mainSub: { type: String, default: '' },
	distribution: { type: Array, default: () => [] }, // [{ key, label, pct, count }]
	unit: { type: String, default: 'learners' },
	defaultOpen: { type: Boolean, default: false },
})

const open = ref(props.defaultOpen)
const tone = computed(() => bandStyle(props.band))
</script>

<style scoped>
.ba {
	overflow: hidden;
	border: 1px solid;
	border-radius: 16px;
}

.ba-head {
	display: grid;
	grid-template-columns: minmax(9rem, 1fr) minmax(8rem, 0.8fr) minmax(0, 3fr) auto;
	align-items: center;
	gap: 1rem;
	width: 100%;
	padding: 1rem 1.1rem;
	text-align: left;
}

.ba-chip {
	display: inline-block;
	margin-top: 0.35rem;
	border-radius: 4px;
	padding: 0.1rem 0.45rem;
	color: #fff;
	font-size: 0.75rem;
	font-weight: 500;
}

.ba-box {
	border: 1px solid #e6e7e8;
	border-radius: 10px;
	padding: 0.6rem 0.85rem;
	background: #fff;
}

.ba-dist {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 0.75rem;
}

.ba-chev {
	width: 1.1rem;
	height: 1.1rem;
	color: var(--il-muted);
	transition: transform 0.15s ease;
}

.ba-body {
	border-top: 1px solid rgba(0, 0, 0, 0.06);
	padding: 1rem 1.1rem 1.1rem;
	background: #fff;
}

@media (max-width: 900px) {
	.ba-head {
		grid-template-columns: 1fr auto;
	}

	.ba-main,
	.ba-dist {
		grid-column: 1 / -1;
	}

	.ba-dist {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.ba-chev {
		grid-row: 1;
		grid-column: 2;
	}
}
</style>
