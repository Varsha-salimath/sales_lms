import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { usersStore } from './user'
import { computed, reactive, ref } from 'vue'

export const sessionStore = defineStore('lms-session', () => {
	let { userResource } = usersStore()
	const brand = reactive({})

	function sessionUser() {
		let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
		let _sessionUser = cookies.get('user_id')
		if (_sessionUser === 'Guest') {
			_sessionUser = null
		} else {
			userResource.reload()
		}
		return _sessionUser
	}

	let user = ref(sessionUser())
	const isLoggedIn = computed(() => !!user.value)

	const goToLogin = () => {
		userResource.reset()
		user.value = null
		window.location.href = '/login'
	}

	const logout = createResource({
		url: 'logout',
		onSuccess() {
			goToLogin()
		},
		onError() {
			goToLogin()
		},
	})

	const branding = createResource({
		url: 'lms.lms.api.get_branding',
		cache: 'brand',
		auto: true,
		onSuccess(data) {
			brand.name = data.app_name
			brand.logo = data.app_logo
			brand.favicon =
				data.favicon?.file_url || '/assets/lms/images/il-favicon.png'
		},
	})

	return {
		user,
		isLoggedIn,
		logout,
		brand,
		branding,
	}
})
