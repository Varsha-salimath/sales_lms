<template>
	<div class="il-page min-h-full pb-12">
		<nav class="flex items-center gap-1.5 pt-5 text-sm">
			<span class="text-[color:var(--il-primary-40)]">{{ __('Reports') }}</span>
			<span class="text-[color:var(--il-neutral-60)]">/</span>
			<span class="font-medium text-[color:var(--il-primary-20)]">{{ __('Sales CRT') }}</span>
		</nav>

		<!-- Header card (PTM board: name strip + meta row) -->
		<section class="cr-head mt-3">
			<div class="cr-head-strip">
				<div>
					<h1 class="text-xl font-semibold text-[color:var(--il-ink)]">{{ __('Sales CRT · Combined report') }}</h1>
					<p class="mt-0.5 text-xs text-[color:var(--il-muted)]">{{ __('For training managers and above') }}</p>
				</div>
				<div class="flex items-center gap-3">
					<span v-if="report.data?.last_updated" class="hidden text-xs text-[color:var(--il-muted)] sm:inline">
						{{ __('Last updated') }}: {{ fmtDate(report.data.last_updated) }}
					</span>
					<button class="il-btn il-btn-primary" :disabled="!rows.length" @click="exportCsv">
						<Download class="h-4 w-4" />
						{{ __('Export') }}
					</button>
				</div>
			</div>
			<div class="cr-filters">
				<label class="cr-select">
					<span>{{ __('Training manager') }}</span>
					<select v-model="filters.training_manager">
						<option value="__all__">{{ __('All managers') }}</option>
						<option v-for="m in options.training_manager" :key="m" :value="m">{{ managerName(m) }}</option>
					</select>
				</label>
				<label class="cr-select">
					<span>{{ __('Batch code') }}</span>
					<select v-model="filters.batch_code">
						<option value="__all__">{{ __('All batch codes') }}</option>
						<option v-for="code in options.batch_code" :key="code" :value="code">{{ code }}</option>
					</select>
				</label>
				<label class="cr-select">
					<span>{{ __('Location') }}</span>
					<select v-model="filters.location">
						<option value="__all__">{{ __('All locations') }}</option>
						<option v-for="l in options.location" :key="l" :value="l">{{ l }}</option>
					</select>
				</label>
				<label class="cr-search">
					<Search class="h-4 w-4 text-[color:var(--il-neutral-60)]" />
					<input v-model="search" :placeholder="__('Search learner or email')" />
				</label>
			</div>
		</section>

		<div v-if="report.loading && !report.data" class="mt-6 space-y-4">
			<div class="h-40 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div class="h-64 animate-pulse rounded-3xl bg-[#e6e7e8]" />
		</div>

		<div v-else-if="report.error" class="il-card mt-6 p-8 text-center text-sm text-[color:var(--il-error-50)]">
			{{ report.error.messages?.[0] || __('Could not load the report.') }}
		</div>

		<div
			v-if="report.data || tab === 'batches' || batchWise.data"
			class="cr-tabs mt-6"
		>
			<button v-for="t in tabs" :key="t.key" :class="{ 'is-active': tab === t.key }" @click="tab = t.key">
				{{ t.label }}
			</button>
		</div>

		<section v-if="tab === 'batches'" class="mt-6 space-y-4">
			<div v-if="batchWise.loading && !batchWise.data" class="h-40 animate-pulse rounded-3xl bg-[#e6e7e8]" />
			<div v-else-if="batchWise.error" class="il-card p-8 text-center text-sm text-[color:var(--il-error-50)]">
				{{ batchWise.error.messages?.[0] || __('Could not load learners by batch.') }}
			</div>
			<template v-else-if="batchWise.data">
				<p class="text-sm text-[color:var(--il-muted)]">
					{{ __('Your assigned learners grouped by batch.') }}
					<span class="font-medium text-[color:var(--il-ink)]">
						{{ batchWise.data.total_learners }} {{ __('learners') }}
					</span>
					{{ __('across') }}
					<span class="font-medium">{{ batchWise.data.batches?.length || 0 }}</span>
					{{ __('batches') }}.
				</p>
				<div v-if="!batchWise.data.batches?.length" class="il-card p-10 text-center text-sm text-[color:var(--il-muted)]">
					{{ __('No batch enrollments found for your learners yet.') }}
				</div>
				<div v-for="group in batchWise.data.batches" :key="group.batch" class="cr-batch-group">
					<button
						type="button"
						class="cr-batch-head"
						@click="toggleBatch(group.batch)"
					>
						<div class="min-w-0 text-left">
							<div class="font-semibold text-[color:var(--il-ink)] truncate">{{ group.title }}</div>
							<div class="text-xs text-[color:var(--il-muted)] mt-0.5">
								<span v-if="group.start_date">{{ fmtDate(group.start_date) }}</span>
								<span v-if="group.end_date"> – {{ fmtDate(group.end_date) }}</span>
								· {{ group.learner_count }} {{ __('learners') }}
							</div>
						</div>
						<router-link
							class="il-btn il-btn-outline shrink-0 text-xs"
							:to="`/batches/${group.batch}#dashboard`"
							@click.stop
						>
							{{ __('Batch dashboard') }}
						</router-link>
					</button>
					<div v-show="expandedBatches.has(group.batch)" class="cr-batch-body">
						<table class="cr-mini cr-mini-lg w-full">
							<thead>
								<tr>
									<th>{{ __('Learner') }}</th>
									<th>{{ __('Email') }}</th>
									<th>{{ __('Enrolled') }}</th>
									<th class="text-center">{{ __('Readiness') }}</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="learner in group.learners" :key="learner.enrollment">
									<td class="font-medium">{{ learner.member_name || learner.email }}</td>
									<td class="text-[color:var(--il-muted)] text-sm">{{ learner.email }}</td>
									<td class="text-sm whitespace-nowrap">{{ fmtDate(learner.enrolled_on) }}</td>
									<td class="text-center">
										<span
											v-if="learner.readiness != null"
											class="rp-cell rp-cell-strong"
											:style="cellStyle(learner.readiness_band)"
										>
											{{ fmtPct(learner.readiness) }}
										</span>
										<span v-else class="text-[color:var(--il-muted)]">—</span>
									</td>
									<td class="text-right">
										<button
											v-if="learner.report_name"
											type="button"
											class="text-xs font-medium text-[color:var(--il-primary-40)]"
											@click="openReport(learner.report_name)"
										>
											{{ __('Report card') }}
										</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</template>
		</section>

		<template v-else-if="report.data">
			<!-- Highlights -->
			<h2 class="cr-h2">{{ __('Highlights') }}</h2>
			<section class="cr-card cr-highlights">
				<div class="flex items-center gap-4">
					<div class="cr-donut" :style="{ '--p': stats.readiness?.avg || 0, '--c': bandStyle(bandOfPct(stats.readiness?.avg)).dot }">
						<span>{{ fmtPct(stats.readiness?.avg) }}</span>
					</div>
					<div>
						<div class="text-lg leading-6 text-[color:var(--il-ink)]">{{ __('Average') }}<br />{{ __('readiness') }}</div>
						<div class="mt-1 text-xs text-[color:var(--il-muted)]">{{ rows.length }} {{ __('learners') }}</div>
					</div>
				</div>
				<InsightsCard :title="__('Insights')" :items="batchInsights" :chip="readyChip.label" :chip-tone="readyChip.tone" />
			</section>

			<!-- Overview -->
			<div v-if="tab === 'overview'" class="space-y-6">
				<ReportSection :title="__('Readiness proficiency')">
					<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						<button
							v-for="(b, i) in report.data.bands"
							:key="b.key"
							type="button"
							class="cr-band"
							:style="{ background: i === 0 ? bandStyle(b.key).bg : bandStyle(b.key).soft, borderColor: bandStyle(b.key).rowBorder }"
							@click="openBand(b.key)"
						>
							<div>
								<div class="text-sm text-[color:var(--il-ink)]">{{ b.label }}</div>
								<div class="mt-0.5 text-sm">
									<strong :style="{ color: bandStyle(b.key).text }">{{ b.count }}</strong>
									<span class="ms-1 text-[color:var(--il-muted)]">{{ __('learners') }}</span>
								</div>
							</div>
							<div class="text-sm font-semibold" :style="{ color: bandStyle(b.key).text }">{{ share(b.count) }}%</div>
						</button>
					</div>
					<div class="cr-legend">
						<span v-for="l in legend" :key="l.key" class="inline-flex items-center gap-1.5">
							<span class="h-2.5 w-2.5 rounded-full" :style="{ background: bandStyle(l.key).dot }" />
							{{ l.text }}
						</span>
					</div>
				</ReportSection>

				<ReportSection :title="__('Input summary')" :action="__('View learners')" @action="tab = 'learners'">
					<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						<div v-for="c in inputCards" :key="c.key" class="cr-input" :style="{ background: bandStyle(c.band).soft, borderColor: bandStyle(c.band).rowBorder }">
							<div class="px-3.5 pt-3">
								<div class="text-[15px] text-[color:var(--il-ink)]">{{ c.label }}</div>
								<div class="mt-1 flex items-baseline gap-2">
									<span class="text-xl font-semibold" :style="{ color: bandStyle(c.band).text }">{{ fmtPct(c.pct) }}</span>
									<span class="border-s border-[color:var(--il-neutral-80)] ps-2 text-xs text-[color:var(--il-muted)]">
										{{ fmt(c.avg) }} {{ __('of') }} {{ c.max }} {{ __('avg') }}
									</span>
								</div>
							</div>
							<div class="cr-input-foot">
								{{ c.count }}/{{ rows.length }} {{ __('scored') }} · {{ __('range') }} {{ fmt(c.min) }}–{{ fmt(c.max_seen) }}
							</div>
						</div>
					</div>
				</ReportSection>

				<ReportSection :title="__('Learners by score')" :subtitle="__('Product tests against call skill (AI mock and audit). Click a dot to open that report card.')">
					<QuadrantChart
						:points="quadrantPoints"
						:threshold="75"
						:x-label="__('Product tests %')"
						:y-label="__('Call skill %')"
						:legend-title="__('Readiness based on score (75% cut-off)')"
						:labels="quadrantLabels"
						@select="(p) => openCard({ name: p.id })"
					/>
				</ReportSection>
			</div>

			<!-- Test performance -->
			<div v-if="tab === 'tests'" class="space-y-6">
				<ReportSection :title="__('Test performance')" :subtitle="__('Five CRT product tests, each out of 20.')">
					<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
						<div v-for="s in testStats" :key="s.label" class="cr-stat">
							<div class="text-xl font-semibold text-[color:var(--il-ink)]">
								{{ s.value }}<small v-if="s.of" class="font-normal text-[color:var(--il-muted)]"> / {{ s.of }}</small>
							</div>
							<div class="mt-0.5 text-sm text-[color:var(--il-muted)]">{{ s.label }}</div>
						</div>
					</div>
					<ScoreTrend
						class="mt-5"
						:title="__('Score trend')"
						:items="testTrend"
						:modes="[
							{ key: 'avg', label: __('Batch average') },
							{ key: 'top', label: __('vs Topper') },
							{ key: 'low', label: __('vs Lowest') },
						]"
						:value-label="__('Batch average')"
						:best-label="__('Strongest test')"
					/>
				</ReportSection>

				<ReportSection :title="__('Test-wise performance')" :subtitle="__('Bands are % of the 20-mark maximum. Open a test to see every learner.')">
					<div class="space-y-4">
						<BandAccordion
							v-for="(t, i) in testBreakdown"
							:key="t.key"
							:title="t.label"
							:band="t.band"
							:main-label="__('Average')"
							:main-value="t.avg == null ? '—' : `${fmt(t.avg)} / 20`"
							:main-sub="t.avg == null ? __('Not taken yet') : `${fmtPct(t.pct)} · ${t.scored} ${__('scored')}`"
							:distribution="t.distribution"
							:default-open="i === weakestIndex"
						>
							<InsightsCard :title="__('Insights')" :items="t.insights" class="mb-4" />
							<div class="cr-mini-wrap">
								<table class="cr-mini">
									<thead>
										<tr>
											<th>{{ __('Learner') }}</th>
											<th class="text-center">{{ __('Score') }}</th>
											<th class="text-center">{{ __('vs avg') }}</th>
											<th class="text-center">{{ __('Attendance') }}</th>
											<th>{{ __('Training manager') }}</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="r in t.learners" :key="r.name" @click="openCard(r)">
											<td>
												<span class="cr-name" :style="{ background: bandStyle(r.scores[t.key]?.band).bg }">
													<span>{{ r.employee_name }}</span>
													<span>{{ fmtPct(r.scores[t.key]?.pct) }}</span>
												</span>
											</td>
											<td class="text-center tabular-nums">{{ fmt(r[t.key]) }}/20</td>
											<td class="text-center tabular-nums" :class="r[t.key] >= t.avg ? 'text-[#04742D]' : 'text-[#D12B2B]'">
												<span class="cr-dot" :style="{ background: r[t.key] >= t.avg ? '#35C759' : '#F03E3E' }" />
												{{ signed(r[t.key] - t.avg) }}
											</td>
											<td class="text-center tabular-nums">{{ fmt(r.attendance_days) }}/15</td>
											<td class="whitespace-nowrap">{{ managerName(r.training_manager) }}</td>
										</tr>
										<tr v-if="!t.learners.length">
											<td colspan="5" class="py-6 text-center text-sm text-[color:var(--il-muted)]">{{ __('No one has taken this test yet.') }}</td>
										</tr>
									</tbody>
								</table>
							</div>
						</BandAccordion>
					</div>
				</ReportSection>
			</div>

			<!-- Calling -->
			<div v-if="tab === 'calling'" class="space-y-6">
				<ReportSection :title="__('Calling performance')" :subtitle="callingSubtitle">
					<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
						<div v-for="s in callingStats" :key="s.label" class="cr-stat">
							<div class="text-xl font-semibold text-[color:var(--il-ink)]">{{ s.value }}</div>
							<div class="mt-0.5 text-sm text-[color:var(--il-muted)]">{{ s.label }}</div>
						</div>
					</div>
					<div class="mt-5 space-y-2">
						<div v-for="(s, i) in funnel" :key="s.label" class="flex items-center gap-3">
							<div class="w-36 shrink-0 text-sm text-[color:var(--il-ink)]">{{ s.label }}</div>
							<div class="relative h-9 flex-1 overflow-hidden rounded-xl bg-[#eef5ff]">
								<div class="h-full rounded-xl" :style="{ width: `${s.width}%`, background: ['#027BFF', '#3395FF', '#67B0FF', '#99CAFF'][i] }" />
								<span class="absolute inset-y-0 flex items-center text-sm font-semibold" :class="s.width > 18 ? 'left-3 text-white' : 'text-[color:var(--il-ink)]'" :style="s.width > 18 ? {} : { left: `calc(${s.width}% + 0.5rem)` }">
									{{ s.value.toLocaleString('en-IN') }}
								</span>
							</div>
							<div class="w-28 shrink-0 text-right text-xs text-[color:var(--il-muted)]">{{ s.rate == null ? '' : `${fmtPct(s.rate)} ${__('of previous')}` }}</div>
						</div>
					</div>
				</ReportSection>

				<ReportSection :title="__('By training manager')" :subtitle="__('Click a manager to filter the whole report to their learners.')" flush>
					<div class="cr-mini-wrap">
						<table class="cr-mini cr-mini-lg">
							<thead>
								<tr>
									<th>{{ __('Training manager') }}</th>
									<th class="text-center">{{ __('Learners') }}</th>
									<th class="text-center">{{ __('Avg readiness') }}</th>
									<th class="text-center">{{ __('Good or better') }}</th>
									<th class="text-center">{{ __('Connect rate') }}</th>
									<th class="text-center">{{ __('Booking rate') }}</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="m in byManager" :key="m.email" @click="filters.training_manager = m.email">
									<td>
										<div class="flex items-center gap-2.5">
											<span class="rp-avatar">{{ initials(managerName(m.email)) }}</span>
											<span class="font-medium">{{ managerName(m.email) }}</span>
										</div>
									</td>
									<td class="text-center tabular-nums">{{ m.count }}</td>
									<td class="text-center">
										<span class="rp-cell rp-cell-strong" :style="cellStyle(bandOfPct(m.readiness))">{{ fmtPct(m.readiness) }}</span>
									</td>
									<td class="text-center tabular-nums">{{ m.ready }} / {{ m.count }}</td>
									<td class="text-center tabular-nums">{{ fmtPct(m.connect) }}</td>
									<td class="text-center tabular-nums">{{ fmtPct(m.booking) }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</ReportSection>
			</div>

			<!-- Learners (OJT sheet) -->
			<section v-if="tab === 'learners'" class="cr-card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-2 bg-[#f4f9ff] px-5 py-3.5">
					<h2 class="text-lg font-normal text-[color:var(--il-ink)]">
						{{ __('Learners') }} <span class="text-[color:var(--il-muted)]">({{ visibleRows.length }})</span>
					</h2>
					<div class="flex items-center gap-3">
						<button v-if="bandFilter" class="cr-filter-chip" :style="cellStyle(bandFilter)" @click="bandFilter = null">
							{{ bandStyle(bandFilter).label }} <X class="h-3.5 w-3.5" />
						</button>
						<span class="text-xs text-[color:var(--il-muted)]">{{ __('Click a learner to open their report card') }}</span>
					</div>
				</div>
				<div class="rp-table-wrap">
					<table class="rp-table">
						<thead>
							<tr class="rp-group-row">
								<th colspan="3" class="rp-sticky">{{ __('Employee') }}</th>
								<th colspan="3">{{ __('Intent & Skill') }}</th>
								<th colspan="6">{{ __('Calling') }}</th>
								<th colspan="5">{{ __('Tests (out of 20)') }}</th>
								<th>{{ __('Voice viva') }}</th>
								<th>{{ __('Overall') }}</th>
							</tr>
							<tr>
								<th v-for="col in columns" :key="col.key" :class="[col.sticky ? 'rp-sticky' : '', col.align || '']" @click="sortBy(col.key)">
									<span class="inline-flex items-center gap-1">
										{{ col.label }}
										<ArrowUpDown v-if="sort.key !== col.key" class="h-3 w-3 opacity-30" />
										<ArrowUp v-else-if="sort.dir === 'asc'" class="h-3 w-3" />
										<ArrowDown v-else class="h-3 w-3" />
									</span>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in visibleRows" :key="row.name" @click="openCard(row)">
								<td class="rp-sticky">
									<div class="flex items-center gap-2.5">
										<span class="rp-avatar">{{ initials(row.employee_name) }}</span>
										<div class="min-w-0">
											<div class="truncate font-medium text-[color:var(--il-ink)]">{{ row.employee_name }}</div>
											<div class="truncate text-xs text-[color:var(--il-muted)]">{{ row.email }}</div>
										</div>
									</div>
								</td>
								<td>{{ row.location || '—' }}</td>
								<td class="whitespace-nowrap">{{ managerName(row.training_manager) }}</td>
								<td v-for="k in ['attendance_days', 'ai_mock_score', 'audit_score']" :key="k" class="text-center">
									<span class="rp-cell" :style="cellStyle(row.scores[k]?.band)">{{ fmt(row[k]) }}</span>
								</td>
								<td class="text-center tabular-nums">{{ fmt(row.dc) }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.cc) }}</td>
								<td class="text-center tabular-nums">{{ row.talk_time || '—' }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.booked) }}</td>
								<td class="text-center tabular-nums">{{ fmt(row.catered) }}</td>
								<td class="text-center tabular-nums">{{ fmtPct(row.booking_rate) }}</td>
								<td v-for="k in TEST_KEYS" :key="k" class="text-center">
									<span class="rp-cell" :style="cellStyle(row.scores[k]?.band)">{{ fmt(row[k]) }}</span>
								</td>
								<td class="text-center" :title="row.viva_passed_days ? `${row.viva_passed_days} ${__('days passed')}` : ''">
									<span class="rp-cell" :style="cellStyle(bandOfPct(row.viva_avg))">{{ row.viva_avg == null ? '—' : fmtPct(row.viva_avg) }}</span>
								</td>
								<td class="text-center">
									<span class="rp-cell rp-cell-strong" :style="cellStyle(row.readiness_band)">{{ fmtPct(row.readiness) }}</span>
								</td>
							</tr>
							<tr v-if="!visibleRows.length">
								<td :colspan="columns.length" class="py-10 text-center text-sm text-[color:var(--il-muted)]">
									{{ __('No learners match these filters.') }}
								</td>
							</tr>
						</tbody>
						<tfoot v-if="visibleRows.length">
							<tr>
								<td class="rp-sticky font-medium">{{ __('Batch average') }}</td>
								<td></td>
								<td></td>
								<td v-for="k in ['attendance_days', 'ai_mock_score', 'audit_score', 'dc', 'cc']" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center">{{ fmtDuration(stats.talk_seconds?.avg) }}</td>
								<td v-for="k in ['booked', 'catered']" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center">{{ fmtPct(stats.booking_rate?.avg) }}</td>
								<td v-for="k in TEST_KEYS" :key="k" class="text-center tabular-nums">{{ fmt(stats[k]?.avg) }}</td>
								<td class="text-center tabular-nums">{{ vivaAvg == null ? '—' : fmtPct(vivaAvg) }}</td>
								<td class="text-center font-medium">{{ fmtPct(stats.readiness?.avg) }}</td>
							</tr>
						</tfoot>
					</table>
				</div>
			</section>

			<p class="mt-4 text-xs text-[color:var(--il-muted)]">{{ BAND_RULES }} {{ __("(of each metric's maximum)") }}</p>
		</template>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search, X } from 'lucide-vue-next'
