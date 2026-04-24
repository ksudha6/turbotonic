import { test, expect } from '@playwright/test';
import { resolveRedirect } from '../src/lib/ui/redirects';

test('resolveRedirect returns null for unmapped paths', () => {
	expect(resolveRedirect('/nonexistent')).toBeNull();
});

test('resolveRedirect substitutes :param tokens from mapped entries', () => {
	const registry = { '/test-old/:id': '/test-new/:id' };
	expect(resolveRedirect('/test-old/123', registry)).toBe('/test-new/123');
});

test('resolveRedirect handles multiple :param tokens', () => {
	const registry = { '/a/:x/b/:y': '/new/:y/:x' };
	expect(resolveRedirect('/a/foo/b/bar', registry)).toBe('/new/bar/foo');
});
