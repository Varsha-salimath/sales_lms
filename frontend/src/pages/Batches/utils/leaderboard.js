export function sortBatchmates(batchmates) {
	return [...batchmates].sort((a, b) => {
		if (b.completion_pct !== a.completion_pct) {
			return b.completion_pct - a.completion_pct
		}
		return (a.full_name || '').localeCompare(b.full_name || '', undefined, {
			sensitivity: 'base',
		})
	})
}

export function getProgressBarColor(completionPct, isCurrentUser) {
	if (isCurrentUser) return '#1D9E75'
	if (completionPct >= 70) return '#378ADD'
	if (completionPct >= 40) return '#EF9F27'
	return '#B4B2A9'
}

export function computeLeaderboardStats(sortedBatchmates, totalLessons) {
	const currentUser = sortedBatchmates.find((m) => m.is_current_user)
	const currentUserIndex = sortedBatchmates.findIndex((m) => m.is_current_user)
	const yourRank = currentUserIndex >= 0 ? currentUserIndex + 1 : null

	const batchAverage =
		sortedBatchmates.length > 0
			? Math.round(
					sortedBatchmates.reduce((sum, m) => sum + m.completion_pct, 0) /
						sortedBatchmates.length
				)
			: 0

	return {
		yourRank,
		yourProgress: currentUser ? Math.round(currentUser.completion_pct) : 0,
		yourLessonsCompleted: currentUser?.lessons_completed || 0,
		totalLessons,
		batchAverage,
		currentUser,
	}
}

export function getInitials(fullName) {
	if (!fullName) return '?'
	const parts = fullName.trim().split(/\s+/)
	if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
	return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

export function getAvatarColor(fullName) {
	const colors = [
		'#E8F5F0',
		'#FDE8F0',
		'#E8F0FD',
		'#E8F5E8',
		'#F0E8FD',
		'#FDE8E8',
		'#FDF5E8',
		'#E8E8E8',
	]
	const textColors = [
		'#1D9E75',
		'#D4537E',
		'#378ADD',
		'#2D8A4E',
		'#7B4FD4',
		'#D45353',
		'#C48A1A',
		'#6B6B6B',
	]
	let hash = 0
	for (let i = 0; i < (fullName || '').length; i++) {
		hash = fullName.charCodeAt(i) + ((hash << 5) - hash)
	}
	const idx = Math.abs(hash) % colors.length
	return { bg: colors[idx], text: textColors[idx] }
}