import ReportSection from './ReportSection.vue'
import InsightsCard from './InsightsCard.vue'
import QuadrantChart from './QuadrantChart.vue'
import ScoreTrend from './ScoreTrend.vue'
import BandAccordion from './BandAccordion.vue'
import {
	BAND_ORDER,
	BAND_RULES,
	avg,
	bandOfPct,
	bandStyle,
	fmt,
	fmtDate,
	fmtDuration,
	fmtPct,
	initials,
	managerName,
	median,
} from './reportUtils'

const TEST_KEYS = ['target_exam', 'cbse', 'test_prep', 'lsq', 'math_champ']

const router = useRouter()
const route = useRoute()
const user = inject('$user')
const filters = reactive({
	batch_code: '__all__',
	location: '__all__',
	training_manager: '__all__',
})
const search = ref('')
const bandFilter = ref(null)
const sort = reactive({ key: 'readiness', dir: 'desc' })
const tab = ref(route.query.tab === 'batches' ? 'batches' : 'overview')
const expandedBatches = ref(new Set())

const tabs = [
	{ key: 'batches', label: __('By batch') },
	{ key: 'overview', label: __('Overview') },
	{ key: 'tests', label: __('Test performance') },
	{ key: 'calling', label: __('Calling') },
	{ key: 'learners', label: __('Learners') },
]

