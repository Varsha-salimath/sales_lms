<template>
	<div
		class="genius-player flex h-screen flex-col overflow-hidden"
		style="background: var(--genius-bg)"
	>
		<PlayerProgressHeader
			:title="course.data?.title || __('Course player')"
			:progress="displayProgress"
			:breadcrumbs="breadcrumbs"
			:current-lesson="activeLesson?.title || ''"
			:duration-label="durationLabel"
			:celebrate="celebrate"
			@exit="exitCourse"
		/>

		<div
			v-if="!user.data"
			class="flex flex-1 items-center justify-center p-8 text-center"
		>
			<div>
				<p class="mb-4 text-[color:var(--genius-muted)]">
					{{ __('Please sign in to open the course player.') }}
				</p>
				<a href="/login" class="text-[color:var(--genius-blue)] underline">
					{{ __('Sign in') }}
				</a>
			</div>
		</div>

		<div
			v-else-if="canAccess"
			class="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)]"
		>
			<div class="hidden min-h-0 lg:block">
				<PlayerSidebar
					:lessons="flatLessons"
					:active-key="activeLessonKey"
					:course-progress="displayProgress"
					@select-lesson="onSelectLesson"
				/>
			</div>

			<main class="relative flex min-h-0 flex-col bg-white">
				<div
					v-if="loadingLesson"
					class="absolute inset-0 z-10 grid place-items-center bg-white/70"
				>
					<div class="text-sm font-medium text-[color:var(--genius-primary)]">
						{{ __('Loading lesson…') }}
					</div>
				</div>

				<iframe
					v-if="activeLaunchFile"
					:key="iframeKey"
					:src="activeLaunchFile"
					class="min-h-0 w-full flex-1 border-0"
					title="Lesson content"
					allow="fullscreen"
				/>
				<div
					v-else
					class="grid flex-1 place-items-center text-sm text-[color:var(--genius-muted)]"
				>
					{{ __('Select a lesson to begin.') }}
				</div>

				<PlayerNotesPanel
					:course-name="courseName"
					:score="lessonProgress?.scorm_score"
					:total-time="lessonProgress?.scorm_total_time"
					:launch-file="activeLaunchFile"
					:storage-key="notesKey"
					:last-lesson="activeLesson?.title || ''"
				/>

				<div
					class="flex items-center justify-between gap-3 border-t px-4 py-3"
					style="border-color: var(--genius-border); background: var(--genius-surface-elevated)"
				>
					<button
						type="button"
						class="rounded-xl border px-4 py-2 text-sm font-semibold disabled:opacity-40"
						style="border-color: var(--genius-border); color: var(--genius-navy)"
						:disabled="!prevLesson"
						@click="goPrev"
					>
						{{ __('Previous Lesson') }}
					</button>
					<div class="text-xs text-[color:var(--genius-muted)]">
						{{ activeIndex + 1 }} / {{ flatLessons.length }}
					</div>
					<button
						type="button"
						class="rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
						style="background: var(--genius-primary)"
						:disabled="!nextLesson || nextLesson.locked"
						@click="goNext"
					>
						{{ __('Next Lesson') }}
					</button>
				</div>
			</main>
		</div>

		<div
			v-else-if="!enrollment.data?.length"
			class="flex flex-1 items-center justify-center p-8"
		>
			<div class="max-w-md text-center">
				<p class="mb-4 text-[color:var(--genius-muted)]">
					{{
						__(
							'You are not enrolled in this course. Please enroll to access this lesson.'
						)
					}}
				</p>
				<Button variant="solid" @click="enrollStudent">
					{{ __('Start Learning') }}
				</Button>
			</div>
		</div>

		<div
			v-if="celebrate"
			class="pointer-events-none fixed inset-0 z-50 grid place-items-center"
		>
			<div
				class="rounded-2xl px-6 py-4 text-sm font-semibold text-white shadow-xl"
				style="background: var(--genius-gradient)"
			>
				{{ __('Lesson completed!') }}
			</div>
		</div>

		<div
			v-if="showFeedbackGate"
			class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
		>
			<div class="w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl">
				<div
					class="px-6 py-7 text-center text-white"
					style="background: linear-gradient(135deg, #1d4ed8, #0f172a)"
				>
					<div class="mb-2 text-3xl">🎉</div>
					<h2 class="text-xl font-semibold text-white">
						{{ __('Congratulations!') }}
					</h2>
					<p class="mt-2 text-sm text-white/90">
						{{
							__(
								'You have successfully completed {0}.'
							).format(course.data?.title || props.courseName)
						}}
					</p>
					<p class="mt-3 text-sm text-white/80">
						{{
							__(
								'Before downloading your certificate, please complete the feedback form.'
							)
						}}
					</p>
				</div>
				<div class="flex flex-wrap items-center justify-center gap-3 px-6 py-5">
					<button
						type="button"
						class="rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
						style="background: var(--genius-primary)"
						@click="goToFeedback"
					>
						{{ __('Complete Feedback') }}
					</button>
					<button
						type="button"
						class="rounded-xl border px-5 py-2.5 text-sm font-semibold text-[color:var(--genius-ink)]"
						@click="showFeedbackGate = false"
					>
						{{ __('Later') }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import {
	Button,
	call,
	createListResource,
	createResource,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { createScormApiBridge } from '@/components/scorm/ScormApiBridge'
import PlayerProgressHeader from '@/components/scorm/PlayerProgressHeader.vue'
import PlayerSidebar from '@/components/scorm/PlayerSidebar.vue'
import PlayerNotesPanel from '@/components/scorm/PlayerNotesPanel.vue'

const props = defineProps({
	courseName: { type: String, required: true },
	chapterName: { type: String, default: '' },
})

const user = inject('$user')
const { brand } = sessionStore()
const router = useRouter()
const route = useRoute()

const loadingLesson = ref(false)
const celebrate = ref(false)
const showFeedbackGate = ref(false)
const activeLessonKey = ref('')
const lessonProgress = ref(null)
const enrollmentProgress = ref(0)
const liveMeasureProgress = ref(null)
const iframeKey = ref(0)

const course = createResource({
	url: 'lms.lms.utils.get_course_details',
	params: { course: props.courseName },
	auto: true,
	cache: ['genius-player-course', props.courseName],
})

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	params: { course: props.courseName, progress: true },
	auto: true,
	cache: ['genius-player-outline', props.courseName],
	onSuccess() {
		ensureActiveLesson()
	},
})

