import type { ReferenceData } from '$lib/types';

export function buildLabelResolver(refData: ReferenceData) {
	const maps: Record<string, Map<string, string>> = {
		currencies: new Map(refData.currencies.map((i) => [i.code, i.label])),
		incoterms: new Map(refData.incoterms.map((i) => [i.code, i.label])),
		payment_terms: new Map(refData.payment_terms.map((i) => [i.code, i.label])),
		countries: new Map(refData.countries.map((i) => [i.code, i.label])),
		ports: new Map(refData.ports.map((i) => [i.code, i.label])),
		vendor_types: new Map(refData.vendor_types.map((i) => [i.code, i.label])),
		po_types: new Map(refData.po_types.map((i) => [i.code, i.label]))
	};

	return {
		resolve(category: string, code: string): string {
			if (category === 'ports') {
				const city = maps.ports.get(code);
				if (!city) return code;
				const countryCode = code.slice(0, 2);
				const country = maps.countries.get(countryCode);
				return country ? `${city}, ${country}` : city;
			}
			return maps[category]?.get(code) ?? code;
		}
	};
}
