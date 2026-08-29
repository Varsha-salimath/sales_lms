import { h, createApp } from 'vue'
import { ThumbsUp } from 'lucide-vue-next'

export class FeedbackBlock {
	constructor({ data, api, readOnly }) {
		this.data = data || {}
		this.api = api
		this.readOnly = readOnly
		this.wrapper = null
	}

	static get toolbox() {
		const app = createApp({
			render: () =>
				h(ThumbsUp, { size: 18, strokeWidth: 1.5, color: 'black' }),
		})
		const div = document.createElement('div')
		app.mount(div)

		return {
			title: 'Feedback Button',
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		this.wrapper.classList.add('feedback-block')

		if (this.readOnly) {
			this._renderStudentView()
		} else {
			this._renderEditorView()
		}

		return this.wrapper
	}

	_renderEditorView() {
		this.wrapper.innerHTML = `
			<div style="border:2px dashed #D1D5DB; border-radius:12px; padding:24px; text-align:center; background:#F9FAFB; margin:16px 0;">
				<div style="font-weight:600; font-size:14px; color:#374151; margin-bottom:8px;">
					Lesson Feedback Widget
				</div>
				<div style="font-size:13px; color:#6B7280;">
					Students will see "Was this lesson helpful?" with Yes/No buttons and a Next Lesson button here.
				</div>
			</div>
		`
	}

	_renderStudentView() {
		this.wrapper.innerHTML = `
			<div class="feedback-widget" style="background:#1F2937; border-radius:12px; padding:24px 32px; margin:24px 0; color:#fff;">
				<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px;">
					<div>
						<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
							<span class="feedback-status-badge" style="background:#10B981; color:#fff; font-size:11px; font-weight:600; padding:2px 8px; border-radius:4px;">Completed</span>
						</div>
						<div style="font-size:16px; font-weight:600; color:#F9FAFB;">
							Was this lesson helpful?
						</div>
					</div>
					<div style="display:flex; align-items:center; gap:12px;">
						<button class="feedback-yes-btn" style="display:flex; align-items:center; gap:6px; padding:8px 16px; border-radius:8px; border:2px solid #374151; background:transparent; color:#D1D5DB; font-size:14px; font-weight:500; cursor:pointer; transition:all 0.2s;">
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/></svg>
							Yes
						</button>
						<button class="feedback-no-btn" style="display:flex; align-items:center; gap:6px; padding:8px 16px; border-radius:8px; border:2px solid #374151; background:transparent; color:#D1D5DB; font-size:14px; font-weight:500; cursor:pointer; transition:all 0.2s;">
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z"/></svg>
							No
						</button>
						<button class="feedback-next-btn" style="display:flex; align-items:center; gap:6px; padding:8px 20px; border-radius:8px; border:none; background:#4F46E5; color:#fff; font-size:14px; font-weight:600; cursor:pointer; transition:all 0.2s;">
							Next Lesson
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
						</button>
					</div>
				</div>
			</div>
		`

		const yesBtn = this.wrapper.querySelector('.feedback-yes-btn')
		const noBtn = this.wrapper.querySelector('.feedback-no-btn')
		const nextBtn = this.wrapper.querySelector('.feedback-next-btn')

		yesBtn.addEventListener('click', () =>
			this._submitFeedback('Yes', yesBtn, noBtn)
		)
		noBtn.addEventListener('click', () =>
			this._submitFeedback('No', noBtn, yesBtn)
		)
		nextBtn.addEventListener('click', () => this._navigateNext())

		this._loadExistingFeedback(yesBtn, noBtn)
	}

	_getRouteParams() {
		const path = window.location.pathname
		const match = path.match(
			/\/lms\/courses\/([^/]+)\/learn\/(\d+)-(\d+)/
		)
		if (!match) return null
		return { course: match[1], chapter: match[2], lesson: match[3] }
	}

	_submitFeedback(reaction, activeBtn, inactiveBtn) {
		const params = this._getRouteParams()
		if (!params) return

		this._setActiveState(activeBtn, inactiveBtn)

		fetch('/api/method/lms.lms.api.save_lesson_feedback', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token':
					window.csrf_token ||
					document.cookie
						.split('; ')
						.find((c) => c.startsWith('csrf_token='))
						?.split('=')[1] ||
					'',
			},
			body: JSON.stringify({
				course: params.course,
				chapter: params.chapter,
				lesson: params.lesson,
				reaction,
			}),
		})
			.then((r) => r.json())
			.then((data) => {
				if (data.exc) {
					console.error('Feedback save failed:', data.exc)
				}
			})
			.catch((err) => console.error('Feedback save error:', err))
	}

	_loadExistingFeedback(yesBtn, noBtn) {
		const params = this._getRouteParams()
		if (!params) return

		fetch(
			`/api/method/lms.lms.api.get_lesson_feedback?course=${encodeURIComponent(params.course)}&chapter=${params.chapter}&lesson=${params.lesson}`,
			{
				headers: {
					'X-Frappe-CSRF-Token':
						window.csrf_token ||
						document.cookie
							.split('; ')
							.find((c) => c.startsWith('csrf_token='))
							?.split('=')[1] ||
						'',
				},
			}
		)
			.then((r) => r.json())
			.then((data) => {
				const reaction = data?.message?.user_reaction
				if (reaction === 'Yes') {
					this._setActiveState(yesBtn, noBtn)
				} else if (reaction === 'No') {
					this._setActiveState(noBtn, yesBtn)
				}
			})
			.catch(() => {})
	}

	_setActiveState(activeBtn, inactiveBtn) {
		activeBtn.style.borderColor = '#10B981'
		activeBtn.style.background = '#064E3B'
		activeBtn.style.color = '#6EE7B7'

		inactiveBtn.style.borderColor = '#374151'
		inactiveBtn.style.background = 'transparent'
		inactiveBtn.style.color = '#D1D5DB'
	}

	_navigateNext() {
		window.dispatchEvent(new CustomEvent('lms-feedback-next-lesson'))
	}

	validate() {
		return true
	}

	save() {
		return { lesson_feedback_widget: true }
	}
}