const enrollment = createListResource({
	doctype: 'LMS Enrollment',
	fields: ['name', 'member', 'course', 'progress', 'current_lesson'],
	filters: {
		course: props.courseName,
		member: user.data?.name,
	},
	auto: !!user.data?.name,
	cache: ['enrollments', props.courseName, user.data?.name],
	onSuccess(data) {
		enrollmentProgress.value = Number(data?.[0]?.progress || 0)
	},
})

const canAccess = computed(() => {
	return (
		enrollment.data?.length ||
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_system_manager
	)
})

const flatLessons = computed(() => {
	const items = []
	for (const chapter of outline.data || []) {
		const lessons = chapter.lessons?.length
			? chapter.lessons
			: [{ name: chapter.name, title: chapter.title, is_complete: false }]
		for (const lesson of lessons) {
			const lessonName = lesson.name || lesson.lesson || chapter.name
			const isComplete = !!(
				lesson.is_complete ||
				lesson.progress === 'Complete' ||
				lesson.status === 'Complete'
			)
			const locked = !!(lesson.is_locked && !isComplete)
			items.push({
				key: `${chapter.name}:${lessonName}`,
				chapterName: chapter.name,
				lessonName,
				title: lesson.title || chapter.title,
				launch_file: chapter.launch_file || '',
				is_scorm: !!chapter.is_scorm_package,
				isComplete,
				partial:
					!isComplete &&
					(lesson.progress === 'Partially Complete' ||
						Number(lesson.scorm_progress || 0) > 0),
				scormProgress: Number(lesson.scorm_progress || 0),
				locked,
				number: lesson.number,
			})
		}
	}
	return items
})

const activeIndex = computed(() =>
	flatLessons.value.findIndex((l) => l.key === activeLessonKey.value)
)

const activeLesson = computed(() =>
	activeIndex.value >= 0 ? flatLessons.value[activeIndex.value] : null
)

const prevLesson = computed(() =>
	activeIndex.value > 0 ? flatLessons.value[activeIndex.value - 1] : null
)

const nextLesson = computed(() => {
	if (activeIndex.value < 0) return null
	return flatLessons.value[activeIndex.value + 1] || null
})

const activeLaunchFile = computed(() => activeLesson.value?.launch_file || '')

const displayProgress = computed(() => {
	if (liveMeasureProgress.value != null) {
		return Math.max(enrollmentProgress.value, liveMeasureProgress.value)
	}
	return enrollmentProgress.value
})

const durationLabel = computed(() => {
	const seconds = Number(lessonProgress.value?.scorm_total_time || 0)
	if (!seconds) return ''
	const m = Math.floor(seconds / 60)
	if (m < 60) return `${m || 1} ${__('min spent')}`
	return `${Math.floor(m / 60)}h ${m % 60}m ${__('spent')}`
})

const notesKey = computed(() =>
	user.data?.name && activeLessonKey.value
		? `genius-notes:${props.courseName}:${activeLessonKey.value}:${user.data.name}`
		: ''
)

const breadcrumbs = computed(() => [
	{ label: __('Courses'), route: { name: 'Courses' } },
	{
		label: course.data?.title || props.courseName,
		route: {
			name: 'GeniusCourseDetail',
			params: { courseName: props.courseName },
		},
	},
	{ label: __('Player') },
])

let bridge = null

const getProgress = () => lessonProgress.value || {}

const applyLiveMeasure = (scormDetails) => {
	if (scormDetails?.is_complete) {
		liveMeasureProgress.value = 100
		return
	}
	if (scormDetails?.progress_measure == null) return
	const lessonCount = flatLessons.value.length || 1
	const completed = flatLessons.value.filter((l) => l.isComplete).length
	const measure = Number(scormDetails.progress_measure)
	liveMeasureProgress.value = ((completed + measure) / lessonCount) * 100
}

