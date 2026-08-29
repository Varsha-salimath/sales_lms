<template>
	<div>
		<!-- Loading -->
		<div v-if="leaderboard.loading && !leaderboard.data" class="space-y-5">
			<div class="animate-pulse rounded-lg border p-5 space-y-3">
				<div class="h-6 bg-surface-gray-2 rounded w-1/2" />
				<div class="h-4 bg-surface-gray-2 rounded w-1/3" />
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
				<div
					v-for="i in 3"
					:key="i"
					class="animate-pulse rounded-lg border p-4 h-20 bg-surface-gray-1"
				/>
			</div>
			<div
				v-for="i in 5"
				:key="'row-' + i"
				class="animate-pulse rounded-lg border p-4 h-14 bg-surface-gray-1"
			/>
		</div>

		<!-- Error -->
		<div
			v-else-if="leaderboard.error"
			class="flex flex-col items-center justify-center py-16 gap-3"
		>
			<p class="text-ink-gray-7 text-center">
				{{ __('Something went wrong loading the leaderboard.') }}
			</p>
			<Button @click="leaderboard.reload()">
				{{ __('Try again') }}
			</Button>
		</div>

		<!-- Populated -->
		<div v-else-if="leaderboard.data" class="space-y-6">
			<!-- Batch Header -->
			<div
				class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3"
			>
				<div>
					<h2 class="text-xl font-semibold text-ink-gray-9">
						{{ headerTitle }}
					</h2>
					<p class="text-sm text-ink-gray-6 mt-1">
						{{ leaderboard.data.total_members }}
						{{
							leaderboard.data.total_members === 1
								? __('batchmate')
								: __('batchmates')
						}}
						•
						{{ __('Started') }}
						{{ formatDate(leaderboard.data.start_date) }}
						•
						{{ leaderboard.data.total_lessons }}
						{{
							leaderboard.data.total_lessons === 1
								? __('lesson total')
								: __('lessons total')
						}}
					</p>
				</div>
				<Badge theme="green" variant="subtle" class="self-start">
					{{ __('Enrolled') }}
				</Badge>
			</div>

			<!-- Summary Cards -->
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
				<div class="rounded-lg border p-4">
					<div class="text-xs font-medium text-ink-gray-6 uppercase tracking-wide">
						{{ __('Your rank') }}
					</div>
					<div class="text-2xl font-semibold text-ink-gray-9 mt-1">
						<template v-if="stats.yourRank">
							#{{ stats.yourRank }}
							<span class="text-sm font-normal text-ink-gray-6">
								{{ __('out of') }} {{ leaderboard.data.total_members }}
							</span>
						</template>
						<template v-else>—</template>
					</div>
				</div>
				<div class="rounded-lg border p-4">
					<div class="text-xs font-medium text-ink-gray-6 uppercase tracking-wide">
						{{ __('Your progress') }}
					</div>
					<div class="text-2xl font-semibold text-ink-gray-9 mt-1">
						{{ stats.yourProgress }}%
					</div>
					<div class="text-sm text-ink-gray-6">
						{{ stats.yourLessonsCompleted }} {{ __('of') }}
						{{ stats.totalLessons }} {{ __('lessons') }}
					</div>
				</div>
				<div class="rounded-lg border p-4">
					<div class="text-xs font-medium text-ink-gray-6 uppercase tracking-wide">
						{{ __('Batch avg completion') }}
					</div>
					<div class="text-2xl font-semibold text-ink-gray-9 mt-1">
						{{ stats.batchAverage }}%
					</div>
				</div>
			</div>

			<!-- Your Position Card -->
			<div
				v-if="stats.currentUser"
				class="rounded-lg border-2 p-4 flex items-center gap-4"
				style="border-color: #1d9e75; background-color: #f0faf6"
			>
				<div
					class="text-3xl font-bold shrink-0 w-12 text-center"
					style="color: #1d9e75"
				>
					#{{ stats.yourRank }}
				</div>
				<div
					class="flex items-center justify-center rounded-full w-10 h-10 text-sm font-semibold shrink-0"
					:style="{
						backgroundColor: getAvatarColor(stats.currentUser.full_name).bg,
						color: getAvatarColor(stats.currentUser.full_name).text,
					}"
				>
					{{ getInitials(stats.currentUser.full_name) }}
				</div>
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2">
						<span class="font-semibold text-ink-gray-9">
							{{ stats.currentUser.full_name }}
						</span>
						<span
							class="text-xs font-medium px-2 py-0.5 rounded"
							style="background-color: #1d9e75; color: white"
						>
							{{ __('You') }}
						</span>
					</div>
					<div class="text-sm text-ink-gray-6">
						{{ stats.currentUser.lessons_completed }}
						{{ __('of') }} {{ stats.totalLessons }}
						{{ __('lessons done') }}
					</div>
				</div>
				<div class="text-lg font-semibold text-ink-gray-9 shrink-0">
					{{ stats.yourProgress }}%
				</div>
			</div>

			<!-- Leaderboard List -->
			<div>
				<div
					class="text-xs font-semibold text-ink-gray-6 uppercase tracking-wide mb-3"
				>
					{{ __('Batchmates — ranked by progress') }}
				</div>
				<div class="rounded-lg border divide-y">
					<div
						v-for="(member, index) in sortedBatchmates"
						:key="member.user_id"
						class="flex items-center gap-3 px-4 py-3"
						:class="member.is_current_user ? 'bg-green-50' : ''"
					>
						<!-- Rank -->
						<div class="w-8 shrink-0 flex items-center justify-center">
							<Trophy
								v-if="index === 0"
								class="w-5 h-5 stroke-1.5"
								style="color: #ef9f27"
							/>
							<Medal
								v-else-if="index === 1 || index === 2"
								class="w-5 h-5 stroke-1.5"
								style="color: #9ca3af"
							/>
							<span v-else class="text-sm font-medium text-ink-gray-6">
								{{ index + 1 }}
							</span>
						</div>

						<!-- Avatar -->
						<div
							class="flex items-center justify-center rounded-full w-9 h-9 text-xs font-semibold shrink-0"
							:style="{
								backgroundColor: getAvatarColor(member.full_name).bg,
								color: getAvatarColor(member.full_name).text,
							}"
						>
							{{ getInitials(member.full_name) }}
						</div>

						<!-- Name + lessons -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="font-medium text-ink-gray-9 truncate">
									{{ member.full_name }}
								</span>
								<span
									v-if="member.is_current_user"
									class="text-xs font-medium px-1.5 py-0.5 rounded shrink-0"
									style="background-color: #1d9e75; color: white"
								>
									{{ __('You') }}
								</span>
							</div>
							<div class="text-xs text-ink-gray-6">
								{{ member.lessons_completed }}
								{{ __('of') }} {{ stats.totalLessons }}
								{{ __('lessons') }}
							</div>
						</div>

						<!-- Progress % + bar -->
						<div class="flex items-center gap-3 shrink-0 w-32 sm:w-40">
							<span class="text-sm font-medium text-ink-gray-7 w-8 text-right">
								{{ Math.round(member.completion_pct) }}%
							</span>
							<div
								class="flex-1 bg-surface-gray-3 rounded-full h-2 min-w-0"
								style="min-width: 0"
							>
								<div
									class="h-2 rounded-full transition-all"
									:style="{
										width: `${Math.min(member.completion_pct, 100)}%`,
										backgroundColor: getProgressBarColor(
											member.completion_pct,
											member.is_current_user
										),
										minWidth: member.completion_pct > 0 ? '2px' : '0',
									}"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Link to batch details (inline mode) -->
			<div v-if="showBatchDetailsLink" class="flex justify-end">
				<router-link
					:to="{
						name: 'BatchDetail',
						params: { batchName: batchName },
					}"
					class="text-sm text-ink-gray-7 hover:text-ink-gray-9 flex items-center gap-1"
				>
					{{ __('Batch details') }}
					<ArrowRight class="w-4 h-4 stroke-1.5" />
				</router-link>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button, createResource } from 'frappe-ui'
