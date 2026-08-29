<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Make an Announcement'),
			size: 'xl',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					onClick: (close) => makeAnnouncement(close),
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div
					class="rounded-md border border-outline-blue-1 bg-surface-blue-1 px-3 py-2 text-sm text-ink-blue-3"
				>
					{{
						`${__('This announcement will be emailed to all')} ${props.students.length} ${__('students enrolled in this batch.')}`
					}}
				</div>
				<FormControl
					:label="__('Subject')"
					type="text"
					v-model="announcement.subject"
					:required="true"
				/>
				<FormControl
					:label="__('Reply-To email')"
					type="email"
					v-model="announcement.replyTo"
					:required="true"
					:description="
						__(
							'Students can reply to this address. The announcement itself is sent to everyone in the batch.'
						)
					"
				/>
				<div class="mb-4">
					<div class="mb-1.5 text-sm text-ink-gray-5">
						{{ __('Announcement') }}
						<span class="text-ink-red-3">*</span>
					</div>
					<TextEditor
						:fixedMenu="true"
						@change="(val) => (announcement.announcement = val)"
						editorClass="prose-sm py-2 px-2 min-h-[200px] border-outline-gray-2 hover:border-outline-gray-3 rounded-b-md bg-surface-gray-3"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	FormControl,
	TextEditor,
	createResource,
	toast,
} from 'frappe-ui'
import { inject, reactive, watch } from 'vue'

const show = defineModel()
const user = inject('$user')

const props = defineProps({
	batch: {
		type: String,
		required: true,
	},
	students: {
		type: Array,
		required: true,
	},
})

const announcement = reactive({
	subject: '',
	replyTo: '',
	announcement: '',
})

watch(show, (open) => {
	if (!open) return
	if (!announcement.replyTo && user?.data?.email) {
		announcement.replyTo = user.data.email
	}
})

const announcementResource = createResource({
	url: 'frappe.core.doctype.communication.email.make',
	makeParams(values) {
		return {
			recipients: announcement.replyTo,
			bcc: props.students.join(', '),
			subject: announcement.subject,
			content: announcement.announcement,
			doctype: 'LMS Batch',
			name: props.batch,
			send_email: 1,
			send_me_a_copy: 1,
		}
	},
})

const makeAnnouncement = (close) => {
	announcementResource.submit(
		{},
		{
			validate() {
				if (!props.students.length) {
					return __('No students in this batch')
				}
				if (!announcement.subject) {
					return __('Subject is required')
				}
				if (!announcement.announcement) {
					return __('Announcement is required')
				}
				if (!announcement.replyTo) {
					return __('Reply-To email is required')
				}
			},
			onSuccess() {
				close()
				toast.success(__('Announcement has been sent successfully'))
			},
			onError(err) {
				toast.error(__(err.messages?.[0] || err))
			},
		}
	)
}
</script>