const persistProgress = (scormDetails) => {
	const lessonName = activeLesson.value?.lessonName
	if (!lessonName) return Promise.resolve()

	applyLiveMeasure(scormDetails)

	return call('lms.lms.doctype.course_lesson.course_lesson.save_progress', {
		lesson: lessonName,
		course: props.courseName,
		scorm_details: scormDetails,
	})
		.then((progress) => {
			if (typeof progress === 'number') {
				enrollmentProgress.value = progress
				if (!scormDetails?.is_complete && progress > 0) {
					liveMeasureProgress.value = Math.max(
						liveMeasureProgress.value || 0,
						progress
					)
				}
				if (progress >= 100) {
					maybePromptFeedback()
				}
			}
			if (scormDetails?.is_complete) {
				liveMeasureProgress.value = 100
				enrollmentProgress.value = Math.max(enrollmentProgress.value, 100)
				celebrate.value = true
				setTimeout(() => {
					celebrate.value = false
				}, 1800)
				outline.reload()
				maybePromptFeedback()
			}
			loadLessonProgress()
			enrollment.reload()
		})
		.catch((err) => {
			console.error('Failed to save SCORM progress', err)
		})
}

const maybePromptFeedback = async () => {
	return
}

const goToFeedback = () => {
	showFeedbackGate.value = false
	router.push({
		name: 'CourseFeedback',
		params: { courseName: props.courseName },
	})
}

const loadLessonProgress = () => {
	const lessonName = activeLesson.value?.lessonName
	if (!lessonName || !user.data?.name) {
		loadingLesson.value = false
		return
	}
	call('frappe.client.get_value', {
		doctype: 'LMS Course Progress',
		fieldname: [
			'status',
			'scorm_content',
			'scorm_score',
			'scorm_total_time',
			'scorm_progress',
		],
		filters: {
			member: user.data.name,
			lesson: lessonName,
			course: props.courseName,
		},
	})
		.then((data) => {
			lessonProgress.value = data || {}
			bridge?.markCompletedFromServer({
				...lessonProgress.value,
				progress_measure:
					lessonProgress.value?.status === 'Complete'
						? 1
						: lessonProgress.value?.scorm_progress != null
							? Number(lessonProgress.value.scorm_progress) / 100
							: null,
			})
			if (
				lessonProgress.value?.status !== 'Complete' &&
				lessonProgress.value?.scorm_progress != null
			) {
				liveMeasureProgress.value = Math.max(
					liveMeasureProgress.value || 0,
					Number(lessonProgress.value.scorm_progress)
				)
			} else if (lessonProgress.value?.status === 'Complete') {
				liveMeasureProgress.value = 100
			}
		})
		.finally(() => {
			loadingLesson.value = false
		})
}

const ensureActiveLesson = () => {
	if (!flatLessons.value.length) return
	if (activeLessonKey.value) {
		const still = flatLessons.value.find((l) => l.key === activeLessonKey.value)
		if (still) return
	}
	const fromChapter =
		props.chapterName || route.query.chapter || route.params.chapterName
	const match =
		flatLessons.value.find((l) => l.chapterName === fromChapter) ||
		flatLessons.value.find((l) => !l.locked) ||
		flatLessons.value[0]
	if (match) selectLesson(match, false)
}

const selectLesson = (lesson, showLoader = true) => {
	if (!lesson || lesson.locked) return
	if (lesson.key === activeLessonKey.value) return
	if (showLoader) loadingLesson.value = true
	bridge?.resetForLesson()
	activeLessonKey.value = lesson.key
	liveMeasureProgress.value = null
	iframeKey.value += 1
	router.replace({
		query: { ...route.query, chapter: lesson.chapterName, lesson: lesson.lessonName },
	})
	loadLessonProgress()
}

const onSelectLesson = (lesson) => selectLesson(lesson, true)

const goPrev = () => {
	if (prevLesson.value) selectLesson(prevLesson.value, true)
}

const goNext = () => {
	if (nextLesson.value && !nextLesson.value.locked) {
		selectLesson(nextLesson.value, true)
	}
}

const exitCourse = () => {
	router.push({
		name: 'GeniusCourseDetail',
		params: { courseName: props.courseName },
	})
}

const enrollStudent = () => {
	enrollment.insert.submit(
		{
			course: props.courseName,
			member: user.data?.name,
		},
		{
			onSuccess() {
				window.location.reload()
			},
		}
	)
}

onMounted(() => {
	bridge = createScormApiBridge({
		getProgress,
		saveProgress: persistProgress,
		onComplete: () => {
			celebrate.value = true
			setTimeout(() => {
				celebrate.value = false
			}, 1800)
		},
		onProgress: (details) => {
			applyLiveMeasure(details)
		},
	})
	bridge.attach()
})

onBeforeUnmount(() => {
	bridge?.detach()
})

watch(
	() => outline.data,
	() => ensureActiveLesson()
)

usePageMeta(() => ({
	title: course.data?.title || __('Player'),
	icon: brand.favicon,
}))
</script>
