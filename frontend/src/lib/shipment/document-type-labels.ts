export const DOCUMENT_TYPE_LABELS: Readonly<Record<string, string>> = {
	PACKING_LIST: 'Packing List',
	COMMERCIAL_INVOICE: 'Commercial Invoice',
	BILL_OF_LADING: 'Bill of Lading',
	CERTIFICATE_OF_ORIGIN: 'Certificate of Origin',
	INSURANCE_CERTIFICATE: 'Insurance Certificate',
	EEI_AES: 'EEI / AES Filing',
};

export function labelForDocumentType(type: string): string {
	return DOCUMENT_TYPE_LABELS[type] ?? type;
}
