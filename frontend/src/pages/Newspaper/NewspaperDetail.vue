<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
			<div class="flex gap-2">
				<Button
					v-if="isAdmin"
					theme="red"
					variant="outline"
					:loading="deleting"
					@click="confirmDelete"
				>
					{{ __('Delete') }}
				</Button>
				<Button @click="router.push({ name: 'Newspaper' })">
					{{ __('Back to History') }}
				</Button>
			</div>
		</header>

		<div class="mx-auto max-w-3xl p-5">
			<div v-if="detail.loading" class="text-sm text-ink-gray-5">
				{{ __('Loading newsletter...') }}
			</div>

			<div v-else-if="detail.data" class="space-y-6">
				<div>
					<h1 class="text-2xl font-semibold text-ink-gray-9">
						{{ detail.data.title }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-5">{{ __('Newsletter') }}</p>
				</div>

				<img
					v-if="detail.data.image"
					:src="detail.data.image"
					class="max-h-80 w-full rounded-xl border object-cover"
					:alt="detail.data.title"
				/>

				<div
					class="prose prose-sm max-w-none rounded-xl border bg-surface-white p-5 text-ink-gray-8"
					v-html="detail.data.content"
				/>

				<div class="grid gap-3 rounded-xl border bg-surface-gray-2 p-5 text-sm">
					<div v-if="isAdmin">
						<span class="font-medium text-ink-gray-7">{{ __('Target') }}:</span>
						{{ detail.data.target_label }}
					</div>
					<div v-if="isAdmin">
						<span class="font-medium text-ink-gray-7"
							>{{ __('Recipients') }}:</span
						>
						{{ detail.data.recipient_count }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Published by') }}:</span
						>
						{{ detail.data.published_by_name || detail.data.published_by }}
					</div>
					<div>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Published') }}:</span
						>
						{{ formatDateTime(detail.data.published_at) }}
					</div>
					<div v-if="isAdmin">
						<span class="font-medium text-ink-gray-7">{{ __('Status') }}:</span>
						<span
							:class="
								detail.data.status === 'Sent'
									? 'text-ink-green-3'
									: detail.data.status === 'Failed'
										? 'text-ink-red-3'
										: 'text-ink-orange-3'
							"
						>
							{{ detail.data.status }}
						</span>
					</div>
					<div
						v-if="
							isAdmin &&
							(detail.data.email_sent_count || detail.data.email_failed_count)
						"
					>
						<span class="font-medium text-ink-gray-7"
							>{{ __('Email delivery') }}:</span
						>
						{{ __('Sent') }} {{ detail.data.email_sent_count || 0 }},
						{{ __('Failed') }} {{ detail.data.email_failed_count || 0 }}
					</div>
				</div>

				<section class="rounded-xl border bg-surface-white p-5">
					<h2 class="text-base font-semibold text-ink-gray-9">
						{{ __('Comments') }}
					</h2>
					<div v-if="comments.loading" class="mt-3 text-sm text-ink-gray-5">
						{{ __('Loading comments...') }}
					</div>
					<div v-else class="mt-4 space-y-4">
						<p
							v-if="!threadedComments.length"
							class="text-sm text-ink-gray-5"
						>
							{{ __('No comments yet.') }}
						</p>
						<div
							v-for="comment in threadedComments"
							:key="comment.name"
							class="rounded-lg border px-3 py-2 text-sm"
							:class="comment.is_staff_reply ? 'border-outline-blue-1 bg-surface-blue-1' : ''"
						>
							<div class="flex items-center justify-between gap-2">
								<span class="font-medium text-ink-gray-8">
									{{ comment.author_name || comment.author }}
									<span
										v-if="comment.is_staff_reply"
										class="ms-1 text-xs font-normal text-ink-blue-3"
									>
										{{ __('Staff') }}
									</span>
								</span>
								<span class="text-xs text-ink-gray-5">
									{{ formatDateTime(comment.creation) }}
								</span>
							</div>
							<div
								class="prose prose-sm mt-2 max-w-none text-ink-gray-7"
								v-html="comment.content"
							/>
							<div v-if="isAdmin" class="mt-2">
								<Button variant="outline" size="sm" @click="startReply(comment)">
									{{ __('Reply') }}
								</Button>
							</div>
							<div
								v-for="reply in comment.replies"
								:key="reply.name"
								class="mt-3 ms-4 rounded-lg border bg-surface-gray-1 px-3 py-2"
								:class="reply.is_staff_reply ? 'border-outline-blue-1 bg-surface-blue-1' : ''"
							>
								<div class="flex items-center justify-between gap-2">
									<span class="font-medium text-ink-gray-8">
										{{ reply.author_name || reply.author }}
									</span>
									<span class="text-xs text-ink-gray-5">
										{{ formatDateTime(reply.creation) }}
									</span>
								</div>
								<div
									class="prose prose-sm mt-2 max-w-none text-ink-gray-7"
									v-html="reply.content"
								/>
							</div>
						</div>
					</div>
					<div class="mt-4 space-y-2">
						<p
							v-if="replyingTo"
							class="text-xs text-ink-gray-6"
						>
							{{ __('Replying to') }} {{ replyingTo.author_name || replyingTo.author }}
							<button type="button" class="ms-2 text-ink-blue-3" @click="cancelReply">
								{{ __('Cancel') }}
							</button>
						</p>
						<TextEditor
							:key="replyEditorKey"
							:fixedMenu="true"
							@change="(val) => (newComment = val)"
							editorClass="prose-sm min-h-[100px] rounded-md border border-outline-gray-2 bg-surface-gray-2 px-3 py-2"
						/>
						<div class="flex justify-end">
							<Button
								variant="solid"
								:loading="postingComment"
								@click="submitComment"
							>
								{{
									replyingTo
										? __('Post reply')
										: isAdmin
											? __('Post comment')
											: __('Post comment')
								}}
							</Button>
						</div>
					</div>
				</section>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	TextEditor,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const { brand } = sessionStore()
const { userResource } = usersStore()
const isAdmin = computed(() => {
	const user = userResource.data
	return !!(
		user?.is_moderator ||
		user?.is_instructor ||
		user?.is_evaluator ||
		user?.is_system_manager
	)
})

const breadcrumbs = computed(() => [
	{ label: __('Newsletter'), route: { name: 'Newspaper' } },
	{ label: props.name, route: { name: 'NewspaperDetail', params: { name: props.name } } },
])

const detail = createResource({
	url: 'lms.lms.newspaper.get_newspaper',
	makeParams() {
		return { name: props.name }
	},
	auto: true,
})

const comments = createResource({
	url: 'lms.lms.newspaper.get_newspaper_comments',
	makeParams() {
		return { newspaper: props.name }
	},
	auto: true,
})

const newComment = ref('')
const postingComment = ref(false)
const deleting = ref(false)
const replyingTo = ref(null)
const replyEditorKey = ref(0)

const threadedComments = computed(() => {
	const rows = comments.data || []
	const roots = rows.filter((row) => !row.parent_comment)
	const byParent = {}
	for (const row of rows) {
		if (!row.parent_comment) continue
		byParent[row.parent_comment] = byParent[row.parent_comment] || []
		byParent[row.parent_comment].push(row)
	}
	return roots.map((root) => ({
		...root,
		replies: byParent[root.name] || [],
	}))
})

const submitComment = async () => {
	const plain = newComment.value?.replace(/<[^>]+>/g, '').trim()
	if (!plain) {
		toast.error(__('Comment cannot be empty.'))
		return
	}
	postingComment.value = true
	try {
		await call('lms.lms.newspaper.add_newspaper_comment', {
			newspaper: props.name,
			content: newComment.value,
			parent_comment: replyingTo.value?.name || null,
		})
		newComment.value = ''
		replyingTo.value = null
		replyEditorKey.value += 1
		comments.reload()
		toast.success(__('Comment posted'))
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Could not post comment'))
	} finally {
		postingComment.value = false
	}
}

const startReply = (comment) => {
	replyingTo.value = comment
	replyEditorKey.value += 1
}

const cancelReply = () => {
	replyingTo.value = null
	replyEditorKey.value += 1
}

const confirmDelete = async () => {
	if (
		!window.confirm(
			__('Delete this newsletter permanently? Comments will also be removed.')
		)
	) {
		return
	}
	deleting.value = true
	try {
		await call('lms.lms.newspaper.delete_newspaper', { name: props.name })
		toast.success(__('Newsletter deleted'))
		router.push({ name: 'Newspaper' })
	} catch (err) {
		toast.error(err.messages?.[0] || err.message || __('Could not delete newsletter'))
	} finally {
		deleting.value = false
	}
}

usePageMeta(() => ({
	title: __('Newsletter'),
	icon: brand.favicon,
}))

const formatDateTime = (value) => {
	if (!value) return '—'
	return new Date(value).toLocaleString(undefined, {
		day: '2-digit',
		month: 'long',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	})
}
</script>