const isTmPrimaryView = computed(() => {
	const u = user?.data
	if (!u?.is_training_manager) return false
	return !u.is_moderator && !u.is_instructor && !u.is_evaluator && !u.is_system_manager
})

const batchWise = createResource({
	url: 'lms.lms.training_manager_dashboard.get_learners_by_batch',
	auto: true,
	onSuccess(data) {
		const ids = (data?.batches || []).map((b) => b.batch)
		expandedBatches.value = new Set(ids.slice(0, 3))
	},
})

function toggleBatch(batchId) {
	const next = new Set(expandedBatches.value)
	if (next.has(batchId)) next.delete(batchId)
	else next.add(batchId)
	expandedBatches.value = next
}

function openReport(name) {
	router.push({ name: 'LearnerReportCard', params: { name } })
}

watch(tab, (key) => {
	const q = { ...route.query }
	if (key === 'batches') q.tab = 'batches'
	else delete q.tab
	router.replace({ query: q })
})

onMounted(() => {
	if (isTmPrimaryView.value && !route.query.tab) {
		tab.value = 'batches'
	}
})

const tmFilterInitialized = ref(false)
const skipReportReload = ref(false)

const report = createResource({
	url: 'lms.lms.learner_report.get_combined_report',
	makeParams: () => ({ ...filters }),
	auto: true,
	onSuccess(data) {
		if (tmFilterInitialized.value || !data?.default_training_manager) {
			return
		}
		tmFilterInitialized.value = true
		skipReportReload.value = true
		filters.training_manager = data.default_training_manager
		skipReportReload.value = false
		report.reload()
	},
})
watch(
	() => filters.training_manager,
	() => {
		filters.batch_code = '__all__'
	}
)
watch(filters, () => {
	if (skipReportReload.value) {
		return
	}
	report.reload()
})

