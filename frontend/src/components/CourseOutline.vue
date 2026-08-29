<template>
	<div class="">
		<div
			v-if="title && (outline.data?.length || allowEdit)"
			class="flex items-center justify-between gap-x-2 mb-4 px-2"
			:class="{
				'sticky top-0 z-10 bg-surface-white border-b px-3 py-2.5 sm:px-5':
					allowEdit,
			}"
		>
			<div
				class="font-semibold text-lg leading-5 text-ink-gray-9"
				:class="{ 'font-medium text-p-base': allowEdit }"
			>
				{{ __(title) }}
			</div>
			<Button size="sm" v-if="allowEdit" @click="openChapterModal()">
				<template #prefix>
					<Plus class="size-4 stroke-1.5" />
				</template>
				{{ __('Add') }}
			</Button>
		</div>
		<div
			:class="{
				'border-2 rounded-md py-2 px-2': showOutline && outline.data?.length,
			}"
		>
			<Draggable
				:list="outline.data"
				:disabled="!allowEdit"
				item-key="name"
				group="chapters"
				@end="updateChapterOrder"
			>
				<template #item="{ element: chapter, index }">
					<div class="chapter-item">
						<Disclosure
							v-slot="{ open }"
							:key="chapter.name"
							:defaultOpen="openChapterDetail(chapter.idx)"
						>
							<DisclosureButton
								ref=""
								class="flex items-center w-full p-2 group"
							>
								<ChevronRight
									:class="{
										'rotate-90': open,
										'rtl:rotate-180': !open,
										hidden: chapter.is_scorm_package,
										open: index == 1,
									}"
									class="h-4 w-4 text-ink-gray-9 stroke-1 transform duration-200"
								/>
								<div
									class="text-base text-start text-ink-gray-9 font-medium leading-5 ms-2"
									@click="redirectToChapter(chapter)"
								>
									{{ chapter.title }}
								</div>
								<div class="flex ms-auto gap-x-4">
									<Tooltip :text="__('Edit Chapter')" placement="bottom">
										<FilePenLine
											v-if="allowEdit"
											@click.prevent="openChapterModal(chapter)"
											class="h-4 w-4 text-ink-gray-9 invisible group-hover:visible"
										/>
									</Tooltip>
									<Tooltip :text="__('Delete Chapter')" placement="bottom">
										<Trash2
											v-if="allowEdit"
											@click.prevent="trashChapter(chapter.name)"
											class="h-4 w-4 text-ink-red-3 invisible group-hover:visible"
										/>
									</Tooltip>
								</div>
								<Check
									v-if="
										chapter.is_scorm_package && isScormChapterComplete(chapter)
									"
									class="h-4 w-4 text-green-700"
								/>
							</DisclosureButton>
							<DisclosurePanel v-if="!chapter.is_scorm_package">
								<Draggable
									v-if="!chapter.is_scorm_package"
									:list="chapter.lessons"
									:disabled="!allowEdit"
									item-key="name"
									group="items"
									@end="updateOutline"
									:data-chapter="chapter.name"
								>
									<template #item="{ element: lesson }">
										<div
											class="outline-lesson ps-8 py-2 pe-4 text-ink-gray-9"
											:class="{
												'bg-surface-gray-3': isActiveLesson(lesson.number),
												'opacity-50': isLessonLocked(lesson),
											}"
										>
											<router-link
												v-if="!isLessonLocked(lesson)"
												:to="{
													name: allowEdit ? 'LessonForm' : 'Lesson',
													params: {
														courseName: courseName,
														chapterNumber: lesson.number.split('-')[0],
														lessonNumber: lesson.number.split('-')[1],
													},
												}"
											>
												<div class="flex items-center text-sm leading-5 group">
													<MonitorPlay
														v-if="lesson.icon === 'icon-youtube'"
														class="h-4 w-4 stroke-1 me-2"
													/>
													<HelpCircle
														v-else-if="lesson.icon === 'icon-quiz'"
														class="h-4 w-4 stroke-1 me-2"
													/>
													<NotebookPen
														v-else-if="lesson.icon === 'icon-assignment'"
														class="h-4 w-4 stroke-1 me-2"
													/>
													<SquareCode
														v-else-if="lesson.icon === 'icon-code'"
														class="h-4 w-4 stroke-1 me-2"
													/>
													<FileText
														v-else-if="lesson.icon === 'icon-list'"
														class="h-4 w-4 text-ink-gray-9 stroke-1 me-2"
													/>
													{{ lesson.title }}
													<Trash2
														v-if="allowEdit"
														@click.prevent="
															trashLesson(lesson.name, chapter.name)
														"
														class="h-4 w-4 text-ink-red-3 ms-auto invisible group-hover:visible"
													/>
													<Check
														v-if="lesson.is_complete"
														class="h-4 w-4 text-green-700 ms-2 shrink-0"
													/>
												</div>
											</router-link>
											<div
												v-else
												class="flex items-center text-sm leading-5 text-ink-gray-5 cursor-not-allowed select-none"
												:title="__('Complete previous lessons to unlock')"
											>
												<LockKeyhole class="h-4 w-4 stroke-1 me-2 shrink-0" />
												{{ lesson.title }}
											</div>
										</div>
									</template>
								</Draggable>
							<div v-if="allowEdit" class="flex mt-2 mb-4 ps-8 gap-2">
								<router-link
									v-if="!chapter.is_scorm_package"
									:to="{
										name: 'LessonForm',
										params: {
											courseName: courseName,
											chapterNumber: chapter.idx,
											lessonNumber: chapter.lessons.length + 1,
										},
									}"
								>
									<Button>
										{{ __('Add Lesson') }}
									</Button>
								</router-link>
								<Button
									v-if="!chapter.is_scorm_package"
									@click="triggerUploadLesson(chapter)"
								>
									<template #prefix>
										<UploadIcon class="size-4 stroke-1.5" />
									</template>
									{{ __('Upload Lesson') }}
								</Button>
								<input
									type="file"
									ref="fileInputRef"
									accept=".pdf,.docx"
									class="hidden"
									@change="handleFileUpload($event)"
								/>
							</div>
							</DisclosurePanel>
						</Disclosure>
					</div>
				</template>
			</Draggable>
		</div>
		<div
			v-if="allowEdit && courseName"
			class="mt-6 border-t pt-4 px-2"
		>
			<div class="flex items-center justify-between mb-3">
				<div class="font-semibold text-lg leading-5 text-ink-gray-9">
					{{ __('Assessments') }}
				</div>
				<Button theme="green" size="sm" @click="showAssessmentModal = true">
					<template #prefix>
						<Plus class="size-4 stroke-1.5" />
					</template>
					{{ __('Add Assessment') }}
				</Button>
			</div>
			<div
				v-if="courseAssessments.data?.length"
				class="space-y-3"
			>
				<div
					v-for="row in courseAssessments.data"
					:key="row.name"
					class="rounded-md border bg-surface-white p-3 group"
				>
					<div class="flex items-center gap-2">
					<HelpCircle
						v-if="row.assessment_type === 'LMS Quiz'"
						class="h-4 w-4 stroke-1 shrink-0"
					/>
					<NotebookPen
						v-else-if="row.assessment_type === 'LMS Assignment'"
						class="h-4 w-4 stroke-1 shrink-0"
					/>
					<SquareCode
						v-else
						class="h-4 w-4 stroke-1 shrink-0"
					/>
					<div class="flex-1 min-w-0">
						<div class="text-sm font-medium text-ink-gray-9 truncate">
							{{ row.title }}
						</div>
						<div class="text-xs text-ink-gray-6">
							{{ getAssessmentTypeLabel(row.assessment_type) }}
						</div>
					</div>
						<Trash2
							class="h-4 w-4 text-ink-red-3 shrink-0 invisible group-hover:visible cursor-pointer"
							@click="trashAssessment(row.name)"
						/>
					</div>
					<div
						v-if="row.batches?.length"
						class="mt-3 space-y-2 border-t pt-3"
					>
						<div
							v-for="batch in row.batches"
							:key="batch.batch"
							class="flex items-center justify-between gap-3"
						>
							<span class="text-xs text-ink-gray-7 truncate">
								{{ batch.title }}
							</span>
							<div class="flex items-center gap-2 shrink-0">
								<span
									class="text-xs"
									:class="
										batch.is_visible
											? 'text-green-700'
											: 'text-ink-gray-6'
									"
								>
									{{ batch.is_visible ? __('Live') : __('Hidden') }}
								</span>
								<Switch
									size="sm"
									:modelValue="!!batch.is_visible"
									:disabled="visibilityToggle.loading"
									@update:modelValue="
										(value) =>
											updateVisibility(row.name, batch.batch, value)
									"
								/>
							</div>
						</div>
					</div>
					<div v-else class="mt-2 text-xs text-ink-gray-6">
						{{
							__(
								'Add this course to a batch to control when students see this assessment.'
							)
						}}
					</div>
				</div>
			</div>
			<div v-else class="text-sm text-ink-gray-6 px-2">
				{{ __('No assessments added yet. Assessments are hidden from students until you enable them per batch.') }}
			</div>
		</div>
		<div
			v-if="!allowEdit && getProgress && visibleCourseAssessments.data?.length"
			class="mt-6 border-t pt-4 px-2"
		>
			<div class="font-semibold text-lg leading-5 text-ink-gray-9 mb-3">
				{{ __('Assessments') }}
			</div>
			<div class="space-y-2">
				<router-link
					v-for="row in visibleCourseAssessments.data"
					:key="row.name"
					:to="getAssessmentRoute(row)"
					class="flex items-center gap-2 p-2 rounded-md border bg-surface-white hover:bg-surface-gray-2"
				>
					<HelpCircle
						v-if="row.assessment_type === 'LMS Quiz'"
						class="h-4 w-4 stroke-1 shrink-0"
					/>
					<NotebookPen
						v-else-if="row.assessment_type === 'LMS Assignment'"
						class="h-4 w-4 stroke-1 shrink-0"
					/>
					<SquareCode v-else class="h-4 w-4 stroke-1 shrink-0" />
					<div class="flex-1 min-w-0">
						<div class="text-sm font-medium text-ink-gray-9 truncate">
							{{ row.title }}
						</div>
						<div class="text-xs text-ink-gray-6">
							{{ getAssessmentTypeLabel(row.assessment_type) }}
							<span v-if="row.status"> · {{ row.status }}</span>
						</div>
					</div>
				</router-link>
			</div>
		</div>
	</div>
	<ChapterModal
		v-if="user.data"
		v-model="showChapterModal"
		v-model:outline="outline"
		:course="courseName"
		:chapterDetail="getCurrentChapter()"
	/>
	<AssessmentModal
		v-model="showAssessmentModal"
		v-model:assessments="courseAssessments"
		:course="courseName"
		@added="courseAssessments.reload()"
	/>
