<template>
	<div>
		<div class="qc-legend">
			<span class="text-xs text-[color:var(--il-muted)]">{{ legendTitle }}</span>
			<div class="mt-2 grid gap-x-5 gap-y-2 sm:grid-cols-2 xl:grid-cols-4">
				<div v-for="q in quadrants" :key="q.key">
					<div class="inline-flex items-center gap-1.5 text-xs font-medium" :style="{ color: q.ink }">
						<span class="h-2.5 w-2.5 rounded-full" :style="{ background: q.dot }" />
						{{ q.title }} · {{ counts[q.key] }}
					</div>
					<div class="ps-4 text-[11px] text-[color:var(--il-muted)]">{{ q.hint }}</div>
				</div>
			</div>
		</div>

		<div class="qc-wrap">
			<div class="qc-y">
				<span v-for="t in [100, 75, 50, 25, 0]" :key="t" :style="{ bottom: `${t}%` }">{{ t }}%</span>
			</div>
			<div class="qc-plot" @mouseleave="hover = null">
				<div
					v-for="q in quadrants"
					:key="q.key"
					class="qc-zone"
					:style="zoneStyle(q)"
				>
					<div class="qc-zone-label" :class="`is-${q.key}`" :style="{ color: q.ink }">{{ q.title }}</div>
				</div>
				<div v-for="g in [25, 50, 75]" :key="g" class="qc-grid" :style="{ bottom: `${g}%` }" />
				<button
					v-for="p in placed"
					:key="p.id"
					type="button"
					class="qc-dot"
					:style="{ left: `${p.x}%`, bottom: `${p.y}%`, background: quadrantOf(p).dot }"
					:aria-label="p.label"
					@mouseenter="hover = p"
					@focus="hover = p"
					@click="$emit('select', p)"
				/>
				<div v-if="hover" class="qc-tip" :style="tipStyle(hover)">
					<div class="font-medium text-[color:var(--il-ink)]">{{ hover.label }}</div>
					<div v-for="r in hover.rows || []" :key="r.label" class="mt-1 flex justify-between gap-4 text-xs">
						<span class="text-[color:var(--il-muted)]">{{ r.label }}</span>
						<span class="font-semibold" :style="{ color: r.color || 'var(--il-ink)' }">{{ r.value }}</span>
					</div>
					<div class="mt-1.5 text-xs font-medium" :style="{ color: quadrantOf(hover).ink }">{{ quadrantOf(hover).title }}</div>
				</div>
			</div>
		</div>
		<div class="qc-x">
			<span v-for="t in [0, 25, 50, 75, 100]" :key="t">{{ t }}%</span>
		</div>
		<div class="mt-1 flex justify-between text-[11px] text-[color:var(--il-muted)]">
			<span>↑ {{ yLabel }}</span>
			<span>{{ xLabel }} →</span>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'

// "Performance by score" quadrant from the PTM board. Points: { id, label, x, y, rows } with x/y in 0–100.
const props = defineProps({
	points: { type: Array, default: () => [] },
	threshold: { type: Number, default: 75 },
	xLabel: { type: String, default: '' },
	yLabel: { type: String, default: '' },
	legendTitle: { type: String, default: '' },
	// [top-right, top-left, bottom-right, bottom-left] copy
	labels: { type: Array, required: true },
})
defineEmits(['select'])

const hover = ref(null)
const tones = [
	{ key: 'tr', bg: '#DDF6E4', dot: '#0F6B2E', ink: '#0F6B2E' },
	{ key: 'tl', bg: '#FDF6DA', dot: '#8C7A1E', ink: '#7A6A12' },
	{ key: 'br', bg: '#FCE4E4', dot: '#9E1C1C', ink: '#9E1C1C' },
	{ key: 'bl', bg: '#FFFFFF', dot: '#9A9C9F', ink: '#4D5054' },
]
const quadrants = computed(() => tones.map((t, i) => ({ ...t, ...props.labels[i] })))