const options = computed(
	() => report.data?.options || { batch_code: [], location: [], training_manager: [] }
)
const stats = computed(() => report.data?.stats || {})
const rows = computed(() => {
	const term = search.value.trim().toLowerCase()
	const all = report.data?.rows || []
	return term ? all.filter((r) => `${r.employee_name} ${r.email}`.toLowerCase().includes(term)) : all
})
const metricLabel = (key) => report.data?.metrics?.find((m) => m.key === key)?.label || key

const share = (n) => (rows.value.length ? Math.round((n / rows.value.length) * 100) : 0)
const signed = (v) => (v == null || Number.isNaN(v) ? '—' : `${v > 0 ? '+' : ''}${fmt(Math.round(v * 10) / 10)}`)

// ---- Highlights ---------------------------------------------------------------------------

const readyCount = computed(() => rows.value.filter((r) => ['excellent', 'good'].includes(r.readiness_band)).length)
const readyChip = computed(() => {
	if (!rows.value.length) return { label: '', tone: 'good' }
	const s = share(readyCount.value)
	return {
		label: `${readyCount.value} ${__('of')} ${rows.value.length} ${__('ready')}`,
		tone: s >= 60 ? 'good' : s >= 30 ? 'warn' : 'bad',
	}
})
const batchInsights = computed(() =>
	(report.data?.insights || []).map((line) => {
		const i = line.indexOf(':')
		return i > 0 && i < 40 ? { lead: line.slice(0, i + 1), text: line.slice(i + 1) } : line
	})
)

