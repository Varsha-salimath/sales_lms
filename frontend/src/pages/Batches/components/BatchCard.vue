<template>
	<div
		class="flex flex-col border hover:border-outline-gray-3 rounded-md h-full"
		style="min-height: 150px"
	>
		<router-link
			:to="{ name: 'BatchDetail', params: { batchName: batch.name } }"
			class="flex flex-col flex-1 p-4"
		>
			<div class="text-lg leading-5 font-semibold mb-2 text-ink-gray-9">
				{{ batch.title }}
			</div>
			<Badge
				v-if="batch.seat_count && batch.seats_left > 0"
				variant="subtle"
				theme="green"
				size="md"
				class="self-start"
				:label="
					batch.seats_left +
					' ' +
					(batch.seats_left > 1 ? __('Seats Left') : __('Seat Left'))
				"
			/>
			<Badge
				v-else-if="batch.seat_count && batch.seats_left <= 0"
				variant="subtle"
				theme="red"
				size="md"
				class="self-start"
				:label="__('Sold Out')"
			/>
			<div class="short-introduction text-sm text-ink-gray-7">
				{{ batch.description }}
			</div>
			<div v-if="batch.amount" class="font-semibold text-ink-gray-9 mb-4">
				{{ batch.price }}
			</div>
			<div class="flex flex-col space-y-2 mt-auto">
				<DateRange
					:startDate="batch.start_date"
					:endDate="batch.end_date"
					class="text-sm text-ink-gray-7"
				/>
				<div class="flex items-center text-sm text-ink-gray-7">
					<Clock class="h-4 w-4 stroke-1.5 me-2 text-ink-gray-7" />
					<span dir="ltr">
						{{ formatTime(batch.start_time) }} - {{ formatTime(batch.end_time) }}
					</span>
				</div>
				<div
					v-if="batch.timezone"
					class="flex items-center text-sm text-ink-gray-7"
				>
					<Globe class="h-4 w-4 stroke-1.5 me-2 text-ink-gray-5" />
					<span>
						{{ batch.timezone }}
					</span>
				</div>
			</div>
			<div
				v-if="batch.instructors?.length"
				class="flex avatar-group overlap mt-4"
			>
				<div
					class="h-6 me-1"
					:class="{ 'avatar-group overlap': batch.instructors.length > 1 }"
				>
					<UserAvatar
						v-for="instructor in batch.instructors"
						:user="instructor"
					/>
				</div>
				<CourseInstructors :instructors="batch.instructors" />
			</div>
		</router-link>
		<div
			v-if="showLeaderboardAction"
			class="border-t px-4 py-3"
		>
			<router-link
				:to="{
					name: 'BatchLeaderboard',
					params: { batchName: batch.name },
				}"
				class="flex items-center gap-2 text-sm font-medium text-ink-gray-8 hover:text-ink-gray-9 transition-colors"
				@click.stop
			>
				<Trophy class="w-4 h-4 stroke-1.5" style="color: #ef9f27" />
				{{ __('View Leaderboard') }}
				<ArrowRight class="w-3.5 h-3.5 stroke-1.5 ms-auto text-ink-gray-5" />
			</router-link>
		</div>
	</div>
</template>
<script setup>
import { Badge } from 'frappe-ui'
import { formatTime } from '@/utils'
import { ArrowRight, Clock, Globe, Trophy } from 'lucide-vue-next'
import DateRange from '@/components/Common/DateRange.vue'
import CourseInstructors from '@/components/CourseInstructors.vue'
import UserAvatar from '@/components/UserAvatar.vue'

defineProps({
	batch: {
		type: Object,
		default: null,
	},
	showLeaderboardAction: {
		type: Boolean,
		default: false,
	},
})
</script>
<style>
.short-introduction {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	text-overflow: ellipsis;
	width: 100%;
	overflow: hidden;
	margin: 0.25rem 0 1rem;
	line-height: 1.5;
}

.avatar-group {
	display: inline-flex;
	align-items: center;
}

.avatar-group .avatar {
	transition: margin 0.1s ease-in-out;
}

.avatar-group.overlap .avatar + .avatar {
	margin-inline-start: calc(-8px);
}
</style>
