<template>
	<div class="genius-admin-dashboard min-h-full w-full px-4 pb-8 pt-4 sm:px-6 lg:px-8">
		<!-- Hero -->
		<section
			class="genius-hero-surface genius-fade-up mb-5 overflow-hidden rounded-2xl px-5 py-6 text-white sm:px-7 sm:py-7"
		>
			<div class="relative z-10 flex flex-wrap items-end justify-between gap-3">
				<div>
					<p class="mb-1 text-xs font-medium uppercase tracking-wide text-white/75">
						{{ __('Admin Portal') }}
					</p>
					<h1
						class="text-2xl font-semibold tracking-tight sm:text-3xl"
						style="color: #fff !important"
					>
						{{ __('LMS Control Center') }}
					</h1>
					<p class="mt-1.5 max-w-xl text-sm text-white/85">
						{{
							__(
								'Operational hub for courses, programs, learners, and certificates.'
							)
						}}
					</p>
				</div>
				<div class="text-sm text-white/80">
					{{ __('Welcome') }}{{ user.data?.full_name ? `, ${user.data.full_name}` : '' }}
				</div>
			</div>
		</section>

		<!-- KPIs -->
		<section class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
			<div
				v-for="kpi in kpiCards"
				:key="kpi.key"
				class="genius-card rounded-2xl p-4 shadow-sm"
			>
				<div class="mb-2 flex items-center justify-between">
					<div
						class="grid size-9 place-items-center rounded-xl"
						:style="{ background: kpi.tint, color: kpi.color }"
					>
						<component :is="kpi.icon" class="size-4" />
					</div>
					<span
						v-if="kpi.delta"
						class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
					>
						{{ kpi.delta }}
					</span>
				</div>
				<div class="text-2xl font-semibold tabular-nums text-[color:var(--genius-navy)]">
					{{ metricsLoading ? '—' : kpi.value }}
				</div>
				<div class="mt-0.5 text-xs text-[color:var(--genius-muted)]">
					{{ kpi.label }}
				</div>
			</div>
		</section>
		<p
			v-if="adminMetrics.error"
			class="mb-5 text-sm text-red-600"
		>
			{{ adminMetrics.error?.messages?.[0] || __('Failed to load dashboard metrics.') }}
		</p>

		<!-- Quick Actions -->
		<section class="mb-5">
			<h2 class="mb-2.5 text-base font-semibold text-[color:var(--genius-navy)]">
				{{ __('Quick Actions') }}
			</h2>
			<div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-6">
				<button
					v-for="action in quickActions"
					:key="action.key"
					type="button"
					class="genius-card genius-card-hover flex items-center gap-3 rounded-2xl px-3 py-3 text-left"
					@click="action.onClick"
				>
					<div
						class="grid size-9 shrink-0 place-items-center rounded-xl"
						style="background: var(--genius-blue-light); color: var(--genius-primary)"
					>
						<component :is="action.icon" class="size-4" />
					</div>
					<span class="text-sm font-semibold text-[color:var(--genius-navy)]">
						{{ action.label }}
					</span>
				</button>
			</div>
		</section>

		<!-- Courses Created -->
		<section class="mb-5">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<div>
					<h2 class="text-base font-semibold text-[color:var(--genius-navy)]">
						{{ __('Courses Created') }}
					</h2>
					<p class="text-xs text-[color:var(--genius-muted)]">
						{{ __('Courses available in Sales CRT') }}
					</p>
				</div>
				<router-link
					:to="{ name: 'Courses' }"
					class="text-sm font-semibold text-[color:var(--genius-blue)] hover:underline"
				>
					{{ __('View all') }}
				</router-link>
			</div>
			<div
				v-if="createdCourses.loading"
				class="genius-card rounded-2xl px-4 py-10 text-center text-sm text-[color:var(--genius-muted)]"
			>
				{{ __('Loading courses…') }}
			</div>
			<div
				v-else-if="courseCards.length"
				class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
			>
				<router-link
					v-for="course in courseCards"
					:key="course.name"
					:to="{
						name: 'GeniusCourseDetail',
						params: { courseName: course.name },
					}"
					class="block overflow-hidden rounded-2xl border bg-white shadow-sm"
					style="border-color: var(--genius-border)"
				>
					<CourseCard :course="course" />
				</router-link>
			</div>
			<div
				v-else
				class="genius-card rounded-2xl px-4 py-10 text-center text-sm text-[color:var(--genius-muted)]"
			>
				{{ __('No courses created yet.') }}
				<button
					type="button"
					class="ms-2 font-semibold text-[color:var(--genius-blue)] hover:underline"
					@click="router.push({ name: 'Courses', query: { newCourse: '1' } })"
				>
					{{ __('Create Course') }}
				</button>
			</div>
		</section>

		<!-- Certified Users + Recent Users -->
		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<section class="genius-card flex flex-col rounded-2xl p-4 sm:p-5">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-base font-semibold text-[color:var(--genius-navy)]">
						{{ __('Certified Users') }}
					</h2>
					<router-link
						:to="{ name: 'CertifiedParticipants' }"
						class="text-xs font-semibold text-[color:var(--genius-blue)] hover:underline"
					>
						{{ __('View all') }}
					</router-link>
				</div>
				<ul v-if="certificates.loading" class="space-y-2.5">
					<li
						class="rounded-xl border px-3 py-6 text-center text-sm text-[color:var(--genius-muted)]"
						style="border-color: var(--genius-border)"
					>
						{{ __('Loading certificates…') }}
					</li>
				</ul>
				<ul v-else-if="certifiedUsers.length" class="space-y-2.5">
					<li
						v-for="item in certifiedUsers"
						:key="item.name"
						class="flex gap-3 rounded-xl border px-3 py-2.5"
						style="border-color: var(--genius-border)"
					>
						<div
							class="mt-1 size-2 shrink-0 rounded-full"
							style="background: #0d9488"
						/>
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center justify-between gap-1">
								<p class="text-sm font-semibold text-[color:var(--genius-navy)]">
									{{ item.member_name || item.member }}
								</p>
								<span class="text-[11px] text-[color:var(--genius-muted)]">
									{{ formatIssueDate(item.issue_date) }}
								</span>
							</div>
							<p class="truncate text-xs text-[color:var(--genius-muted)]">
								{{ item.course_title || item.course }}
							</p>
						</div>
					</li>
				</ul>
				<div
					v-else
					class="flex flex-1 items-center justify-center py-10 text-sm text-[color:var(--genius-muted)]"
				>
					{{ __('No certificates issued yet.') }}
				</div>
			</section>

			<section class="genius-card rounded-2xl p-4 sm:p-5">
				<div class="mb-3 flex items-center justify-between gap-2">
					<h2 class="text-base font-semibold text-[color:var(--genius-navy)]">
						{{ __('Recent Users') }}
					</h2>
					<button
						type="button"
						class="text-xs font-semibold text-[color:var(--genius-blue)] hover:underline"
						@click="openSettings('Members')"
					>
						{{ __('Manage Users') }}
					</button>
				</div>
				<div
					v-if="recentUsersResource.loading"
					class="py-8 text-center text-sm text-[color:var(--genius-muted)]"
				>
					{{ __('Loading users…') }}
				</div>
				<div v-else class="overflow-x-auto">
					<table class="min-w-full text-left text-sm">
						<thead>
							<tr
								class="border-b text-[11px] uppercase tracking-wide text-[color:var(--genius-muted)]"
								style="border-color: var(--genius-border)"
							>
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
								class="border-b last:border-0"
								style="border-color: var(--genius-border)"
							>
								<td class="py-2.5 pr-3">
									<div class="font-medium text-[color:var(--genius-navy)]">
										{{ row.full_name || row.name }}
									</div>
									<div class="text-[11px] text-[color:var(--genius-muted)]">
										{{ row.email || row.name }}
									</div>
								</td>
								<td class="py-2.5 pr-3 text-xs">{{ row.role || __('User') }}</td>
								<td class="py-2.5 pr-3 text-xs text-[color:var(--genius-muted)]">
									{{ formatIssueDate(row.last_active) || __('Never') }}
								</td>
								<td class="py-2.5">
									<span
										class="rounded-full px-2 py-0.5 text-[11px] font-semibold"
										:class="
											row.enabled
												? 'bg-emerald-50 text-emerald-700'
												: 'bg-slate-100 text-slate-600'
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
					class="py-8 text-center text-sm text-[color:var(--genius-muted)]"
				>
					{{ __('No users found.') }}
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { createListResource, createResource, usePageMeta } from 'frappe-ui'
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import {
	Award,
	BarChart3,
	BookOpen,
	GraduationCap,
	Layers,
	Plus,
	Users,
	UsersRound,
} from 'lucide-vue-next'
import CourseCard from '@/components/CourseCard.vue'
import { openSettings } from '@/utils'
import { sessionStore } from '@/stores/session'