// ---- Overview -----------------------------------------------------------------------------

const legend = [
	{ key: 'excellent', text: '≥ 90% (Excellent)' },
	{ key: 'good', text: '80% – <90% (Good)' },
	{ key: 'average', text: '60% – <80% (Average)' },
	{ key: 'needs_improvement', text: '<60% (Needs Improvement)' },
	{ key: null, text: __('(Not scored)') },
]

const inputCards = computed(() =>
	[
		{ key: 'attendance_days', label: __('Attendance'), max: 15 },
		{ key: 'ai_mock_score', label: __('AI mock'), max: 20 },
		{ key: 'audit_score', label: __('Audit'), max: 20 },
		{ key: 'product_avg', label: __('Product tests'), max: 20 },
	].map((c) => {
		const s = stats.value[c.key] || {}
		const pct = s.avg == null ? null : Math.round((s.avg / c.max) * 1000) / 10
		return { ...c, avg: s.avg, pct, band: bandOfPct(pct), count: s.count || 0, min: s.min, max_seen: s.max }
	})
)

const pctOf = (v, max) => (v == null ? null : Math.min(100, (v / max) * 100))
const quadrantPoints = computed(() =>
	rows.value.map((r) => {
		const skill = avg([pctOf(r.ai_mock_score, 20), pctOf(r.audit_score, 20)])
		const product = pctOf(r.product_avg, 20)
		return {
			id: r.name,
			label: r.employee_name,
			x: product,
			y: skill,
			rows: [
				{ label: __('Product tests'), value: fmtPct(product == null ? null : Math.round(product)), color: '#0F6B2E' },
				{ label: __('Call skill'), value: fmtPct(skill == null ? null : Math.round(skill)), color: '#6D4AFF' },
				{ label: __('Readiness'), value: fmtPct(r.readiness) },
			],
		}
	})
)
const quadrantLabels = [
	{ title: __('High skill · High score'), hint: __('Certification ready. Keep them on live calls.') },
	{ title: __('High skill · Low score'), hint: __('Good on calls. Revise product knowledge.') },
	{ title: __('Low skill · High score'), hint: __('Knows the product. Needs more mock calls.') },
	{ title: __('Low skill · Low score'), hint: __('Needs coaching on both. Start here.') },
]

function openBand(key) {
	bandFilter.value = key
	tab.value = 'learners'
}

