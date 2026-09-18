<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>
		<div class="p-5">
			<OJTCertificationAnalytics />
		</div>
	</div>
</template>

<script setup>
import { Breadcrumbs, usePageMeta } from 'frappe-ui'
import { computed, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'
import OJTCertificationAnalytics from '@/components/Analytics/OJTCertificationAnalytics.vue'

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()

watchEffect(() => {
	if (userResource.data?.is_student) {
		router.replace({ name: 'Home' })
	}
})

const breadcrumbs = computed(() => [
	{
		label: __('OJT Certification Analytics'),
		route: { name: 'OJTCertificationAnalytics' },
	},
])

usePageMeta(() => ({
	title: __('OJT Certification Analytics'),
	icon: brand.favicon,
}))
</script>
