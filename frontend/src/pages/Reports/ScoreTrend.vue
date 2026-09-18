<template>
	<div class="st-card">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h3 class="text-lg font-normal text-[color:var(--il-ink)]">{{ title }}</h3>
			<div v-if="modes.length > 1" class="st-seg">
				<button v-for="m in modes" :key="m.key" type="button" :class="{ 'is-active': mode === m.key }" @click="mode = m.key">
					{{ m.label }}
				</button>
			</div>
		</div>

		<div class="st-chart" @mouseleave="hover = null">
			<div class="st-y">
				<span v-for="t in [100, 75, 50, 25, 0]" :key="t" :style="{ bottom: `${t}%` }">{{ t }}%</span>
			</div>
			<div class="st-plot">
				<div v-for="g in [0, 25, 50, 75, 100]" :key="g" class="st-grid" :style="{ bottom: `${g}%` }" />
				<div class="st-bars">
					<div
						v-for="(b, i) in items"
						:key="b.label"
						class="st-col"
						:class="{ 'is-hover': hover === i }"
						@mouseenter="hover = i"
					>
						<div class="st-pair">
							<div
								class="st-bar"
								:class="{ 'is-empty': b.value == null }"
								:style="{ height: `${b.value ?? 3}%`, background: b.value == null ? '#E6E7E8' : hover === i ? '#00254C' : '#027BFF' }"
							/>
							<div v-if="compareOf(b) != null" class="st-bar is-compare" :style="{ height: `${compareOf(b)}%` }" />
						</div>
						<Star v-if="i === bestIndex" class="st-star" :style="{ bottom: `calc(${b.value}% + 6px)` }" />
						<div class="st-label">{{ b.short || b.label }}</div>
						<div v-if="hover === i" class="st-tip" :class="{ 'is-left': i > items.length / 2 }">
							<div class="font-medium text-[color:var(--il-ink)]">{{ b.label }}</div>
							<div class="mt-1 grid grid-cols-[auto_auto] gap-x-3 text-xs">
								<span class="text-[color:var(--il-muted)]">{{ valueLabel }}</span>
								<span class="font-semibold text-[color:var(--il-primary-40)]">{{ b.display ?? pct(b.value) }}</span>
								<template v-if="compareOf(b) != null">
									<span class="text-[color:var(--il-muted)]">{{ activeMode.label }}</span>
									<span class="font-semibold text-[color:var(--il-ink)]">{{ pct(compareOf(b)) }}</span>
								</template>
								<template v-for="r in b.extra || []" :key="r.label">
									<span class="text-[color:var(--il-muted)]">{{ r.label }}</span>
									<span class="font-semibold text-[color:var(--il-ink)]">{{ r.value }}</span>
								</template>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="mt-2 flex flex-wrap items-center gap-4 text-xs text-[color:var(--il-muted)]">
			<span class="inline-flex items-center gap-1"><Star class="h-3.5 w-3.5 fill-[#FF8A00] text-[#FF8A00]" /> {{ bestLabel }}</span>
			<span v-if="compareOf(items[0] || {}) != null" class="inline-flex items-center gap-1">
				<span class="h-2.5 w-2.5 rounded-sm bg-[#B8D9FF]" /> {{ activeMode.label }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Star } from 'lucide-vue-next'

// PTM "Score Trend" bars. Items: { label, short?, value (0–100), compare: { [modeKey]: 0–100 }, display?, extra? }.
const props = defineProps({
	title: { type: String, default: 'Score trend' },
	items: { type: Array, default: () => [] },
	modes: { type: Array, default: () => [] }, // [{ key, label }]; first is "value only"
	valueLabel: { type: String, default: 'Score' },
	bestLabel: { type: String, default: 'Best score' },
})

const mode = ref(props.modes[0]?.key)
const hover = ref(null)
const activeMode = computed(() => props.modes.find((m) => m.key === mode.value) || {})

const bestIndex = computed(() => {
	let best = -1
	props.items.forEach((b, i) => {
		if (b.value != null && (best < 0 || b.value > props.items[best].value)) best = i
	})
	return best
})

function compareOf(b) {
	return b.compare?.[mode.value] ?? null
}

function pct(v) {
	return v == null ? '—' : `${Math.round(v * 10) / 10}%`
}
</script>

<style scoped>
.st-card {
	border: 1px solid #edf0f4;
	border-radius: 16px;
	padding: 1rem 1.1rem;
	background: #fff;
	box-shadow: 0 1px 6px rgba(0, 37, 76, 0.05);
}

.st-seg {
	display: inline-flex;
	gap: 0.25rem;
	border-radius: 999px;
	padding: 0.2rem;
	background: #fff;
	box-shadow: 0 1px 6px rgba(0, 37, 76, 0.12);
}

.st-seg button {
	border-radius: 999px;
	padding: 0.3rem 0.8rem;
	color: var(--il-primary-20);
	font-size: 0.75rem;
	font-weight: 500;
}

.st-seg button.is-active {
	background: #00254c;
	color: #fff;
}

.st-chart {
	display: flex;
	gap: 0.5rem;
	margin-top: 1.25rem;
}

.st-y {
	position: relative;
	width: 2.1rem;
	height: 12rem;
	flex-shrink: 0;
	color: var(--il-neutral-60);
	font-size: 0.6875rem;
}

.st-y span {
	position: absolute;
	right: 0;
	transform: translateY(50%);
}

.st-plot {
	position: relative;
	flex: 1;
	height: 12rem;
}

.st-grid {
	position: absolute;
	left: 0;
	right: 0;
	border-top: 1px dashed #e6e7e8;
}

.st-bars {
	position: absolute;
	inset: 0;
	display: flex;
	justify-content: space-around;
	gap: 0.5rem;
}

.st-col {
	position: relative;
	display: flex;
	flex: 1;
	max-width: 5.5rem;
	justify-content: center;
	border-radius: 8px 8px 0 0;
}

.st-col.is-hover {
	background: rgba(2, 123, 255, 0.06);
}

.st-pair {
	display: flex;
	align-items: flex-end;
	gap: 3px;
	height: 100%;
}

.st-bar {
	width: 1.35rem;
	border-radius: 3px 3px 0 0;
	transition: height 0.3s ease, background 0.15s ease;
}

.st-bar.is-compare {
	background: #b8d9ff;
}

.st-star {
	position: absolute;
	left: 50%;
	width: 1rem;
	height: 1rem;
	margin-left: -0.5rem;
	color: #ff8a00;
	fill: #ff8a00;
}

.st-label {
	position: absolute;
	top: calc(100% + 0.4rem);
	width: 100%;
	overflow: hidden;
	color: var(--il-ink);
	font-size: 0.6875rem;
	text-align: center;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.st-tip {
	position: absolute;
	z-index: 5;
	top: 0.5rem;
	left: 70%;
	min-width: 11rem;
	border-radius: 12px;
	padding: 0.6rem 0.8rem;
	background: #fff;
	box-shadow: 0 6px 24px rgba(0, 37, 76, 0.18);
	font-size: 0.8125rem;
	pointer-events: none;
}

.st-tip.is-left {
	left: auto;
	right: 70%;
}

.st-card > .flex:last-child {
	margin-top: 2rem;
}
</style>