// ---- Tests --------------------------------------------------------------------------------

function distribution(scores) {
	const list = scores.filter(Boolean)
	return BAND_ORDER.map((key) => {
		const count = list.filter((b) => b === key).length
		return { key, label: bandStyle(key).label, count, pct: list.length ? Math.round((count / list.length) * 100) : 0 }
	})
}

const testBreakdown = computed(() =>
	TEST_KEYS.map((key) => {
		const scored = rows.value.filter((r) => r[key] != null && r[key] !== '')
		const a = avg(scored.map((r) => r[key]))
		const pct = a == null ? null : Math.round((a / 20) * 1000) / 10
		const label = metricLabel(key)
		const lows = scored.filter((r) => r.scores[key]?.band === 'needs_improvement')
		const tops = scored.filter((r) => r.scores[key]?.band === 'excellent')
		const insights = []
		if (!scored.length) insights.push(__('This test has not been taken by anyone in this view yet.'))
		else {
			if (tops.length) insights.push({ lead: `${tops.length} ${__('learners scored 18+.')}`, text: tops.slice(0, 3).map((r) => r.employee_name).join(', ') + (tops.length > 3 ? ' …' : '') })
			if (lows.length) insights.push({ lead: `${lows.length} ${__('learners are below 12/20.')}`, text: `${__('Plan a refresher on')} ${label} ${__('for them.')}` })
			const missing = rows.value.length - scored.length
			if (missing) insights.push({ lead: `${missing} ${__('not taken yet.')}`, text: __('They will show here once scored.') })
		}
		return {
			key,
			label,
			avg: a,
			pct,
			band: bandOfPct(pct),
			scored: scored.length,
			top: scored.length ? (Math.max(...scored.map((r) => r[key])) / 20) * 100 : null,
			low: scored.length ? (Math.min(...scored.map((r) => r[key])) / 20) * 100 : null,
			distribution: distribution(scored.map((r) => r.scores[key]?.band)),
			learners: [...scored].sort((x, y) => y[key] - x[key]),
			insights,
		}
	})
)

const weakestIndex = computed(() => {
	let w = -1
	testBreakdown.value.forEach((t, i) => {
		if (t.avg != null && (w < 0 || t.avg < testBreakdown.value[w].avg)) w = i
	})
	return w
})

const testTrend = computed(() =>
	testBreakdown.value.map((t) => ({
		label: t.label,
		value: t.pct,
		display: t.avg == null ? __('Not taken') : `${fmt(t.avg)}/20 (${fmtPct(t.pct)})`,
		compare: { top: t.top, low: t.low },
		extra: [{ label: __('Scored'), value: `${t.scored}/${rows.value.length}` }],
	}))
)

const testStats = computed(() => {
	const taken = testBreakdown.value.filter((t) => t.scored)
	const all = rows.value.flatMap((r) => TEST_KEYS.map((k) => r.scores[k]?.pct).filter((v) => v != null))
	return [
		{ label: __('Tests taken'), value: String(taken.length).padStart(2, '0'), of: TEST_KEYS.length },
		{ label: __('Learners scored'), value: rows.value.filter((r) => r.product_avg != null).length, of: rows.value.length },
		{ label: __('Highest score'), value: all.length ? `${Math.round(Math.max(...all))}%` : '—' },
		{ label: __('Median score'), value: all.length ? `${Math.round(median(all))}%` : '—' },
	]
})

// ---- Calling ------------------------------------------------------------------------------

const sum = (key) => rows.value.reduce((t, r) => t + (Number(r[key]) || 0), 0)
const calling = computed(() => ({ dc: sum('dc'), cc: sum('cc'), booked: sum('booked'), catered: sum('catered') }))
const callers = computed(() => rows.value.filter((r) => r.dc != null && r.dc !== '').length)
const callingSubtitle = computed(() =>
	callers.value < rows.value.length
		? `${callers.value} ${__('of')} ${rows.value.length} ${__('learners are on live calls; the rest are still in CRT.')}`
		: __('Totals for everyone in this view.')
)
const rate = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : null)
const callingStats = computed(() => [
	{ label: __('Dialled (DC)'), value: calling.value.dc.toLocaleString('en-IN') },
	{ label: __('Connect rate'), value: fmtPct(rate(calling.value.cc, calling.value.dc)) },
	{ label: __('Booking rate'), value: fmtPct(rate(calling.value.booked, calling.value.cc)) },
	{ label: __('Avg talk time'), value: fmtDuration(stats.value.talk_seconds?.avg) },
])
const funnel = computed(() => {
	const c = calling.value
	const top = Math.max(c.dc, 1)
	return [
		{ label: __('Dialled (DC)'), value: c.dc, rate: null },
		{ label: __('Connected (CC)'), value: c.cc, rate: rate(c.cc, c.dc) },
		{ label: __('Booked'), value: c.booked, rate: rate(c.booked, c.cc) },
		{ label: __('Catered'), value: c.catered, rate: rate(c.catered, c.booked) },
	].map((s) => ({ ...s, width: Math.max(3, (s.value / top) * 100) }))
})

const byManager = computed(() => {
	const groups = {}
	rows.value.forEach((r) => (groups[r.training_manager || '—'] ||= []).push(r))
	return Object.entries(groups)
		.map(([email, list]) => {
			const t = (k) => list.reduce((s, r) => s + (Number(r[k]) || 0), 0)
			return {
				email,
				count: list.length,
				readiness: avg(list.map((r) => r.readiness)),
				ready: list.filter((r) => ['excellent', 'good'].includes(r.readiness_band)).length,
				connect: rate(t('cc'), t('dc')),
				booking: rate(t('booked'), t('cc')),
			}
		})
		.sort((a, b) => (b.readiness ?? -1) - (a.readiness ?? -1))
})

