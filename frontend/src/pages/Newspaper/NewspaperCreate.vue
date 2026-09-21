<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>

		<div class="mx-auto max-w-6xl p-5">
			<h1 class="mb-6 text-2xl font-semibold text-ink-gray-9">
				{{ __('Create Newsletter') }}
			</h1>

			<div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
				<div class="space-y-5 rounded-xl border bg-surface-white p-5">
					<FormControl
						:label="__('Title')"
						v-model="form.title"
						type="text"
						:required="true"
					/>

					<div
						v-if="limits.data?.outgoing_sender"
						class="rounded-lg border border-outline-gray-2 bg-surface-gray-2 px-3 py-2 text-sm text-ink-gray-7"
					>
						{{ __('Sent from') }}:
						<span class="font-medium">{{ limits.data.outgoing_sender }}</span>
						<p class="mt-1 text-xs text-ink-gray-5">
							{{
								__(
									'Same outgoing address and email layout as the welcome / registration message.'
								)
							}}
						</p>
					</div>

					<div>
						<div class="mb-2 text-sm text-ink-gray-5">{{ __('Image') }}</div>
						<div
							class="rounded-lg border border-dashed border-outline-gray-3 bg-surface-gray-2 p-4 text-center"
						>
							<div v-if="!form.image">
								<FileUploader
									:fileTypes="['image/*']"
									:validateFile="validateImage"
									@success="onImageUploaded"
								>
									<template
										#default="{ openFileSelector, uploading, progress }"
									>
										<Button
											:loading="uploading"
											@click="openFileSelector"
										>
											{{
												uploading
													? `${__('Uploading')} ${progress}%`
													: __('Upload Image')
											}}
										</Button>
										<p class="mt-2 text-xs text-ink-gray-5">
											{{ __('PNG, JPG, or WEBP up to 5 MB') }}
										</p>
									</template>
								</FileUploader>
							</div>
							<div v-else class="flex items-center gap-4">
								<img
									:src="form.image"
									class="h-28 w-28 rounded-lg border object-cover"
									alt=""
								/>
								<Button variant="outline" @click="form.image = ''">
									{{ __('Remove') }}
								</Button>
							</div>
						</div>
					</div>

					<div>
						<div class="mb-1.5 text-sm text-ink-gray-5">
							{{ __('Message') }}
							<span class="text-ink-red-3">*</span>
						</div>
						<TextEditor
							:fixedMenu="true"
							@change="(val) => (form.content = val)"
							editorClass="prose-sm min-h-[180px] rounded-md border border-outline-gray-2 bg-surface-gray-2 px-3 py-2"
						/>
						<div class="mt-1 text-xs text-ink-gray-5">
							{{ plainLength }} / {{ limits.data?.max_content_length || 5000 }}
						</div>
					</div>

					<div>
						<div class="mb-2 text-sm font-medium text-ink-gray-7">
							{{ __('Send To') }}
						</div>
						<div class="space-y-2">
							<label class="flex items-center gap-2 text-sm">
								<input
									type="radio"
									value="All Learners"
									v-model="form.target_type"
								/>
								{{ __('All Learners') }}
							</label>
							<label class="flex items-center gap-2 text-sm">
								<input
									type="radio"
									value="Selected Batch"
									v-model="form.target_type"
								/>
								{{ __('Select Batch') }}
							</label>
							<label class="flex items-center gap-2 text-sm">
								<input
									type="radio"
									value="Selected Members"
									v-model="form.target_type"
								/>
								{{ __('Select Members') }}
							</label>
						</div>

						<div
							v-if="form.target_type === 'Selected Members'"
							class="mt-3"
						>
							<MultiSelect
								v-model="form.selectedMembers"
								doctype="User"
								:label="__('Learners')"
								:required="true"
								url="lms.lms.api.search_users_by_role"
								:searchParams="{ roles: JSON.stringify(['LMS Student']) }"
							/>
						</div>

						<div
							v-if="form.target_type === 'Selected Batch'"
							class="mt-3 max-h-48 space-y-2 overflow-y-auto rounded-lg border p-3"
						>
							<label
								v-for="batch in batches.data || []"
								:key="batch.name"
								class="flex items-center gap-2 text-sm"
							>
								<input
									type="checkbox"
									:value="batch.name"
									v-model="form.selectedBatches"
								/>
								{{ batch.title || batch.name }}
							</label>
						</div>
					</div>

					<div
						class="rounded-lg border border-outline-blue-1 bg-surface-blue-1 px-3 py-2 text-sm text-ink-blue-3"
					>
						{{ __('Recipients') }}:
						<span class="font-semibold">{{ recipientCount.data?.count ?? 0 }}</span>
						{{ __('learners') }}
					</div>

					<div class="flex justify-end gap-2 pt-2">
						<Button @click="router.push({ name: 'Newspaper' })">
							{{ __('Cancel') }}
						</Button>
						<Button variant="solid" :loading="sending" @click="openConfirm">
							{{ __('Send Newsletter') }}
						</Button>
					</div>
				</div>

				<div class="rounded-xl border bg-surface-gray-2 p-5">
					<h2 class="mb-4 text-base font-semibold text-ink-gray-8">
						{{ __('Preview') }}
					</h2>
					<div class="overflow-hidden rounded-xl border bg-white shadow-sm">
						<div class="bg-[#0075ff] px-4 py-3 text-sm font-semibold text-white">
							{{ __('LMS') }}
						</div>
						<div class="p-5">
							<h3 class="text-xl font-semibold text-ink-gray-9">
								{{ form.title || __('Newsletter Title') }}
							</h3>
							<img
								v-if="form.image"
								:src="form.image"
								class="mt-4 max-h-56 w-full rounded-lg object-cover"
								alt=""
							/>
							<div
								class="prose prose-sm mt-4 max-w-none text-ink-gray-7"
								v-html="form.content || `<p>${__('Your message will appear here...')}</p>`"
							/>
							<div class="mt-6 border-t pt-4 text-xs text-ink-gray-5">
								<div>{{ __('Sent to') }}: {{ previewTargetLabel }}</div>
								<div>
									{{ __('Recipients') }}:
									{{ recipientCount.data?.count ?? 0 }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showConfirm"
			:options="{
				title: __('Confirm Send'),
				size: 'md',
				actions: [
					{ label: __('Cancel'), onClick: (close) => close() },
					{
						label: __('Confirm & Send'),
						variant: 'solid',
						onClick: (close) => confirmSend(close),
					},
				],
			}"
		>
			<template #body-content>
				<p class="text-sm text-ink-gray-7">
					{{
						__('Send this newsletter to {0} learners?', [
							String(recipientCount.data?.count ?? 0),
						])
					}}
				</p>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	Dialog,
	FileUploader,
	FormControl,
	TextEditor,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, reactive, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'
