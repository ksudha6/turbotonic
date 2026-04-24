import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { me } from '$lib/auth';

export const prerender = false;
export const ssr = false;

export const load: LayoutLoad = async ({ url }) => {
	const user = await me();
	if (!user) {
		const redirectParam = encodeURIComponent(url.pathname + url.search);
		throw redirect(307, `/login?redirect=${redirectParam}`);
	}
	return { user };
};