// ---- Learners table -----------------------------------------------------------------------

const columns = [
	{ key: 'employee_name', label: __('Name'), sticky: true },
	{ key: 'location', label: __('Location') },
	{ key: 'training_manager', label: __('Training manager') },
	{ key: 'attendance_days', label: __('Attendance'), align: 'text-center' },
	{ key: 'ai_mock_score', label: __('AI mock'), align: 'text-center' },
	{ key: 'audit_score', label: __('Audit'), align: 'text-center' },
	{ key: 'dc', label: 'DC', align: 'text-center' },
	{ key: 'cc', label: 'CC', align: 'text-center' },
	{ key: 'talk_seconds', label: __('Talk time'), align: 'text-center' },
	{ key: 'booked', label: __('Booked'), align: 'text-center' },
	{ key: 'catered', label: __('Catered'), align: 'text-center' },
	{ key: 'booking_rate', label: __('Book %'), align: 'text-center' },
	{ key: 'target_exam', label: __('Target exam'), align: 'text-center' },
	{ key: 'cbse', label: 'CBSE', align: 'text-center' },
	{ key: 'test_prep', label: __('Test prep'), align: 'text-center' },
	{ key: 'lsq', label: 'LSQ', align: 'text-center' },
	{ key: 'math_champ', label: __('Math champ'), align: 'text-center' },
	{ key: 'viva_avg', label: __('Avg best'), align: 'text-center' },
	{ key: 'readiness', label: __('Readiness'), align: 'text-center' },
]

// Batch average of the learners' viva scores (only those who have taken one).
const vivaAvg = computed(() => {
	const vals = rows.value.map((r) => r.viva_avg).filter((v) => v !== null && v !== undefined)
	return vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null
})

const visibleRows = computed(() => {
	const list = rows.value.filter((r) => !bandFilter.value || r.readiness_band === bandFilter.value)
	const dir = sort.dir === 'asc' ? 1 : -1
	return [...list].sort((a, b) => {
		const x = a[sort.key]
		const y = b[sort.key]
		if (x === y) return 0
		if (x === null || x === undefined || x === '') return 1
		if (y === null || y === undefined || y === '') return -1
		return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir
	})
})

function sortBy(key) {
	if (sort.key === key) sort.dir = sort.dir === 'asc' ? 'desc' : 'asc'
	else Object.assign(sort, { key, dir: ['employee_name', 'location', 'training_manager'].includes(key) ? 'asc' : 'desc' })
}

function cellStyle(band) {
	const s = bandStyle(band)
	return { background: s.soft, color: s.text, borderColor: s.bg }
}

function openCard(row) {
	router.push({ name: 'LearnerReportCard', params: { name: row.name } })
}

function exportCsv() {
	const keys = ['employee_name', 'email', 'location', 'training_manager', 'batch_start', 'attendance_days', 'ai_mock_score', 'audit_score', 'viva_avg', 'dc', 'cc', 'talk_time', 'booked', 'catered', 'booking_rate', ...TEST_KEYS, 'readiness']
	const esc = (v) => {
		const text = String(v ?? '')
		// A cell starting with = + - @ is run as a formula when the file is opened in Excel.
		const safe = /^[=+\-@]/.test(text) ? `'${text}` : text
		return `"${safe.replace(/"/g, '""')}"`
	}
	const csv = [keys.join(','), ...visibleRows.value.map((r) => keys.map((k) => esc(r[k])).join(','))].join('\n')
	const link = document.createElement('a')
	link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
	link.download = 'learner-report.csv'
	link.click()
}
</script>

<style scoped>
.cr-card,
.cr-head {
	border: 1px solid #edf0f4;
	border-radius: 20px;
	background: #fff;
	box-shadow: 0 2px 10px rgba(0, 37, 76, 0.06);
}

.cr-head {
	overflow: hidden;
}

.cr-head-strip {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 1rem 1.25rem;
	background: #f4f9ff;
}

.cr-filters {
	display: flex;
	flex-wrap: wrap;
	gap: 0.6rem;
	padding: 0.85rem 1.25rem;
}

.cr-select,
.cr-search {
	display: inline-flex;
	align-items: center;
	gap: 0.5rem;
	height: 2.5rem;
	padding: 0 0.9rem;
	border: 1px solid var(--il-neutral-90);
	border-radius: 999px;
	background: #fff;
	font-size: 0.875rem;
}

.cr-select span {
	color: var(--il-muted);
	font-size: 0.8125rem;
}

.cr-select select {
	border: 0;
	padding: 0 1.25rem 0 0;
	background-color: transparent;
	color: var(--il-ink);
	font-weight: 500;
	font-size: 0.875rem;
	box-shadow: none;
}

.cr-search {
	flex: 1;
	min-width: 13rem;
}

.cr-search input {
	flex: 1;
	border: 0;
	padding: 0;
	background: transparent;
	box-shadow: none;
	font-size: 0.875rem;
}

.cr-h2 {
	margin: 1.5rem 0 0.75rem;
	color: var(--il-ink);
	font-size: 1.25rem;
	font-weight: 400;
}

.cr-highlights {
	display: grid;
	gap: 1.25rem;
	align-items: center;
	padding: 1.1rem 1.25rem;
}

@media (min-width: 1024px) {
	.cr-highlights {
		grid-template-columns: 17rem 1fr;
	}

	.cr-highlights > :first-child {
		height: 100%;
		border-right: 1px solid var(--il-neutral-90);
	}
}

