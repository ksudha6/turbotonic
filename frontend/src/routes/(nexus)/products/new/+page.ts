import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canManageProducts, canViewProducts } from '$lib/permissions';

export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canManageProducts(user.role)) {
		throw redirect(307, user && canViewProducts(user.role) ? '/products' : '/dashboard');
	}
};
