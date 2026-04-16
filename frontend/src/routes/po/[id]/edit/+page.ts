import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { canEditPO } from '$lib/permissions';

export const load: PageLoad = async ({ parent, params }) => {
	const { user } = await parent();
	if (!user || !canEditPO(user.role)) {
		throw redirect(307, `/po/${params.id}`);
	}
};
