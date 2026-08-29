let context = { course: null, lesson: null }

export function setLessonPdfContext({ course, lesson } = {}) {
	context = {
		course: course || null,
		lesson: lesson || null,
	}
}

export function getLessonPdfContext() {
	return { ...context }
}

export function clearLessonPdfContext() {
	context = { course: null, lesson: null }
}
