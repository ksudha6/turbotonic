import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canManageProducts, canViewProducts } from '$lib/permissions';

// Iter 105: FM may view (but not edit) the product page to approve certificates.
// canManageProducts controls the edit/add actions within the page components.
export const load: PageLoad = async ({ parent }) => {
	const { user } = await parent();
	if (!user || !canViewProducts(user.role)) {
		throw redirect(307, '/dashboard');
	}
};
