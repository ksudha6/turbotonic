import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canViewBrands } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canViewBrands(user.role)) {
		throw redirect(307, '/dashboard');
	}
};