// Nudge overlapping dots apart a little so every learner stays hoverable.
const placed = computed(() => {
	const seen = {}
	return props.points
		.filter((p) => p.x != null && p.y != null)
		.map((p) => {
			const key = `${Math.round(p.x / 2)}:${Math.round(p.y / 2)}`
			const n = (seen[key] = (seen[key] || 0) + 1) - 1
			const clamp = (v) => Math.max(1.5, Math.min(98.5, v))
			return { ...p, x: clamp(p.x + (n % 3) * 1.4), y: clamp(p.y + Math.floor(n / 3) * 1.8), rawX: p.x, rawY: p.y }
		})
})

function quadrantOf(p) {
	const x = (p.rawX ?? p.x) >= props.threshold
	const y = (p.rawY ?? p.y) >= props.threshold
	return quadrants.value[y ? (x ? 0 : 1) : x ? 2 : 3]
}

const counts = computed(() => {
	const c = { tr: 0, tl: 0, br: 0, bl: 0 }
	placed.value.forEach((p) => c[quadrantOf(p).key]++)
	return c
})

function zoneStyle(q) {
	const t = props.threshold
	const right = q.key.endsWith('r')
	const top = q.key.startsWith('t')
	return {
		background: q.bg,
		left: right ? `${t}%` : 0,
		width: right ? `${100 - t}%` : `${t}%`,
		bottom: top ? `${t}%` : 0,
		height: top ? `${100 - t}%` : `${t}%`,
	}
}

function tipStyle(p) {
	const style = { bottom: `calc(${p.y}% + 14px)` }
	if (p.x > 60) style.right = `calc(${100 - p.x}% - 10px)`
	else style.left = `calc(${p.x}% - 10px)`
	return style
}
</script>

<style scoped>
.qc-legend {
	border: 1px solid #edf0f4;
	border-radius: 14px;
	padding: 0.7rem 1rem;
	background: #fff;
}

.qc-wrap {
	display: flex;
	gap: 0.5rem;
	margin-top: 1rem;
}

.qc-y {
	position: relative;
	width: 2.1rem;
	height: 22rem;
	flex-shrink: 0;
	color: var(--il-neutral-60);
	font-size: 0.6875rem;
}

.qc-y span {
	position: absolute;
	right: 0;
	transform: translateY(50%);
}

.qc-plot {
	position: relative;
	flex: 1;
	height: 22rem;
	overflow: visible;
	border: 1px solid #e6e7e8;
	border-radius: 14px;
	background: #fff;
}

.qc-zone {
	position: absolute;
}

.qc-zone:first-child {
	border-top-right-radius: 13px;
}

.qc-zone-label {
	position: absolute;
	font-size: 0.6875rem;
	font-weight: 500;
	opacity: 0.85;
	white-space: nowrap;
	pointer-events: none;
}

.qc-zone-label.is-tl,
.qc-zone-label.is-tr {
	top: 0.4rem;
}

.qc-zone-label.is-bl,
.qc-zone-label.is-br {
	bottom: 0.4rem;
}

.qc-zone-label.is-tl,
.qc-zone-label.is-bl {
	left: 0.6rem;
}

.qc-zone-label.is-tr,
.qc-zone-label.is-br {
	right: 0.6rem;
}

.qc-grid {
	position: absolute;
	left: 0;
	right: 0;
	border-top: 1px dashed rgba(0, 0, 0, 0.08);
	pointer-events: none;
}

.qc-dot {
	position: absolute;
	z-index: 2;
	width: 0.95rem;
	height: 0.95rem;
	border: 2px solid #fff;
	border-radius: 999px;
	transform: translate(-50%, 50%);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
	transition: transform 0.12s ease;
}

.qc-dot:hover,
.qc-dot:focus-visible {
	transform: translate(-50%, 50%) scale(1.35);
	outline: none;
}

.qc-tip {
	position: absolute;
	z-index: 5;
	min-width: 11rem;
	border-radius: 12px;
	padding: 0.65rem 0.8rem;
	background: #fff;
	box-shadow: 0 6px 24px rgba(0, 37, 76, 0.18);
	font-size: 0.8125rem;
	pointer-events: none;
}

.qc-x {
	display: flex;
	justify-content: space-between;
	margin: 0.35rem 0 0 2.4rem;
	color: var(--il-neutral-60);
	font-size: 0.6875rem;
}

@media (max-width: 640px) {
	.qc-y,
	.qc-plot {
		height: 17rem;
	}

	.qc-zone-label {
		display: none;
	}
}
</style>