const user = inject('$user')
const router = useRouter()
const { brand } = sessionStore()

const createdCourses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	cache: ['admin-dashboard-courses'],
	auto: true,
})

const adminMetrics = createResource({
	url: 'lms.lms.api.get_admin_dashboard_data',
	auto: true,
	cache: ['admin-dashboard-metrics'],
})

const recentUsersResource = createListResource({
	doctype: 'User',
	fields: ['name', 'full_name', 'email', 'last_active', 'enabled'],
	filters: { name: ['not in', ['Guest', 'Administrator']] },
	orderBy: 'last_active desc',
	pageLength: 8,
	auto: true,
	cache: ['admin-dashboard-recent-users'],
})

const metricsLoading = computed(
	() => adminMetrics.loading || !adminMetrics.fetched
)

const certificates = createListResource({
	doctype: 'LMS Certificate',
	fields: ['name', 'member', 'member_name', 'course', 'course_title', 'issue_date'],
	orderBy: 'issue_date desc',
	pageLength: 8,
	auto: true,
	cache: ['admin-dashboard-certificates'],
})

const certifiedUsers = computed(() => certificates.data || [])

const formatIssueDate = (value) => {
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

const isDemoCourse = (course) => {
	const title = (course?.title || '').toLowerCase()
	return title.includes('frappe learning')
}

const courseCards = computed(() =>
	(createdCourses.data || []).filter((c) => !isDemoCourse(c)).slice(0, 8)
)

const kpiCards = computed(() => {
	const kpis = adminMetrics.data?.kpis || {}
	const users = adminMetrics.data?.users || {}
	const loaded = Boolean(adminMetrics.fetched)
	// Align course KPIs with the cards below (demo seed course is hidden)
	const realCourses = (createdCourses.data || []).filter((c) => !isDemoCourse(c))
	const useList = Boolean(createdCourses.data)
	const totalCourses = useList
		? realCourses.length
		: loaded
			? kpis.total_courses ?? 0
			: '—'
	const publishedCourses = useList
		? realCourses.filter((c) => c.published).length
		: loaded
			? kpis.published_courses ?? 0
			: '—'
	const delta =
		typeof totalCourses === 'number' && totalCourses > 0
			? `+${totalCourses}`
			: ''
	return [
		{
			key: 'courses',
			label: __('Total Courses'),
			value: totalCourses,
			delta,
			icon: BookOpen,
			color: '#1d4ed8',
			tint: '#eff6ff',
		},
		{
			key: 'published',
			label: __('Published Courses'),
			value: publishedCourses,
			delta: '',
			icon: GraduationCap,
			color: '#059669',
			tint: '#ecfdf5',
		},
		{
			key: 'learners',
			label: __('Total Learners'),
			value: loaded ? kpis.total_students ?? 0 : '—',
			delta: '',
			icon: Users,
			color: '#2563eb',
			tint: '#eff6ff',
		},
		{
			key: 'active',
			label: __('Active Learners'),
			value: loaded ? users.active ?? 0 : '—',
			delta: '',
			icon: UsersRound,
			color: '#0891b2',
			tint: '#ecfeff',
		},
		{
			key: 'certs',
			label: __('Certificates Issued'),
			value: loaded ? kpis.total_certificates ?? 0 : '—',
			delta: '',
			icon: Award,
			color: '#0d9488',
			tint: '#f0fdfa',
		},
		{
			key: 'batches',
			label: __('Total Batches'),
			value: loaded ? kpis.total_batches ?? 0 : '—',
			delta: '',
			icon: Layers,
			color: '#1d4ed8',
			tint: '#eff6ff',
		},
	]
})

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
		label: __('View Reports'),
		icon: BarChart3,
		onClick: () => router.push({ name: 'AnalyticsDashboard' }),
	},
])

const recentUsers = computed(() => recentUsersResource.data || [])

usePageMeta(() => ({
	title: __('Admin Dashboard'),
	icon: brand.favicon,
}))
</script>
