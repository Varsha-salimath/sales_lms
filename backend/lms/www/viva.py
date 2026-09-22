"""CRT Day 1 viva demo — served as a raw HTML page, not the Vue SPA."""

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_header = True
	context.no_breadcrumbs = True
	return context