import { computed, inject, watch } from 'vue'
import { ArrowRight, Medal, Trophy } from 'lucide-vue-next'
import {
	computeLeaderboardStats,
	getAvatarColor,
	getInitials,
	getProgressBarColor,
	sortBatchmates,
} from '@/pages/Batches/utils/leaderboard.js'

const props = defineProps({
	batchName: {
		type: String,
		required: true,
	},
	showBatchDetailsLink: {
		type: Boolean,
		default: false,
	},
})

const dayjs = inject('$dayjs')

const leaderboard = createResource({
	url: 'lms.lms.api.get_batch_leaderboard',
	makeParams() {
		return { batch: props.batchName }
	},
	auto: true,
})

watch(
	() => props.batchName,
	() => {
		leaderboard.reload()
	}
)

const sortedBatchmates = computed(() => {
	if (!leaderboard.data?.batchmates) return []
	return sortBatchmates(leaderboard.data.batchmates)
})

const stats = computed(() => {
	return computeLeaderboardStats(
		sortedBatchmates.value,
		leaderboard.data?.total_lessons || 0
	)
})

const headerTitle = computed(() => {
	if (!leaderboard.data) return ''
	const { course_name, batch_name } = leaderboard.data
	if (course_name && batch_name) {
		return `${course_name} — ${batch_name}`
	}
	return batch_name || course_name
})

const formatDate = (date) => {
	if (!date) return ''
	return dayjs(date).format('DD MMM YYYY')
}
</script>
