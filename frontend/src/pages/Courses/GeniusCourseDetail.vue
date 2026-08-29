<template>
	<div v-if="course.data" class="pb-10">
		<header
			class="sticky top-0 z-10 flex items-center justify-between gap-3 border-b bg-white px-3 py-2.5 sm:px-5"
			style="border-color: var(--genius-border)"
		>
			<Breadcrumbs class="h-7 min-w-0" :items="breadcrumbs" />
			<div v-if="isAdmin" class="flex shrink-0 items-center gap-2">
				<Button variant="subtle" @click="openCourseEdit">
					<template #prefix>
						<Settings2 class="size-4 stroke-1.5" />
					</template>
					{{ __('Edit Course') }}
				</Button>
			</div>
		</header>

		<section
			class="genius-hero-surface px-5 py-10 text-white sm:px-8"
		>
			<div class="relative z-10 mx-auto max-w-5xl">
				<h1
					class="genius-fade-up text-3xl font-semibold tracking-tight sm:text-4xl"
					style="color: #fff !important"
				>
					{{ course.data.title }}
				</h1>
				<p class="genius-fade-up-delay mt-3 max-w-2xl text-white/85">
					{{ course.data.short_introduction }}
				</p>
				<div class="genius-fade-up-delay mt-6 flex flex-wrap items-center gap-3">
					<template v-if="course.data.membership">
						<router-link :to="playerOrLessonRoute">
							<Button variant="solid" size="md">
								{{ __('Continue') }}
							</Button>
						</router-link>
						<div class="text-sm text-white/80">
							{{ Math.round(course.data.membership.progress || 0) }}%
							{{ __('complete') }}
						</div>
					</template>
					<Button
						v-else-if="!course.data.disable_self_learning"
						variant="solid"
						size="md"
						@click="enrollStudent"
					>
						{{ __('Enroll / Start') }}
					</Button>
					<Badge v-else theme="blue" size="lg">
						{{ __('Contact the Administrator to enroll for this course') }}
					</Badge>
					<Button
						v-if="isAdmin"
						variant="outline"
						size="md"
						class="!border-white !bg-white !text-[#0075ff] hover:!bg-[#ffd000] hover:!text-[#12263f]"
						@click="openCourseEdit"
					>
						<template #prefix>
							<Settings2 class="size-4 stroke-1.5" />
						</template>
						{{ __('Edit Course') }}
					</Button>
				</div>
			</div>
		</section>

		<div class="mx-auto grid max-w-5xl gap-8 px-5 py-8 sm:px-8 lg:grid-cols-[1fr_280px]">
			<div>
				<div
					v-html="sanitizeHTML(course.data.description)"
					class="ProseMirror prose prose-sm max-w-none !whitespace-normal"
				/>
				<div class="mt-10">
					<CourseOutline
						:courseName="courseName"
						:title="outlineTitle"
						:showOutline="true"
						:getProgress="true"
					/>
				</div>
			</div>
			<aside>
				<CourseCardOverlay :course="course" />
			</aside>
		</div>
	</div>
</template>
<script setup>
import {
	Badge,
	Breadcrumbs,
	Button,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { Settings2 } from 'lucide-vue-next'
import CourseCardOverlay from '@/components/CourseCardOverlay.vue'
import CourseOutline from '@/components/CourseOutline.vue'
import { sessionStore } from '@/stores/session'
import { useTelemetry } from 'frappe-ui/frappe'
import { sanitizeHTML } from '@/utils'

const props = defineProps({
	courseName: { type: String, required: true },
})

const user = inject('$user')
const router = useRouter()
const { brand } = sessionStore()
const { capture } = useTelemetry()

const course = createResource({
	url: 'lms.lms.utils.get_course_details',
	params: { course: props.courseName },
	auto: true,
	cache: ['genius-course', props.courseName],
})

const playerOrLessonRoute = computed(() => {
	if (course.data?.has_scorm) {
		return {
			name: 'GeniusScormPlayer',
			params: { courseName: props.courseName },
		}
	}
	const current = course.data?.current_lesson || '1-1'
	const parts = String(current).split('-')
	return {
		name: 'Lesson',
		params: {
			courseName: props.courseName,
			chapterNumber: parts[0] || 1,
			lessonNumber: parts[1] || 1,
		},
	}
})

const breadcrumbs = computed(() => [
	{ label: __('Courses'), route: { name: 'Courses' } },
	{ label: course.data?.title || props.courseName },
])

const outlineTitle = computed(() => {
	const title = (course.data?.title || props.courseName || '').toLowerCase()
	if (props.courseName === 'sales-crt' || title.includes('crt')) {
		return __('5-day CRT modules')
	}
	return __('Modules')
})

const isInstructor = () => {
	let userIsInstructor = false
	;(course.data?.instructors || []).forEach((instructor) => {
		if (!userIsInstructor && instructor.name == user.data?.name) {
			userIsInstructor = true
		}
	})
	return userIsInstructor
}

const isAdmin = computed(
	() =>
		!!(
			user.data?.is_moderator ||
			user.data?.is_system_manager ||
			isInstructor()
		)
)

const openCourseEdit = () => {
	router.push({
		name: 'CourseDetail',
		params: { courseName: props.courseName },
		hash: '#settings',
	})
}

const enrollStudent = () => {
	if (!user.data) {
		toast.warning(__('You need to login first to enroll for this course'))
		setTimeout(() => {
			window.location.href = `/login?redirect-to=${window.location.pathname}`
		}, 500)
		return
	}
	call('frappe.client.insert', {
		doc: {
			doctype: 'LMS Enrollment',
			course: props.courseName,
			member: user.data.name,
		},
	})
		.then(() => {
			capture('enrolled_in_course', { course: props.courseName })
			toast.success(__('You have been enrolled in this course'))
			course.reload()
			setTimeout(() => {
				router.push(playerOrLessonRoute.value)
			}, 600)
		})
		.catch((err) => {
			toast.warning(__(err.messages?.[0] || err))
		})
}

usePageMeta(() => ({
	title: course.data?.title,
	icon: brand.favicon,
}))
</script>
