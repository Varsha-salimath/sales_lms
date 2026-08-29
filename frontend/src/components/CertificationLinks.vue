<template>
	<Button
		v-if="certification.data && certification.data.certificate"
		@click="downloadCertificate"
		class=""
	>
		<template #prefix>
			<GraduationCap class="size-4 stroke-1.5" />
		</template>
		{{ __('View Certificate') }}
	</Button>
	<router-link
		v-else-if="
			certification.data &&
			certification.data.course_completed &&
			certification.data.can_generate_certificate &&
			!certification.data.paid_certificate
		"
		:to="{ name: 'SalesCertificate' }"
	>
		<Button class="w-full">
			<template #prefix>
				<GraduationCap class="size-4 stroke-1.5" />
			</template>
			{{ __('Get Certificate') }}
		</Button>
	</router-link>
	<div
		v-else-if="
			certification.data &&
			certification.data.membership &&
			certification.data.paid_certificate &&
			user.data?.is_student
		"
	>
		<router-link
			v-if="!certification.data.membership.purchased_certificate"
			:to="{
				name: 'Billing',
				params: {
					type: 'certificate',
					name: courseName,
				},
			}"
		>
			<Button class="w-full">
				<template #prefix>
					<GraduationCap class="size-4 stroke-1.5" />
				</template>
				{{ __('Get Certified') }}
			</Button>
		</router-link>
		<router-link
			v-else-if="!certification.data.membership.certificate"
			:to="{
				name: 'CourseCertification',
				params: {
					courseName: courseName,
				},
			}"
		>
			<Button class="w-full">
				<template #prefix>
					<GraduationCap class="size-4 stroke-1.5" />
				</template>
				{{ __('Get Certified') }}
			</Button>
		</router-link>
	</div>
</template>
<script setup>
import { Button, createResource } from 'frappe-ui'
import { inject } from 'vue'
import { GraduationCap } from 'lucide-vue-next'
import { openCertificatePreview } from '@/utils/certificate'

const user = inject('$user')

const props = defineProps({
	courseName: {
		type: String,
		required: true,
	},
})

const certification = createResource({
	url: 'lms.lms.api.get_certification_details',
	makeParams(values) {
		return {
			course: props.courseName,
		}
	},
	auto: user.data ? true : false,
})

const downloadCertificate = () => {
	openCertificatePreview(certification.data.certificate)
}
</script>