.cr-donut {
	--p: 0;
	--c: #35c759;
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 6.25rem;
	height: 6.25rem;
	border-radius: 999px;
	background: radial-gradient(closest-side, #fff 68%, transparent 69%),
		conic-gradient(var(--c) calc(var(--p) * 1%), #e6f2ff 0);
}

.cr-donut span {
	color: var(--il-ink);
	font-size: 1.25rem;
	font-weight: 500;
}

.cr-tabs {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 0.75rem;
	margin: 1.5rem 0 1.25rem;
}

.cr-tabs button {
	height: 2.4rem;
	border: 1px solid var(--il-primary-40);
	border-radius: 999px;
	background: #fff;
	color: var(--il-primary-20);
	font-size: 0.875rem;
	font-weight: 500;
}

.cr-tabs button.is-active {
	border-color: #00254c;
	background: #00254c;
	color: #fff;
}

.cr-band {
	display: flex;
	align-items: center;
	justify-content: space-between;
	border: 1px solid;
	border-radius: 12px;
	padding: 0.75rem 0.9rem;
	text-align: left;
	transition: box-shadow 0.15s ease;
}

.cr-band:hover {
	box-shadow: 0 0 0 2px var(--il-primary-50);
}

.cr-legend {
	display: flex;
	flex-wrap: wrap;
	justify-content: flex-end;
	gap: 0.4rem 1.25rem;
	margin-top: 1rem;
	border-top: 1px solid var(--il-neutral-90);
	padding-top: 0.85rem;
	color: var(--il-ink);
	font-size: 0.8125rem;
}

.cr-input {
	overflow: hidden;
	border: 1px solid;
	border-radius: 12px;
}

.cr-input-foot {
	margin-top: 0.75rem;
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	padding: 0.45rem 0.9rem;
	background: #fff;
	color: var(--il-muted);
	font-size: 0.75rem;
}

.cr-stat {
	border: 1px solid #edf0f4;
	border-radius: 14px;
	padding: 0.85rem 1rem;
	text-align: center;
	box-shadow: 0 1px 4px rgba(0, 37, 76, 0.05);
}

.cr-mini-wrap {
	max-height: 26rem;
	overflow: auto;
	border: 1px solid #edf0f4;
	border-radius: 12px;
}

.cr-mini {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	font-size: 0.8125rem;
}

.cr-mini th {
	position: sticky;
	top: 0;
	z-index: 1;
	padding: 0.6rem 0.75rem;
	background: #fff;
	color: var(--il-ink);
	font-weight: 500;
	text-align: left;
	border-bottom: 1px solid var(--il-neutral-90);
	white-space: nowrap;
}

.cr-mini td {
	padding: 0.4rem 0.75rem;
	border-bottom: 1px solid var(--il-neutral-95);
	color: var(--il-ink);
}

.cr-mini-lg td {
	padding: 0.65rem 0.75rem;
}

.cr-mini tbody tr {
	cursor: pointer;
}

.cr-mini tbody tr:hover td {
	background: #f7fbff;
}

.cr-name {
	display: flex;
	min-width: 15rem;
	justify-content: space-between;
	gap: 1rem;
	border-radius: 6px;
	padding: 0.35rem 0.7rem;
	font-weight: 500;
	white-space: nowrap;
}

.cr-dot {
	display: inline-block;
	width: 0.4rem;
	height: 0.4rem;
	margin-right: 0.25rem;
	border-radius: 999px;
	vertical-align: middle;
}

.cr-filter-chip {
	display: inline-flex;
	align-items: center;
	gap: 0.3rem;
	border: 1px solid;
	border-radius: 999px;
	padding: 0.15rem 0.6rem;
	font-size: 0.75rem;
	font-weight: 500;
}

.rp-table-wrap {
	overflow-x: auto;
}

.rp-table {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	font-size: 0.8125rem;
}

.rp-table th {
	padding: 0.6rem 0.75rem;
	background: #fff;
	color: var(--il-muted);
	font-size: 0.75rem;
	font-weight: 500;
	white-space: nowrap;
	cursor: pointer;
	user-select: none;
	border-bottom: 1px solid var(--il-neutral-90);
}

.rp-group-row th {
	background: #fff;
	color: var(--il-ink);
	font-size: 0.8125rem;
	font-weight: 500;
	text-align: center;
	cursor: default;
	border-bottom: 0;
}

.rp-table td {
	padding: 0.55rem 0.75rem;
	border-bottom: 1px solid var(--il-neutral-95);
	color: var(--il-ink);
	white-space: nowrap;
}

.rp-table tbody tr {
	cursor: pointer;
}

.rp-table tbody tr:hover td {
	background: #f7fbff;
}

.rp-table tfoot td {
	background: #f4f9ff;
	color: var(--il-ink);
	font-weight: 500;
}

.rp-sticky {
	position: sticky;
	left: 0;
	z-index: 1;
	min-width: 14rem;
	background: #fff;
	text-align: left;
}

.rp-table tfoot .rp-sticky {
	background: #f4f9ff;
}

.rp-avatar {
	display: grid;
	flex-shrink: 0;
	place-items: center;
	width: 2rem;
	height: 2rem;
	border-radius: 999px;
	background: var(--il-primary-95);
	color: var(--il-primary-40);
	font-size: 0.75rem;
	font-weight: 600;
}

.rp-cell {
	display: inline-block;
	min-width: 2.5rem;
	border: 1px solid;
	border-radius: 8px;
	padding: 0.15rem 0.5rem;
	font-variant-numeric: tabular-nums;
	font-weight: 500;
}

.rp-cell-strong {
	min-width: 3.5rem;
	font-weight: 600;
}

.cr-batch-group {
	overflow: hidden;
	border: 1px solid #edf0f4;
	border-radius: 16px;
	background: #fff;
	box-shadow: 0 2px 10px rgba(0, 37, 76, 0.06);
}

.cr-batch-head {
	display: flex;
	width: 100%;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	padding: 1rem 1.25rem;
	background: #f4f9ff;
	border: none;
	cursor: pointer;
	text-align: left;
}

.cr-batch-body {
	padding: 0 1rem 1rem;
	overflow-x: auto;
}

@media (max-width: 640px) {
	.cr-tabs {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
