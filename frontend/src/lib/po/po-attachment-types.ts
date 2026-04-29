import type { POType } from '$lib/types';

export type POAttachmentType =
	| 'SIGNED_PO'
	| 'COUNTERSIGNED_PO'
	| 'SIGNED_AGREEMENT'
	| 'AMENDMENT'
	| 'ADDENDUM';

export const PROCUREMENT_ATTACHMENT_TYPES: readonly POAttachmentType[] = [
	'SIGNED_PO',
	'COUNTERSIGNED_PO',
	'AMENDMENT',
	'ADDENDUM'
] as const;

export const OPEX_ATTACHMENT_TYPES: readonly POAttachmentType[] = [
	'SIGNED_AGREEMENT',
	'AMENDMENT',
	'ADDENDUM'
] as const;

export function allowedAttachmentTypes(poType: POType): readonly POAttachmentType[] {
	return poType === 'PROCUREMENT' ? PROCUREMENT_ATTACHMENT_TYPES : OPEX_ATTACHMENT_TYPES;
}

export const ATTACHMENT_TYPE_LABELS: Record<POAttachmentType, string> = {
	SIGNED_PO: 'Signed PO',
	COUNTERSIGNED_PO: 'Countersigned PO',
	SIGNED_AGREEMENT: 'Signed agreement',
	AMENDMENT: 'Amendment',
	ADDENDUM: 'Addendum'
};
