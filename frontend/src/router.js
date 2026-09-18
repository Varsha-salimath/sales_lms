import { createRouter, createWebHistory } from 'vue-router'
import { usersStore } from './stores/user'
import { sessionStore } from './stores/session'
import { useSettings } from './stores/settings'
import { getRouterHistoryBase } from './utils/basePath'

const routes = [
	{
		path: '/lms',
		redirect: '/dashboard',
	},
	{
		path: '/lms/:pathMatch(.*)*',
		name: 'LegacyLmsPrefix',
		redirect: (to) => {
			const rest = to.params.pathMatch
			const suffix = Array.isArray(rest) ? rest.filter(Boolean).join('/') : rest || ''
			return suffix ? `/${suffix}` : '/dashboard'
		},
	},
	{
		path: '/',
		name: 'Home',
		redirect: { name: 'StudentDashboard' },
	},
	{
		path: '/crt',
		name: 'SalesSchedule',
		redirect: { name: 'StudentDashboard' },
	},
	{
		path: '/crt/:crtNumber',
		name: 'SalesCRT',
		component: () => import('@/pages/Sales/SalesCRTDetail.vue'),
		props: true,
	},
	{
		path: '/evaluation',
		name: 'SalesEvaluation',
		component: () => import('@/pages/Sales/SalesEvaluation.vue'),
	},
	{
		path: '/ojt',
		name: 'SalesOJT',
		component: () => import('@/pages/Sales/SalesOJTLobby.vue'),
	},
	{
		path: '/ojt/:scenarioKey',
		name: 'SalesOJTSim',
		component: () => import('@/pages/Sales/SalesOJTSim.vue'),
		props: true,
	},
	{
		path: '/sales-certificate',
		name: 'SalesCertificate',
		component: () => import('@/pages/Sales/SalesCertificate.vue'),
	},
	{
		path: '/crt/import',
		name: 'SalesImport',
		component: () => import('@/pages/CRT/SalesImport.vue'),
	},
	{
		path: '/crt/session/:sessionKey',
		name: 'SalesSession',
		redirect: { name: 'GeniusCourseDetail', params: { courseName: 'sales-crt' } },
	},
	{
		path: '/dashboard',
		name: 'StudentDashboard',
		component: () => import('@/pages/Dashboard/Dashboard.vue'),
	},
	{
		path: '/admin',
		name: 'AdminDashboard',
		component: () => import('@/pages/Dashboard/AdminDashboard.vue'),
	},
	{
		path: '/home',
		name: 'InstructorHome',
		component: () => import('@/pages/Home/Home.vue'),
	},
	{
		path: '/courses',
		name: 'Courses',
		component: () => import('@/pages/Courses/Courses.vue'),
	},
	{
		path: '/course/:courseName/player',
		name: 'GeniusScormPlayer',
		component: () => import('@/pages/Player/GeniusScormPlayer.vue'),
		props: true,
	},
	{
		path: '/course/:courseName',
		name: 'GeniusCourseDetail',
		component: () => import('@/pages/Courses/GeniusCourseDetail.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName',
		name: 'CourseDetail',
		component: () => import('@/pages/Courses/CourseDetail.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/learn/:chapterNumber-:lessonNumber',
		name: 'Lesson',
		component: () => import('@/pages/Lesson.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/certification',
		name: 'CourseCertification',
		component: () => import('@/pages/Courses/CourseCertification.vue'),
		props: true,
	},
	{
		path: '/course-feedback',
		redirect: '/courses',
	},
	{
		path: '/course-feedback/:courseName',
		name: 'CourseFeedback',
		component: () => import('@/pages/Courses/CourseFeedback.vue'),
		props: true,
	},
	{
		path: '/certificate/:certificateName',
		name: 'CertificatePreview',
		component: () => import('@/pages/Certificates/CertificatePreview.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/learn/:chapterName',
		name: 'SCORMChapter',
		component: () => import('@/pages/SCORMChapter.vue'),
		props: true,
	},
	{
		path: '/batches',
		name: 'Batches',
		component: () => import('@/pages/Batches/Batches.vue'),
	},
	{
		path: '/batches/details/:batchName',
		redirect: (to) => `/batches/${to.params.batchName}`,
	},
	{
		path: '/batches/:batchName/leaderboard',
		name: 'BatchLeaderboard',
		component: () => import('@/pages/Batches/BatchLeaderboard.vue'),
		props: true,
	},
	{
		path: '/batches/:batchName',
		name: 'BatchDetail',
		component: () => import('@/pages/Batches/BatchDetail.vue'),
		props: true,
	},
	{
		path: '/billing/:type/:name',
		name: 'Billing',
		component: () => import('@/pages/Billing.vue'),
		props: true,
	},
	{
		path: '/statistics',
		redirect: { name: 'AnalyticsDashboard' },
	},
	{
		path: '/analytics',
		name: 'AnalyticsDashboard',
		component: () => import('@/pages/AnalyticsDashboard.vue'),
	},
	{
		path: '/analytics-dashboard',
		redirect: (to) => ({
			name: 'AnalyticsDashboard',
			query: to.query,
		}),
	},
	{
		path: '/ojt-certification-analytics',
		redirect: (to) => ({
			name: 'AnalyticsDashboard',
			query: { ...to.query, section: 'certification' },
		}),
	},
	{
		path: '/reports',
		name: 'LearnerReports',
		component: () => import('@/pages/Reports/CombinedReport.vue'),
	},
	{
		path: '/reports/:name',
		name: 'LearnerReportCard',
		component: () => import('@/pages/Reports/LearnerReportCard.vue'),
		props: true,
	},
	{
		path: '/newspaper',
		name: 'Newspaper',
		component: () => import('@/pages/Newspaper/Newspaper.vue'),
	},
	{
		path: '/newspaper/new',
		name: 'NewspaperCreate',
		component: () => import('@/pages/Newspaper/NewspaperCreate.vue'),
	},
	{
		path: '/newspaper/:name',
		name: 'NewspaperDetail',
		component: () => import('@/pages/Newspaper/NewspaperDetail.vue'),
		props: true,
	},
	{
		path: '/library',
		name: 'Library',
		component: () => import('@/pages/Library/Library.vue'),
	},
	{
		path: '/user/:username',
		name: 'Profile',
		component: () => import('@/pages/Profile.vue'),
		props: true,
		redirect: { name: 'ProfileAbout' },
		children: [
			{
				name: 'ProfileAbout',
				path: '',
				component: () => import('@/pages/ProfileAbout.vue'),
			},
			{
				name: 'ProfileCertificates',
				path: 'certificates',
				component: () => import('@/pages/ProfileCertificates.vue'),
			},
			{
				name: 'ProfileRoles',
				path: 'roles',
				component: () => import('@/pages/ProfileRoles.vue'),
			},
			{
				name: 'ProfileEvaluator',
				path: 'slots',
				component: () => import('@/pages/ProfileEvaluator.vue'),
			},
			{
				name: 'ProfileEvaluationSchedule',
				path: 'schedule',
				component: () =>
					import('@/pages/ProfileEvaluationSchedule.vue'),
			},
			{
				name: 'ProfileMockResults',
				path: 'mock-results',
				component: () => import('@/pages/ProfileMockResults.vue'),
			},
		],
	},
	{
		path: '/job-openings',
		name: 'Jobs',
		component: () => import('@/pages/Jobs.vue'),
	},
	{
		path: '/job-openings/:job',
		name: 'JobDetail',
		component: () => import('@/pages/JobDetail.vue'),
		props: true,
	},
	{
		path: '/job-openings/:job/applications',
		name: 'JobApplications',
		component: () => import('@/pages/JobApplications.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/learn/:chapterNumber-:lessonNumber/edit',
		name: 'LessonForm',
		component: () => import('@/pages/LessonForm.vue'),
		props: true,
	},
	{
		path: '/job-opening/:jobName/edit',
		name: 'JobForm',
		component: () => import('@/pages/JobForm.vue'),
		props: true,
	},
	{
		path: '/certified-participants',
		name: 'CertifiedParticipants',
		component: () => import('@/pages/CertifiedParticipants.vue'),
	},
	{
		path: '/notifications',
		name: 'Notifications',
		component: () => import('@/pages/Notifications.vue'),
	},
	{
		path: '/quizzes',
		name: 'Quizzes',
		component: () => import('@/pages/Quizzes.vue'),
	},
	{
		path: '/quizzes/:quizID',
		name: 'QuizForm',
		component: () => import('@/pages/QuizForm.vue'),
		props: true,
	},
	{
		path: '/quiz/:quizID',
		name: 'QuizPage',
		component: () => import('@/pages/QuizPage.vue'),
		props: true,
	},
	{
		path: '/quiz-submissions/:quizID',
		name: 'QuizSubmissionList',
		component: () => import('@/pages/QuizSubmissionList.vue'),
		props: true,
	},
	{
		path: '/quiz-submission/:submission',
		name: 'QuizSubmission',
		component: () => import('@/pages/QuizSubmission.vue'),
		props: true,
	},
	{
		path: '/programs',
		name: 'Programs',
		component: () => import('@/pages/Programs/Programs.vue'),
	},
	{
		path: '/programs/:programName',
		name: 'ProgramDetail',
		component: () => import('@/pages/Programs/ProgramDetail.vue'),
		props: true,
	},
	{
		path: '/assignments',
		name: 'Assignments',
		component: () => import('@/pages/Assignments.vue'),
	},
	{
		path: '/assignment-submission/:assignmentID/:submissionName',
		name: 'AssignmentSubmission',
		component: () => import('@/pages/AssignmentSubmission.vue'),
		props: true,
	},
	{
		path: '/assignment-submissions',
		name: 'AssignmentSubmissionList',
		component: () => import('@/pages/AssignmentSubmissionList.vue'),
	},
	{
		path: '/persona',
		name: 'PersonaForm',
		component: () => import('@/pages/PersonaForm.vue'),
	},
	{
		path: '/programming-exercises',
		name: 'ProgrammingExercises',
		component: () =>
			import('@/pages/ProgrammingExercises/ProgrammingExercises.vue'),
	},
	{
		path: '/programming-exercises/submissions',
		name: 'ProgrammingExerciseSubmissions',
		component: () =>
			import(
				'@/pages/ProgrammingExercises/ProgrammingExerciseSubmissions.vue'
			),
		props: true,
	},
	{
		path: '/programming-exercises/:exerciseID/submission/:submissionID',
		name: 'ProgrammingExerciseSubmission',
		component: () =>
			import(
				'@/pages/ProgrammingExercises/ProgrammingExerciseSubmission.vue'
			),
		props: true,
	},
	{
		path: '/search',
		name: 'Search',
		component: () => import('@/pages/Search/Search.vue'),
	},
	{
		path: '/data-import',
		name: 'DataImportList',
		component: () => import('@/pages/DataImport.vue'),
	},
	{
		path: '/data-import/doctype/:doctype',
		name: 'NewDataImport',
		component: () => import('@/pages/DataImport.vue'),
		props: true,
	},
	{
		path: '/data-import/:importName',
		name: 'DataImport',
		component: () => import('@/pages/DataImport.vue'),
		props: true,
	},
]

let router = createRouter({
	history: createWebHistory(getRouterHistoryBase()),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const { userResource } = usersStore()
	let { isLoggedIn } = sessionStore()
	const { settings } = useSettings()

	try {
		if (isLoggedIn) {
			await userResource.promise
		}
	} catch (error) {
		isLoggedIn = false
	}

	if (!to.matched.length) {
		if (!isLoggedIn) {
			window.location.replace('/login')
			return
		}
		return next({ name: 'StudentDashboard', replace: true })
	}

	if (isLoggedIn && (to.name === 'Home' || to.path === '/')) {
		return next({ name: 'StudentDashboard' })
	}

	if (!isLoggedIn) {
		await settings.promise
		if (to.name === 'Home' || to.path === '/') {
			window.location.replace('/login')
			return
		}
		const publicRoutes = [
			'Courses',
			'GeniusCourseDetail',
			'CourseDetail',
		]
		if (!settings.data?.allow_guest_access && !publicRoutes.includes(to.name)) {
			const redirect = encodeURIComponent(to.fullPath || '/dashboard')
			window.location.replace(`/login?redirect-to=${redirect}`)
			return
		}
	}

	// Staff-only analytics / admin surfaces (API already gated; harden UI route)
	const staffOnlyRoutes = [
		'AnalyticsDashboard',
		'AdminDashboard',
		'LearnerReports',
		'LearnerReportCard',
	]
	if (staffOnlyRoutes.includes(to.name)) {
		if (!isLoggedIn) {
			const redirect = encodeURIComponent(to.fullPath || '/dashboard')
			window.location.replace(`/login?redirect-to=${redirect}`)
			return
		}
		const u = userResource.data
		const staff =
			u?.is_moderator ||
			u?.is_instructor ||
			u?.is_evaluator ||
			u?.is_system_manager ||
			// Managers (e.g. Training Managers) get learner reports, scoped server-side.
			(u?.is_manager && ['LearnerReports', 'LearnerReportCard'].includes(to.name))
		if (!staff) {
			return next({ name: 'StudentDashboard' })
		}
	}

	return next()
})

export default router