</template>
<script setup>
import { Button, call, createResource, Switch, Tooltip, toast } from 'frappe-ui'
import {
	getFrappeErrorMessage,
	LESSON_UPLOAD_MAX_BYTES,
} from '@/utils'
import { getCurrentInstance, inject, ref, watch } from 'vue'
import Draggable from 'vuedraggable'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import {
	Check,
	ChevronRight,
	FileText,
	FilePenLine,
	HelpCircle,
	LockKeyhole,
	MonitorPlay,
	NotebookPen,
	Plus,
	SquareCode,
	Trash2,
	Upload as UploadIcon,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import ChapterModal from '@/components/Modals/ChapterModal.vue'
import AssessmentModal from '@/components/Modals/AssessmentModal.vue'

const route = useRoute()
const router = useRouter()
const user = inject('$user')
const showChapterModal = ref(false)
const showAssessmentModal = ref(false)
const currentChapter = ref(null)
const app = getCurrentInstance()
const { $dialog } = app.appContext.config.globalProperties

const props = defineProps({
	courseName: {
		type: String,
		required: true,
	},
	showOutline: {
		type: Boolean,
		default: false,
	},
	title: {
		type: String,
		default: '',
	},
	allowEdit: {
		type: Boolean,
		default: false,
	},
	getProgress: {
		type: Boolean,
		default: false,
	},
	lessonProgress: {
		type: Number,
		default: 0,
	},
})

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	cache: ['course_outline', props.courseName],
	makeParams() {
		return {
			course: props.courseName,
			progress: props.getProgress,
		}
	},
	auto: true,
})

