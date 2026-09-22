<template>
	<div class="space-y-6">
		<div>
			<h2 class="text-base font-semibold text-ink-gray-9">
				{{ __('Operations') }}
			</h2>
			<p class="text-xs text-ink-gray-6 mt-1">
				{{
					__(
						'Quick actions, courses, certificates, and recent user activity.'
					)
				}}
			</p>
		</div>

		<section>
			<h3 class="mb-2.5 text-sm font-semibold text-ink-gray-8">
				{{ __('Quick Actions') }}
			</h3>
			<div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
				<button
					v-for="action in quickActions"
					:key="action.key"
					type="button"
					class="flex items-center gap-3 rounded-lg border bg-surface-white px-3 py-3 text-left shadow-sm transition-colors hover:bg-surface-gray-1"
					@click="action.onClick"
				>
					<div
						class="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-blue-1 text-ink-blue-3"
					>
						<component :is="action.icon" class="size-4" />
					</div>
					<span class="text-sm font-medium text-ink-gray-9">
						{{ action.label }}
					</span>
				</button>
			</div>
		</section>

		<section class="border rounded-lg bg-surface-white p-4 sm:p-5">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<div>
					<h3 class="text-base font-semibold text-ink-gray-9">
						{{ __('Courses Created') }}
					</h3>
					<p class="text-xs text-ink-gray-6">
						{{ __('Courses available in Sales CRT') }}
					</p>
				</div>
				<router-link
					:to="{ name: 'Courses' }"
					class="text-sm font-semibold text-ink-blue-3 hover:underline"
				>
					{{ __('View all') }}
				</router-link>
			</div>
			<div
				v-if="createdCourses.loading"
				class="py-10 text-center text-sm text-ink-gray-6"
			>
				{{ __('Loading courses…') }}
			</div>
			<div
				v-else-if="courseCards.length"
				class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
			>
				<router-link
					v-for="course in courseCards"
					:key="course.name"
					:to="{
						name: 'GeniusCourseDetail',
						params: { courseName: course.name },
					}"
					class="block overflow-hidden rounded-xl border bg-white shadow-sm"
				>
					<CourseCard :course="course" />
				</router-link>
			</div>
			<div v-else class="py-10 text-center text-sm text-ink-gray-6">
				{{ __('No courses created yet.') }}
				<button
					type="button"
					class="ms-2 font-semibold text-ink-blue-3 hover:underline"
					@click="router.push({ name: 'Courses', query: { newCourse: '1' } })"
				>
					{{ __('Create Course') }}
				</button>
			</div>
		</section>

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<section class="border rounded-lg bg-surface-white p-4 sm:p-5 flex flex-col">
				<div class="mb-3 flex items-center justify-between">
					<h3 class="text-base font-semibold text-ink-gray-9">
						{{ __('Certified Users') }}
					</h3>
					<router-link
						:to="{ name: 'CertifiedParticipants' }"
						class="text-xs font-semibold text-ink-blue-3 hover:underline"
					>
						{{ __('View all') }}
					</router-link>
				</div>
				<ul v-if="certificates.loading" class="py-8 text-center text-sm text-ink-gray-6">
					{{ __('Loading certificates…') }}
				</ul>
				<ul v-else-if="certifiedUsers.length" class="space-y-2.5">
					<li
						v-for="item in certifiedUsers"
						:key="item.name"
						class="flex gap-3 rounded-lg border px-3 py-2.5"
					>
						<div class="mt-1 size-2 shrink-0 rounded-full bg-teal-500" />
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center justify-between gap-1">
								<p class="text-sm font-semibold text-ink-gray-9">
									{{ item.member_name || item.member }}
								</p>
								<span class="text-[11px] text-ink-gray-5">
									{{ formatDate(item.issue_date) }}
								</span>
							</div>
							<p class="truncate text-xs text-ink-gray-6">
								{{ item.course_title || item.course }}
							</p>
						</div>
					</li>
				</ul>
				<div
					v-else
					class="flex flex-1 items-center justify-center py-10 text-sm text-ink-gray-6"
				>
					{{ __('No certificates issued yet.') }}
				</div>
			</section>

			<section class="border rounded-lg bg-surface-white p-4 sm:p-5">
				<div class="mb-3 flex items-center justify-between gap-2">
					<h3 class="text-base font-semibold text-ink-gray-9">
						{{ __('Recent Users') }}
					</h3>
					<button
						type="button"
						class="text-xs font-semibold text-ink-blue-3 hover:underline"
						@click="openSettings('Members')"
					>
						{{ __('Manage Users') }}
					</button>
				</div>
				<div
					v-if="recentUsersResource.loading"
					class="py-8 text-center text-sm text-ink-gray-6"
				>
					{{ __('Loading users…') }}
				</div>
				<div v-else class="overflow-x-auto">
					<table class="min-w-full text-left text-sm">
						<thead>
							<tr class="border-b text-[11px] uppercase tracking-wide text-ink-gray-5">
								<th class="pb-2 pr-3 font-medium">{{ __('Name') }}</th>
								<th class="pb-2 pr-3 font-medium">{{ __('Role') }}</th>
								<th class="pb-2 pr-3 font-medium">{{ __('Last Login') }}</th>
								<th class="pb-2 font-medium">{{ __('Status') }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in recentUsers"
								:key="row.name"
								class="border-b border-outline-gray-1 last:border-0"
							>
								<td class="py-2.5 pr-3">
									<div class="font-medium text-ink-gray-9">
										{{ row.full_name || row.name }}
									</div>
									<div class="text-[11px] text-ink-gray-5">
										{{ row.email || row.name }}
									</div>
								</td>
								<td class="py-2.5 pr-3 text-xs">{{ row.role || __('User') }}</td>
								<td class="py-2.5 pr-3 text-xs text-ink-gray-6">
									{{ formatDate(row.last_active) || __('Never') }}
								</td>
								<td class="py-2.5">
									<span
										class="rounded-full px-2 py-0.5 text-[11px] font-semibold"
										:class="
											row.enabled
												? 'bg-green-50 text-green-700'
												: 'bg-surface-gray-2 text-ink-gray-6'
										"
									>
										{{ row.enabled ? __('Active') : __('Inactive') }}
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div
					v-if="!recentUsersResource.loading && !recentUsers.length"
					class="py-8 text-center text-sm text-ink-gray-6"
				>
					{{ __('No users found.') }}
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Award, BarChart3, Layers, Plus, Users, UsersRound } from 'lucide-vue-next'
import CourseCard from '@/components/CourseCard.vue'
import { openSettings } from '@/utils'

