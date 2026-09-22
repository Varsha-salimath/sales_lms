<template>
	<section class="border rounded-lg bg-surface-white p-4 overflow-hidden min-w-0">
		<div
			class="flex flex-col gap-3 mb-4 sm:flex-row sm:items-start sm:justify-between"
		>
			<div class="min-w-0">
				<h2 class="text-base font-semibold text-ink-gray-9">
					{{ title || __('Certified users') }}
				</h2>
				<p v-if="!compact" class="text-xs text-ink-gray-6 mt-1">
					{{
						__(
							'Everyone who has received an LMS certificate, with course and issue date.'
						)
					}}
				</p>
			</div>
			<div v-if="!compact" class="flex shrink-0 items-center gap-2 w-full sm:w-auto">
				<FormControl
					v-model="search"
					type="text"
					:placeholder="__('Search name, email, or course')"
					class="w-full sm:w-64"
					@update:modelValue="onSearchInput"
				/>
			</div>
		</div>

		<div
			v-if="certificates.loading && !certificates.data"
			class="py-10 text-center text-sm text-ink-gray-6"
		>
			{{ __('Loading certificates…') }}
		</div>
		<div
			v-else-if="certificates.error"
			class="py-10 text-center text-sm text-ink-red-4"
		>
			{{
				certificates.error?.messages?.[0] ||
				__('Failed to load certificates.')
			}}
		</div>
		<div v-else-if="!rows.length" class="py-10 text-center text-sm text-ink-gray-6">
			{{ __('No certificates issued yet.') }}
		</div>
		<div v-else class="overflow-x-auto">
			<table class="w-full text-sm min-w-[640px]">
				<thead>
					<tr class="border-b text-left text-ink-gray-6">
						<th class="py-2 pr-4 font-medium">{{ __('Learner') }}</th>
						<th class="py-2 pr-4 font-medium">{{ __('Email') }}</th>
						<th class="py-2 pr-4 font-medium">{{ __('Course / program') }}</th>
						<th class="py-2 pr-4 font-medium whitespace-nowrap">
							{{ __('Issued') }}
						</th>
						<th v-if="!compact" class="py-2 font-medium text-right">
							{{ __('Certificate') }}
						</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows"
						:key="row.name"
						class="border-b last:border-0 hover:bg-surface-gray-1"
					>
						<td class="py-2.5 pr-4 font-medium text-ink-gray-9 whitespace-nowrap">
							{{ row.member_name || row.full_name || row.member }}
						</td>
						<td class="py-2.5 pr-4 text-ink-gray-7">
							{{ row.email || '—' }}
						</td>
						<td class="py-2.5 pr-4 text-ink-gray-7 max-w-[16rem] truncate">
							{{
								row.course_title ||
								row.batch_title ||
								row.course ||
								'—'
							}}
						</td>
						<td class="py-2.5 pr-4 text-ink-gray-7 whitespace-nowrap tabular-nums">
							{{ formatIssueDate(row.issue_date) }}
						</td>
						<td v-if="!compact" class="py-2.5 text-right whitespace-nowrap">
							<Button variant="ghost" @click="openCertificate(row)">
								{{ __('View') }}
							</Button>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<div
			v-if="!compact && total > pageLength"
			class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4 pt-3 border-t"
		>
			<span class="text-xs text-ink-gray-6 tabular-nums">
				{{ __('Showing {0}–{1} of {2}').format(rangeStart, rangeEnd, total) }}
			</span>
			<div class="flex items-center gap-2">
				<Button
					variant="outline"
					:disabled="page <= 1 || certificates.loading"
					@click="goPage(page - 1)"
				>
					{{ __('Previous') }}
				</Button>
				<span class="text-xs text-ink-gray-6 px-1 tabular-nums">
					{{ __('Page {0} of {1}').format(page, totalPages) }}
				</span>
				<Button
					variant="outline"
					:disabled="page >= totalPages || certificates.loading"
					@click="goPage(page + 1)"
				>
					{{ __('Next') }}
				</Button>
			</div>
		</div>
	</section>
</template>

<script setup>
import { Button, createResource, FormControl } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { openCertificatePreview } from '@/utils/certificate'

const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	compact: {
		type: Boolean,
		default: false,
	},
	pageLength: {
		type: Number,
		default: 50,
	},
})

const search = ref('')
const page = ref(1)
let searchTimer = null

const certificates = createResource({
	url: 'lms.lms.api.get_analytics_issued_certificates',
	makeParams() {
		return {
			search: search.value.trim() || undefined,
			start: (page.value - 1) * props.pageLength,
			page_length: props.pageLength,
		}
	},
	auto: true,
})

const rows = computed(() => certificates.data?.rows ?? [])
const total = computed(() => certificates.data?.total ?? 0)
const totalPages = computed(() =>
	Math.max(1, Math.ceil(total.value / props.pageLength))
)
const rangeStart = computed(() =>
	total.value ? (page.value - 1) * props.pageLength + 1 : 0
)
const rangeEnd = computed(() =>
	Math.min(page.value * props.pageLength, total.value)
)

function reload() {
	certificates.reload()
}

function onSearchInput() {
	if (searchTimer) clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		page.value = 1
		reload()
	}, 300)
}

function goPage(next) {
	page.value = next
	reload()
}

function formatIssueDate(value) {
	if (!value) return '—'
	try {
		return new Date(value).toLocaleDateString(undefined, {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
		})
	} catch {
		return value
	}
}

function openCertificate(row) {
	openCertificatePreview(row)
}

watch(
	() => props.pageLength,
	() => {
		page.value = 1
		reload()
	}
)
</script>