import { validateFile } from '@/utils'
import MultiSelect from '@/components/Controls/MultiSelect.vue'

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()

const form = reactive({
	title: '',
	content: '',
	image: '',
	target_type: 'All Learners',
	selectedBatches: [],
	selectedMembers: [],
})

watchEffect(() => {
	if (userResource.data?.is_student) {
		router.replace({ name: 'StudentDashboard' })
	}
})

const breadcrumbs = computed(() => [
	{ label: __('Newsletter'), route: { name: 'Newspaper' } },
	{ label: __('Create'), route: { name: 'NewspaperCreate' } },
])

const showConfirm = ref(false)
const sending = ref(false)

const limits = createResource({
	url: 'lms.lms.newspaper.get_newspaper_limits',
	auto: true,
})

const batches = createResource({
	url: 'lms.lms.newspaper.get_newspaper_batches',
	auto: true,
})

const recipientCount = createResource({
	url: 'lms.lms.newspaper.get_newspaper_recipient_count',
	makeParams() {
		return {
			target_type: form.target_type,
			batches:
				form.target_type === 'Selected Batch'
					? JSON.stringify(form.selectedBatches)
					: JSON.stringify([]),
			members:
				form.target_type === 'Selected Members'
					? JSON.stringify(form.selectedMembers)
					: JSON.stringify([]),
		}
	},
})

watch(
	() => [
		form.target_type,
		form.selectedBatches.slice(),
		form.selectedMembers.slice(),
	],
	() => recipientCount.reload(),
	{ deep: true, immediate: true }
)

const plainLength = computed(() => {
	const div = document.createElement('div')
	div.innerHTML = form.content || ''
	return (div.textContent || div.innerText || '').trim().length
})

const previewTargetLabel = computed(() => {
	if (form.target_type === 'All Learners') return __('All Learners')
	if (form.target_type === 'Selected Members') {
		return form.selectedMembers.length
			? form.selectedMembers.join(', ')
			: __('Select Members')
	}
	const selected = (batches.data || []).filter((b) =>
		form.selectedBatches.includes(b.name)
	)
	return selected.map((b) => b.title || b.name).join(', ') || __('Select Batch')
})

const validateImage = (file) => validateFile(file, true, 'image')

const onImageUploaded = (file) => {
	form.image = file.file_url
}

const openConfirm = () => {
	if (!form.title.trim()) {
		toast.error(__('Title is required'))
		return
	}
	if (form.title.trim().length > (limits.data?.max_title_length || 200)) {
		toast.error(__('Title is too long'))
		return
	}
	if (!plainLength.value) {
		toast.error(__('Message content is required'))
		return
	}
	if (plainLength.value > (limits.data?.max_content_length || 5000)) {
		toast.error(__('Message is too long'))
		return
	}
	if (
		form.target_type === 'Selected Batch' &&
		!form.selectedBatches.length
	) {
		toast.error(__('Select at least one batch'))
		return
	}
	if (
		form.target_type === 'Selected Members' &&
		!form.selectedMembers.length
	) {
		toast.error(__('Select at least one member'))
		return
	}
	if (!recipientCount.data?.count) {
		toast.error(__('No eligible learners found for the selected audience.'))
		return
	}
	showConfirm.value = true
}

const confirmSend = async (close) => {
	sending.value = true
	try {
		const result = await call('lms.lms.newspaper.send_newspaper', {
			title: form.title.trim(),
			content: form.content,
			target_type: form.target_type,
			batches: JSON.stringify(
				form.target_type === 'Selected Batch' ? form.selectedBatches : []
			),
			members: JSON.stringify(
				form.target_type === 'Selected Members' ? form.selectedMembers : []
			),
			image: form.image || null,
		})
		close()
		toast.success(
			__(
				'Newsletter sent successfully. {0} learners were notified.',
				[String(result.recipient_count || 0)]
			)
		)
		router.push({ name: 'Newspaper' })
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Failed to send newsletter'))
	} finally {
		sending.value = false
	}
}

usePageMeta(() => ({
	title: __('Create Newsletter'),
	icon: brand.favicon,
}))
</script>
