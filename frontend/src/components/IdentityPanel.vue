<template>
	<div class="idp">
		<div v-if="identity.loading && !d" class="idp-muted">{{ __('Loading…') }}</div>
		<div v-else-if="identity.error" class="idp-muted">{{ identity.error.messages?.[0] || __('Could not load account details.') }}</div>
		<template v-else-if="d">
			<!-- Login email -->
			<div class="idp-row">
				<div class="min-w-0 flex-1">
					<div class="idp-label">{{ __('Login email') }}</div>
					<div class="idp-value">{{ d.email }}</div>
				</div>
				<button v-if="d.can_edit && editing !== 'email'" class="idp-link" @click="start('email')">{{ __('Change') }}</button>
			</div>
			<div v-if="editing === 'email'" class="idp-edit">
				<input v-model.trim="value" type="email" class="idp-input" :placeholder="__('New email address')" />
				<input v-model.trim="reason" class="idp-input" :placeholder="__('Reason (e.g. moved from personal to work email)')" />
				<p class="idp-muted">{{ __('All progress, attempts and reports move to the new email. The person signs in with the new email from now on.') }}</p>
				<div class="idp-actions">
					<button class="idp-btn is-ghost" @click="editing = ''">{{ __('Cancel') }}</button>
					<button class="idp-btn" :disabled="busy || !value" @click="save">{{ busy ? __('Saving…') : __('Change email') }}</button>
				</div>
			</div>

			<!-- Employee code -->
			<div class="idp-row">
				<div class="min-w-0 flex-1">
					<div class="idp-label">{{ __('Employee code') }}</div>
					<div class="idp-value">
						{{ d.employee_code || '—' }}
						<span v-if="d.is_temp_code" class="idp-tag">{{ __('placeholder') }}</span>
					</div>
				</div>
				<button v-if="d.can_edit && editing !== 'code'" class="idp-link" @click="start('code')">{{ d.is_temp_code ? __('Set real code') : __('Change') }}</button>
			</div>
			<div v-if="editing === 'code'" class="idp-edit">
				<input v-model.trim="value" class="idp-input" :placeholder="__('Employee code')" />
				<input v-model.trim="reason" class="idp-input" :placeholder="__('Reason (optional)')" />
				<div class="idp-actions">
					<button class="idp-btn is-ghost" @click="editing = ''">{{ __('Cancel') }}</button>
					<button class="idp-btn" :disabled="busy || !value" @click="save">{{ busy ? __('Saving…') : __('Save code') }}</button>
				</div>
			</div>
			<p v-if="error" class="idp-error">{{ error }}</p>

			<!-- History -->
			<div class="idp-label mt-4">{{ __('Change history') }}</div>
			<p v-if="!d.history.length" class="idp-muted">{{ __('No changes yet.') }}</p>
			<ol v-else class="idp-history">
				<li v-for="(h, i) in d.history" :key="i">
					<span class="idp-dot" />
					<div class="min-w-0">
						<div class="idp-change">
							<b>{{ h.field }}</b>: <span class="idp-old">{{ h.old_value || '—' }}</span> → <span>{{ h.new_value }}</span>
						</div>
						<div class="idp-muted">
							{{ formatDate(h.changed_on) }} · {{ __('by') }} {{ h.changed_by_name }}<template v-if="h.reason"> · {{ h.reason }}</template>
						</div>
					</div>
				</li>
			</ol>
		</template>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { call, createResource } from 'frappe-ui'

// Login email + employee code for one person, with their audit trail. Learners see their own;
// admins/managers see (and admins edit) the people they manage.
const props = defineProps({ user: { type: String, required: true } })
const emit = defineEmits(['changed'])

const identity = createResource({
	url: 'lms.lms.identity.get_identity',
	makeParams: () => ({ user: props.user }),
	auto: true,
})
watch(
	() => props.user,
	() => identity.reload()
)
const d = computed(() => identity.data)

const editing = ref('')
const value = ref('')
const reason = ref('')
const busy = ref(false)
const error = ref('')

function start(kind) {
	editing.value = kind
	value.value = kind === 'code' && !d.value.is_temp_code ? d.value.employee_code || '' : ''
	reason.value = ''
	error.value = ''
}

async function save() {
	busy.value = true
	error.value = ''
	try {
		const result =
			editing.value === 'email'
				? await call('lms.lms.identity.change_email', { user: d.value.user, new_email: value.value, reason: reason.value })
				: await call('lms.lms.identity.set_employee_code', { user: d.value.user, employee_code: value.value, reason: reason.value })
		identity.setData(result)
		editing.value = ''
		emit('changed', result)
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || __('Could not save.')
	} finally {
		busy.value = false
	}
}

const formatDate = (v) =>
	v ? new Date(String(v).replace(' ', 'T')).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : ''
</script>

<style scoped>
.idp-row {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 10px 0;
	border-bottom: 1px solid #f2f2f2;
}
.idp-label {
	font-size: 12px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: #52565c;
}
.idp-value {
	margin-top: 2px;
	font-size: 14px;
	font-weight: 500;
	color: #080e14;
	word-break: break-all;
}
.idp-tag {
	margin-left: 6px;
	padding: 1px 8px;
	border-radius: 999px;
	font-size: 11px;
	font-weight: 600;
	background: #ffeecc;
	color: #8a5a00;
}
.idp-link {
	font-size: 13px;
	font-weight: 600;
	color: #0062cc;
	flex: none;
}
.idp-edit {
	display: grid;
	gap: 8px;
	padding: 12px;
	margin: 6px 0;
	border-radius: 14px;
	background: #f4f9ff;
	border: 1px solid #cfe5ff;
}
.idp-input {
	height: 38px;
	padding: 0 12px;
	border-radius: 10px;
	border: 1px solid #e6e7e8;
	background: #fff;
	font-size: 14px;
}
.idp-actions {
	display: flex;
	justify-content: flex-end;
	gap: 8px;
}
.idp-btn {
	height: 36px;
	padding: 0 18px;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	color: #fff;
	background: #027bff;
}
.idp-btn.is-ghost {
	background: #fff;
	color: #52565c;
	border: 1px solid #e6e7e8;
}
.idp-btn:disabled {
	opacity: 0.5;
}
.idp-muted {
	font-size: 12px;
	color: #52565c;
}
.idp-error {
	font-size: 13px;
	color: #b42323;
}
.idp-history {
	margin-top: 8px;
	display: grid;
	gap: 10px;
}
.idp-history li {
	display: flex;
	gap: 10px;
}
.idp-dot {
	margin-top: 6px;
	width: 8px;
	height: 8px;
	flex: none;
	border-radius: 999px;
	background: #027bff;
}
.idp-change {
	font-size: 13px;
	color: #080e14;
	word-break: break-all;
}
.idp-old {
	color: #85878a;
	text-decoration: line-through;
}
</style>