const router = useRouter()

const createdCourses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	cache: ['analytics-operations-courses'],
	auto: true,
})

const certificates = createListResource({
	doctype: 'LMS Certificate',
	fields: ['name', 'member', 'member_name', 'course', 'course_title', 'issue_date'],
	orderBy: 'issue_date desc',
	pageLength: 8,
	auto: true,
	cache: ['analytics-operations-certificates'],
})

const recentUsersResource = createListResource({
	doctype: 'User',
	fields: ['name', 'full_name', 'email', 'last_active', 'enabled'],
	filters: { name: ['not in', ['Guest', 'Administrator']] },
	orderBy: 'last_active desc',
	pageLength: 8,
	auto: true,
	cache: ['analytics-operations-recent-users'],
})

const certifiedUsers = computed(() => certificates.data || [])
const recentUsers = computed(() => recentUsersResource.data || [])

const isDemoCourse = (course) => {
	const title = (course?.title || '').toLowerCase()
	return title.includes('frappe learning')
}

const courseCards = computed(() =>
	(createdCourses.data || []).filter((c) => !isDemoCourse(c)).slice(0, 8)
)

const formatDate = (value) => {
	if (!value) return ''
	try {
		return new Date(value).toLocaleDateString(undefined, {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
		})
	} catch {
		return value
	}
}

const quickActions = computed(() => [
	{
		key: 'course',
		label: __('Create Course'),
		icon: Plus,
		onClick: () => router.push({ name: 'Courses', query: { newCourse: '1' } }),
	},
	{
		key: 'program',
		label: __('Create Program'),
		icon: Layers,
		onClick: () => router.push({ name: 'Programs' }),
	},
	{
		key: 'batch',
		label: __('Create Batch'),
		icon: UsersRound,
		onClick: () => router.push({ name: 'Batches' }),
	},
	{
		key: 'users',
		label: __('Manage Users'),
		icon: Users,
		onClick: () => openSettings('Members'),
	},
	{
		key: 'certs',
		label: __('Issue Certificates'),
		icon: Award,
		onClick: () => router.push({ name: 'CertifiedParticipants' }),
	},
	{
		key: 'reports',
		label: __('Learner Reports'),
		icon: BarChart3,
		onClick: () => router.push({ name: 'LearnerReports' }),
	},
])
</script>