const courseAssessments = createResource({
	url: 'lms.lms.utils.get_course_assessments',
	cache: ['course_assessments', props.courseName],
	makeParams() {
		return {
			course: props.courseName,
		}
	},
	auto: () => props.allowEdit && !!props.courseName,
})

const visibleCourseAssessments = createResource({
	url: 'lms.lms.utils.get_visible_course_assessments',
	cache: ['visible_course_assessments', props.courseName],
	makeParams() {
		return {
			course: props.courseName,
		}
	},
	auto: () => !props.allowEdit && props.getProgress && !!props.courseName,
})

const visibilityToggle = createResource({
	url: 'lms.lms.api.set_course_assessment_visibility',
	makeParams(values) {
		return {
			course_assessment: values.course_assessment,
			batch: values.batch,
			is_visible: values.is_visible ? 1 : 0,
		}
	},
})

const deleteAssessment = createResource({
	url: 'lms.lms.api.delete_course_assessment',
	makeParams(values) {
		return {
			course_assessment: values.course_assessment,
		}
	},
	onSuccess() {
		courseAssessments.reload()
		toast.success(__('Assessment removed successfully'))
	},
})

watch(
	() => props.courseName,
	() => {
		outline.reload()
		courseAssessments.reload()
		visibleCourseAssessments.reload()
	}
)

