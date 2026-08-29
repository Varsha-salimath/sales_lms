<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Learning activity'),
			size: '3xl',
		}"
	>
		<template #body-content>
			<div class="text-base space-y-8">
				<div>
					<div class="text-center">
						<div class="text-[30px]">🔥</div>
						<div class="mt-3">
							<div class="text-ink-gray-5 mb-1">
								{{
									streakInfo.data?.current_streak < 1
										? __('You can do better,')
										: streakInfo.data?.current_streak < 10
											? __('Keep going,')
											: __('You rock,')
								}}
								{{ __(' you are on a') }}
							</div>
							<div class="font-semibold text-xl text-ink-gray-9">
								{{ streakInfo.data?.current_streak }} {{ __('day streak') }}
							</div>
						</div>
					</div>

					<div
						class="grid grid-cols-2 bg-surface-gray-1 px-2.5 py-2 rounded-md mt-8"
					>
						<div class="space-y-1 border-e border-outline-gray-2 me-4">
							<div class="text-ink-gray-6">{{ __('Current Streak') }}</div>
							<div class="font-semibold text-lg text-ink-gray-9">
								{{ streakInfo.data?.current_streak }} {{ __('days') }}
							</div>
						</div>
						<div class="space-y-1">
							<div class="text-ink-gray-6">{{ __('Longest Streak') }}</div>
							<div class="font-semibold text-lg text-ink-gray-9">
								{{ streakInfo.data?.longest_streak }} {{ __('days') }}
							</div>
						</div>
					</div>

					<div
						class="text-ink-gray-7 border border-outline-gray-1 px-2.5 py-2 rounded-md text-xs leading-5 mt-5"
					>
						{{
							__(
								'Your learning streak counts the number of days in a row you’ve kept up your learning, whether it’s a lesson, quiz, or assignment. Don’t worry, weekends don’t break your streak.'
							)
						}}
					</div>
				</div>

				<div class="border-t border-outline-gray-2 pt-6">
					<h3 class="text-sm font-semibold text-ink-gray-9 mb-4">
						{{ __('Time on platform') }}
					</h3>

					<div
						v-if="timeTracking?.loading && !timeTracking?.data"
						class="text-sm text-ink-gray-6 py-4 text-center"
					>
						{{ __('Loading time tracking...') }}
					</div>

					<div v-else-if="timeTracking?.data" class="space-y-4">
						<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
							<div
								v-for="card in timeTracking.data.summary_cards"
								:key="card.key"
								class="rounded-lg border bg-surface-gray-1 px-4 py-3"
							>
								<div class="text-xs text-ink-gray-6 mb-1">{{ __(card.label) }}</div>
								<div class="text-lg font-semibold text-ink-gray-9 tabular-nums">
									{{ card.display }}
								</div>
								<div class="text-xs text-ink-gray-5 mt-0.5">{{ card.subtext }}</div>
							</div>
						</div>

						<ActivityHeatmap
							v-if="user.data?.name"
							:user-id="user.data.name"
						/>

						<p class="text-xs text-ink-gray-6 leading-5">
							{{
								__(
									'Active time is tracked while you are focused on the LMS and interacting — not just logged in. Percentages show where your learning time goes.'
								)
							}}
						</p>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { Dialog } from 'frappe-ui'
import { inject, watch } from 'vue'
import ActivityHeatmap from '@/components/Analytics/ActivityHeatmap.vue'

const show = defineModel<boolean>({
	default: false,
})

const props = defineProps<{
	streakInfo: {
		data?: {
			current_streak: number
			longest_streak: number
		}
	}
	timeTracking?: {
		data?: {
			summary_cards?: Array<{
				key: string
				label: string
				display: string
				subtext: string
			}>
			heatmap?: Array<{ date: string; minutes: number; level: number }>
		}
		loading?: boolean
		reload?: () => void
	}
}>()

const user = inject<any>('$user')

watch(show, (open) => {
	if (open) {
		props.timeTracking?.reload?.()
	}
})
</script>
