export type InvoiceAttachmentType =
	| 'VENDOR_INVOICE_PDF'
	| 'CREDIT_NOTE'
	| 'DEBIT_NOTE'
	| 'OTHER';

export const INVOICE_ATTACHMENT_TYPES: readonly InvoiceAttachmentType[] = [
	'VENDOR_INVOICE_PDF',
	'CREDIT_NOTE',
	'DEBIT_NOTE',
	'OTHER'
] as const;

export const INVOICE_ATTACHMENT_TYPE_LABELS: Record<InvoiceAttachmentType, string> = {
	VENDOR_INVOICE_PDF: 'Vendor invoice PDF',
	CREDIT_NOTE: 'Credit note',
	DEBIT_NOTE: 'Debit note',
	OTHER: 'Other'
};