watch(
	() => props.getProgress,
	() => {
		if (!props.allowEdit && props.getProgress) {
			visibleCourseAssessments.reload()
		}
	}
)

const getAssessmentTypeLabel = (type) => {
	if (type === 'LMS Assignment') return __('Assignment')
	if (type === 'LMS Quiz') return __('Quiz')
	if (type === 'LMS Programming Exercise') return __('Programming Exercise')
	return type
}

const updateVisibility = (courseAssessment, batch, isVisible) => {
	visibilityToggle.submit(
		{
			course_assessment: courseAssessment,
			batch,
			is_visible: isVisible,
		},
		{
			onSuccess() {
				courseAssessments.reload()
				toast.success(
					isVisible
						? __('Assessment is now live for this batch')
						: __('Assessment is now hidden for this batch')
				)
			},
		}
	)
}

const getAssessmentRoute = (row) => {
	if (row.assessment_type === 'LMS Assignment') {
		return {
			name: 'AssignmentSubmission',
			params: {
				assignmentID: row.assessment_name,
				submissionName: row.submission?.name || 'new',
			},
		}
	}
	if (row.assessment_type === 'LMS Programming Exercise') {
		return {
			name: 'ProgrammingExerciseSubmission',
			params: {
				exerciseID: row.assessment_name,
				submissionID: row.submission?.name || 'new',
			},
		}
	}
	return {
		name: 'QuizPage',
		params: {
			quizID: row.assessment_name,
		},
	}
}

const trashAssessment = (assessmentName) => {
	$dialog({
		title: __('Remove this assessment?'),
		message: __(
			'This removes the assessment from the course. The quiz, assignment, or exercise itself is not deleted.'
		),
		actions: [
			{
				label: __('Remove'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					deleteAssessment.submit({ course_assessment: assessmentName })
					close()
				},
			},
		],
	})
}

watch(
	() => props.lessonProgress,
	() => {
		outline.reload()
	}
)

const deleteLesson = createResource({
	url: 'lms.lms.api.delete_lesson',
	makeParams(values) {
		return {
			lesson: values.lesson,
			chapter: values.chapter,
		}
	},
	onSuccess() {
		outline.reload()
		toast.success(__('Lesson deleted successfully'))
	},
	onError(err) {
		const msg =
			err?.messages?.[0] ||
			err?.message ||
			__('Cannot delete this lesson because it is linked to other records.')
		toast.error(msg)
		console.error(err)
	},
})

const updateLessonIndex = createResource({
	url: 'lms.lms.api.update_lesson_index',
	makeParams(values) {
		return {
			lesson: values.lesson,
			sourceChapter: values.sourceChapter,
			targetChapter: values.targetChapter,
			idx: values.idx,
		}
	},
	onSuccess() {
		toast.success(__('Lesson moved successfully'))
	},
})

const updateChapterIndex = createResource({
	url: 'lms.lms.api.update_chapter_index',
	makeParams(values) {
		return {
			chapter: values.chapter,
			course: values.course,
			idx: values.idx,
		}
	},
	onSuccess() {
		toast.success(__('Chapter moved successfully'))
	},
})

const trashLesson = (lessonName, chapterName) => {
	$dialog({
		title: __('Delete this lesson?'),
		message: __(
			'Deleting this lesson will permanently remove it from the course. This action cannot be undone. Are you sure you want to continue?'
		),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					deleteLesson.submit({
						lesson: lessonName,
						chapter: chapterName,
					})
					close()
				},
			},
		],
	})
}

const openChapterDetail = (index) => {
	return index == route.params.chapterNumber || index == 1
}

const openChapterModal = (chapter = null) => {
	currentChapter.value = chapter
	showChapterModal.value = true
}

const getCurrentChapter = () => {
	return currentChapter.value
}

const updateOutline = (e) => {
	updateLessonIndex.submit({
		lesson: e.item.__draggable_context.element.name,
		sourceChapter: e.from.dataset.chapter,
		targetChapter: e.to.dataset.chapter,
		idx: e.newIndex,
	})
}

