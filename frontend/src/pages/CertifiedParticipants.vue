<template>
	<header
		class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<router-link
			v-if="!isPersonalView"
			:to="{ name: 'Courses', query: { certification: true } }"
		>
			<Button>
				<template #prefix>
					<GraduationCap class="h-4 w-4 stroke-1.5" />
				</template>
				{{ __('Get Certified') }}
			</Button>
		</router-link>
		<router-link
			v-else
			:to="{ name: 'Courses', query: { certification: true } }"
		>
			<Button>
				<template #prefix>
					<GraduationCap class="h-4 w-4 stroke-1.5" />
				</template>
				{{ __('Browse courses') }}
			</Button>
		</router-link>
	</header>

	<!-- Student: only their own certificates -->
	<div v-if="isPersonalView" class="mx-auto w-full px-5 pt-5 pb-8">
		<div class="mb-5 text-lg font-semibold text-ink-gray-9">
			{{ __('My Certificates') }}
			<span
				v-if="myCertificates.data?.length"
				class="ms-2 text-base font-normal text-ink-gray-6"
			>
				({{ myCertificates.data.length }})
			</span>
		</div>
		<div
			v-if="myCertificates.data?.length"
			class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
		>
			<button
				v-for="certificate in myCertificates.data"
				:key="certificate.name"
				type="button"
				class="flex flex-col rounded-lg border border-outline-gray-2 bg-surface-white p-4 text-left hover:border-outline-gray-3"
				@click="openCertificate(certificate)"
			>
				<div class="mb-3 flex items-center gap-2 text-ink-gray-9">
					<GraduationCap class="h-5 w-5 stroke-1.5 text-ink-gray-7" />
					<div class="font-semibold leading-5">
						{{ certificate.course_title || certificate.batch_title || __('Certificate') }}
					</div>
				</div>
				<div class="mt-auto flex items-center gap-2 text-sm text-ink-gray-7">
					<Calendar class="h-4 w-4 stroke-1.5" />
					<span>
						{{ __('Issued on') }}
						{{ dayjs(certificate.issue_date).format('DD MMM YYYY') }}
					</span>
				</div>
			</button>
		</div>
		<div v-else class="rounded-lg border border-dashed border-outline-gray-2 px-5 py-12 text-center">
			<p class="text-ink-gray-7">
				{{ __('You have not received any certificates yet.') }}
			</p>
			<router-link
				:to="{ name: 'Courses', query: { certification: true } }"
				class="mt-3 inline-flex text-sm font-medium text-ink-gray-9 underline"
			>
				{{ __('Complete a course to earn one') }}
			</router-link>
		</div>
	</div>

	<!-- Staff: all issued certificates -->
	<div v-else class="mx-auto w-full px-5 pt-5 pb-8">
		<IssuedCertificatesList :title="__('Certified users')" />
	</div>
</template>
<script setup>
import { Breadcrumbs, Button, createListResource, usePageMeta } from 'frappe-ui'
import { computed, inject, onMounted } from 'vue'
import { GraduationCap, Calendar } from 'lucide-vue-next'
import { sessionStore } from '../stores/session'
import { useRouter } from 'vue-router'
import IssuedCertificatesList from '@/components/Analytics/IssuedCertificatesList.vue'
import { openCertificatePreview } from '@/utils/certificate'

const { brand } = sessionStore()
const dayjs = inject('$dayjs')
const user = inject('$user')
const router = useRouter()

function canViewStaffCertificateDirectory(u) {
	if (!u) return false
	return Boolean(
		u.is_moderator ||
			u.is_system_manager ||
			u.is_instructor ||
			u.is_training_manager ||
			u.is_manager
	)
}

const isPersonalView = computed(() => {
	const u = user.data
	if (!u) return true
	return !canViewStaffCertificateDirectory(u)
})

const myCertificates = createListResource({
	doctype: 'LMS Certificate',
	fields: ['name', 'course_title', 'batch_title', 'issue_date', 'template', 'course'],
	orderBy: 'issue_date desc',
	auto: false,
	cache: ['my-certificates', user.data?.name],
})

const openCertificate = (certificate) => {
	openCertificatePreview(certificate)
}

onMounted(() => {
	if (!user.data) {
		router.push({ name: 'Courses' })
		return
	}
	if (isPersonalView.value) {
		myCertificates.update({
			filters: { member: user.data.name },
		})
		myCertificates.reload()
	}
})

const breadcrumbs = computed(() => [
	{
		label: isPersonalView.value ? __('My Certificates') : __('Certified users'),
		route: { name: 'CertifiedParticipants' },
	},
])

usePageMeta(() => {
	return {
		title: isPersonalView.value ? __('My Certificates') : __('Certified users'),
		icon: brand.favicon,
	}
})
</script>
<style>
.headline {
	display: -webkit-box;
	-webkit-line-clamp: 1;
	-webkit-box-orient: vertical;
	text-overflow: ellipsis;
	width: 100%;
	overflow: hidden;
}
</style>
