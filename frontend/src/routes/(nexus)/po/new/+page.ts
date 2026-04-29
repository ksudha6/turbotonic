import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canCreatePO } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canCreatePO(user.role)) {
		throw redirect(307, '/po');
	}
};
