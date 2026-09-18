import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSidebar = defineStore('sidebar', () => {
	const isSidebarCollapsed = ref(false)
	const isWebpagesCollapsed = ref(true)
	const isPracticeHubCollapsed = ref(true)

	if (localStorage.getItem('isSidebarCollapsed')) {
		isSidebarCollapsed.value = JSON.parse(
			localStorage.getItem('isSidebarCollapsed')
		)
	}

	if (localStorage.getItem('isWebpagesCollapsed')) {
		isWebpagesCollapsed.value = JSON.parse(
			localStorage.getItem('isWebpagesCollapsed')
		)
	}

	if (localStorage.getItem('isPracticeHubCollapsed')) {
		isPracticeHubCollapsed.value = JSON.parse(
			localStorage.getItem('isPracticeHubCollapsed')
		)
	}

	return {
		isSidebarCollapsed,
		isWebpagesCollapsed,
		isPracticeHubCollapsed,
	}
})
