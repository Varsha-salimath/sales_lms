<template>
	<div class="w-full min-w-[11rem]">
		<div class="px-2 pb-1 text-xs font-medium text-ink-gray-5">
			{{ __('Apps') }}
		</div>
		<button
			type="button"
			class="group flex h-8 w-full items-center gap-2 rounded px-2 text-base text-ink-gray-7 hover:bg-surface-gray-2"
			@click.stop.prevent="openDesk"
		>
			<LayoutGrid class="size-4 stroke-1.5" />
			<span>{{ __('Desk') }}</span>
		</button>
	</div>
</template>
<script setup>
import { LayoutGrid } from 'lucide-vue-next'

function openDesk() {
	window.location.href = '/desk'
}
</script>
