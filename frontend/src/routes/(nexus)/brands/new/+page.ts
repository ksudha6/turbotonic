import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canManageBrands } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canManageBrands(user.role)) {
		throw redirect(307, '/brands');
	}
};
