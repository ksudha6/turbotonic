// Central registry of old-route to new-route mappings, populated by aggregate
// phases as they retire old routes. Phase 4.0 ships the mechanism; no live
// mappings exist yet. Future entries look like:
//   '/po/:id': '/production/:id',
//   '/invoice/:id': '/invoices/:id',

const REDIRECTS: Record<string, string> = {};

export function resolveRedirect(
	pathname: string,
	registry: Record<string, string> = REDIRECTS
): string | null {
	for (const [pattern, target] of Object.entries(registry)) {
		const regex = new RegExp(
			'^' + pattern.replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, '(?<$1>[^/]+)') + '$'
		);
		const match = pathname.match(regex);
		if (match) {
			let result = target;
			for (const [key, value] of Object.entries(match.groups ?? {})) {
				result = result.replace(`:${key}`, value);
			}
			return result;
		}
	}
	return null;
}
