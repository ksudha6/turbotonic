import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canManageVendors } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canManageVendors(user.role)) {
		throw redirect(307, '/dashboard');
	}
};
