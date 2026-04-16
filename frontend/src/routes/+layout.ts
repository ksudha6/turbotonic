import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { me } from '$lib/auth';

export const prerender = false;
export const ssr = false;

const PUBLIC_ROUTES = ['/login', '/register', '/setup'];

export const load: LayoutLoad = async ({ url }) => {
	const isPublic = PUBLIC_ROUTES.some((r) => url.pathname.startsWith(r));

	const user = await me();

	if (!user && !isPublic) {
		const redirectParam = encodeURIComponent(url.pathname + url.search);
		throw redirect(307, `/login?redirect=${redirectParam}`);
	}

	return { user };
};
