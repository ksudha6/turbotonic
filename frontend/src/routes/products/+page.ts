import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canViewProducts } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canViewProducts(user.role)) {
		throw redirect(307, '/dashboard');
	}
};
