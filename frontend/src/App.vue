<template>
	<FrappeUIProvider>
		<Layout class="isolate text-p-base">
			<router-view />
		</Layout>
		<InstallPrompt v-if="isMobile && !settings.data?.disable_pwa" />
		<Dialogs />
	</FrappeUIProvider>
</template>
<script setup>
import { FrappeUIProvider } from 'frappe-ui'
import { Dialogs } from '@/utils/dialogs'
import { computed, onUnmounted, ref } from 'vue'
import { useScreenSize } from './utils/composables'
import { useSettings } from '@/stores/settings'
import { useRouter } from 'vue-router'
import DesktopLayout from './components/Layouts/DesktopLayout.vue'
import MobileLayout from './components/Layouts/MobileLayout.vue'
import NoSidebarLayout from './components/Layouts/NoSidebarLayout.vue'
import InstallPrompt from './components/InstallPrompt.vue'
import { useActivityTracking } from '@/utils/useActivityTracking'

const { isMobile } = useScreenSize()
const router = useRouter()
const noSidebar = ref(false)
const { settings } = useSettings()

useActivityTracking()

router.beforeEach((to, from, next) => {
	const isPlayer =
		to.name === 'GeniusScormPlayer' ||
		to.name === 'SCORMChapter' ||
		/\/course\/[^/]+\/player/.test(to.path)
	if (
		to.query.fromLesson ||
		to.path === '/persona' ||
		to.name === 'Home' ||
		isPlayer
	) {
		noSidebar.value = true
	} else {
		noSidebar.value = false
	}
	next()
})

const Layout = computed(() => {
	if (noSidebar.value) {
		return NoSidebarLayout
	}
	if (isMobile.value) {
		return MobileLayout
	}
	return DesktopLayout
})

onUnmounted(() => {
	noSidebar.value = false
})
</script>
