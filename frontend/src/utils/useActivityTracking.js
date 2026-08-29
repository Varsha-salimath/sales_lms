import { call } from 'frappe-ui'
import { onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { sessionStore } from '@/stores/session'

const IDLE_TIMEOUT_MS = 2 * 60 * 1000
const HEARTBEAT_MIN_MS = 30 * 1000
const HEARTBEAT_MAX_MS = 60 * 1000

const INTERACTION_EVENTS = ['click', 'scroll', 'keydown', 'touchstart', 'mousemove']

function getModuleFromRoute(route) {
	const name = route?.name
	if (
		name === 'Lesson' ||
		name === 'CourseDetail' ||
		name === 'LessonForm' ||
		name === 'SCORMChapter' ||
		name === 'CourseCertification'
	) {
		return 'Courses'
	}
	if (
		name === 'QuizPage' ||
		name === 'QuizForm' ||
		name === 'Quizzes' ||
		name === 'QuizSubmission' ||
		name === 'QuizSubmissionList'
	) {
		return 'Quiz'
	}
	if (
		name === 'Assignments' ||
		name === 'AssignmentSubmission' ||
		name === 'AssignmentSubmissionList'
	) {
		return 'Assignment'
	}
	if (name === 'Library') {
		return 'Library'
	}
	if (
		name === 'ProgrammingExercises' ||
		name === 'ProgrammingExerciseSubmission' ||
		name === 'ProgrammingExerciseSubmissions'
	) {
		return 'Programming'
	}
	return 'Other'
}

function randomHeartbeatDelay() {
	return HEARTBEAT_MIN_MS + Math.random() * (HEARTBEAT_MAX_MS - HEARTBEAT_MIN_MS)
}

export function useActivityTracking() {
	const route = useRoute()
	const { isLoggedIn } = storeToRefs(sessionStore())

	let lastInteraction = Date.now()
	let heartbeatTimer = null
	let isPaused = true
	let isTabVisible = true
	let currentModule = 'Other'

	function clearHeartbeatTimer() {
		if (heartbeatTimer) {
			clearTimeout(heartbeatTimer)
			heartbeatTimer = null
		}
	}

	function scheduleHeartbeat() {
		clearHeartbeatTimer()
		if (isPaused || !isTabVisible || !isLoggedIn.value) return
		heartbeatTimer = setTimeout(() => {
			sendHeartbeat()
			scheduleHeartbeat()
		}, randomHeartbeatDelay())
	}

	function sendHeartbeat() {
		if (isPaused || !isTabVisible || !isLoggedIn.value) return
		call('lms.tracking.send_heartbeat', { module: currentModule }).catch(() => {})
	}

	function onInteraction() {
		lastInteraction = Date.now()
		const wasPaused = isPaused
		isPaused = false
		if (wasPaused && isTabVisible && isLoggedIn.value) {
			scheduleHeartbeat()
		}
	}

	function checkIdle() {
		if (!isLoggedIn.value || isPaused || !isTabVisible) return
		if (Date.now() - lastInteraction >= IDLE_TIMEOUT_MS) {
			isPaused = true
			clearHeartbeatTimer()
		}
	}

	function onVisibilityChange() {
		if (document.visibilityState === 'hidden') {
			isTabVisible = false
			isPaused = true
			clearHeartbeatTimer()
			return
		}
		isTabVisible = true
		isPaused = true
	}

	let idleInterval = null

	function start() {
		if (!isLoggedIn.value) return
		currentModule = getModuleFromRoute(route)
		lastInteraction = Date.now()
		isPaused = true
		isTabVisible = document.visibilityState === 'visible'

		INTERACTION_EVENTS.forEach((event) => {
			window.addEventListener(event, onInteraction, { passive: true })
		})
		document.addEventListener('visibilitychange', onVisibilityChange)
		idleInterval = setInterval(checkIdle, 15000)
	}

	function stop() {
		clearHeartbeatTimer()
		if (idleInterval) {
			clearInterval(idleInterval)
			idleInterval = null
		}
		INTERACTION_EVENTS.forEach((event) => {
			window.removeEventListener(event, onInteraction)
		})
		document.removeEventListener('visibilitychange', onVisibilityChange)
	}

	watch(
		() => route.fullPath,
		() => {
			currentModule = getModuleFromRoute(route)
		}
	)

	watch(isLoggedIn, (loggedIn) => {
		if (loggedIn) {
			start()
		} else {
			stop()
		}
	})

	onMounted(() => {
		if (isLoggedIn.value) start()
	})
	onUnmounted(stop)
}