const updateChapterOrder = (e) => {
	updateChapterIndex.submit({
		chapter: e.item.__draggable_context.element.name,
		course: props.courseName,
		idx: e.newIndex,
	})
}

const deleteChapter = createResource({
	url: 'lms.lms.api.delete_chapter',
	makeParams(values) {
		return {
			chapter: values.chapter,
		}
	},
	onSuccess() {
		outline.reload()
		toast.success(__('Chapter deleted successfully'))
	},
})

const trashChapter = (chapterName) => {
	$dialog({
		title: __('Delete this chapter?'),
		message: __(
			'Deleting this chapter will also delete all its lessons and permanently remove it from the course. This action cannot be undone. Are you sure you want to continue?'
		),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					deleteChapter.submit({ chapter: chapterName })
					close()
				},
			},
		],
	})
}

const redirectToChapter = (chapter) => {
	if (!chapter.is_scorm_package) return
	event.preventDefault()
	if (props.allowEdit) return
	if (!user.data) {
		toast.success(__('Please enroll for this course to view this lesson'))
		return
	}

	router.push({
		name: 'GeniusScormPlayer',
		params: {
			courseName: props.courseName,
		},
		query: {
			chapter: chapter.name,
		},
	})
}

const isScormChapterComplete = (chapter) => {
	return chapter.lessons?.length && chapter.lessons.every((l) => l.is_complete)
}

const isActiveLesson = (lessonNumber) => {
	return (
		route.params.chapterNumber == lessonNumber.split('-')[0] &&
		route.params.lessonNumber == lessonNumber.split('-')[1]
	)
}

const isLessonLocked = (lesson) => {
	return Boolean(props.getProgress && lesson.is_locked && !props.allowEdit)
}

const fileInputRef = ref(null)
const uploadTargetChapter = ref(null)

const triggerUploadLesson = (chapter) => {
	uploadTargetChapter.value = chapter
	const inputs = document.querySelectorAll('input[type="file"][accept=".pdf,.docx"]')
	const chapterInputs = Array.from(inputs)
	const idx = outline.data?.indexOf(chapter) ?? 0
	const input = chapterInputs[idx] || chapterInputs[0]
	if (input) input.click()
}

const uploadLessonFile = async (file, chapter) => {
	if (file.size > LESSON_UPLOAD_MAX_BYTES) {
		const maxMb = Math.floor(LESSON_UPLOAD_MAX_BYTES / (1024 * 1024))
		throw new Error(
			__('File is too large. Maximum size is {0} MB.').format(maxMb)
		)
	}

	const uploadForm = new FormData()
	uploadForm.append('file', file)
	uploadForm.append('is_private', '0')

	const uploadRes = await fetch('/api/method/upload_file', {
		method: 'POST',
		headers: {
			'X-Frappe-CSRF-Token': window.csrf_token || '',
		},
		body: uploadForm,
	})

	if (uploadRes.status === 413) {
		throw new Error(
			__(
				'File is too large for the server. Try a smaller PDF/DOCX or ask an admin to increase the upload limit.'
			)
		)
	}

	const uploadData = await uploadRes.json()
	if (!uploadRes.ok || uploadData.exc) {
		throw new Error(
			getFrappeErrorMessage(uploadData) ||
				__('Failed to upload file. Please try again.')
		)
	}

	const uploaded = uploadData.message
	const result = await call('lms.lms.api.create_lesson_from_file', {
		course: props.courseName,
		chapter: chapter.idx,
		file_url: uploaded.file_url,
		file_name: uploaded.file_name || file.name,
	})

	outline.reload()
	router.push({
		name: 'LessonForm',
		params: {
			courseName: props.courseName,
			chapterNumber: result.chapter_number,
			lessonNumber: result.lesson_number,
		},
	})
	return __('Lesson created: ') + result.title
}

const handleFileUpload = async (event) => {
	const file = event.target.files[0]
	if (!file) return

	const ext = file.name.split('.').pop().toLowerCase()
	if (!['pdf', 'docx'].includes(ext)) {
		toast.error(__('Only PDF and DOCX files are allowed.'))
		event.target.value = ''
		return
	}

	const chapter = uploadTargetChapter.value
	if (!chapter) return

	toast.promise(uploadLessonFile(file, chapter), {
		loading: __('Uploading and creating lesson...'),
		success: (msg) => msg,
		error: (err) =>
			err?.message ||
			getFrappeErrorMessage(err) ||
			__('Failed to create lesson from file'),
	})

	event.target.value = ''
}
</script>
