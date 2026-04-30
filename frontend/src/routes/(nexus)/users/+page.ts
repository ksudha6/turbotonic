import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canManageUsers } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canManageUsers(user.role)) {
		throw redirect(307, '/dashboard');
	}
};
