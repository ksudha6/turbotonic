// Bridges the WebAuthn browser API (ArrayBuffer) and the server JSON format (base64url strings).

export function base64urlToBuffer(base64url: string): ArrayBuffer {
	const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
	const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
	const binary = atob(padded);
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) {
		bytes[i] = binary.charCodeAt(i);
	}
	return bytes.buffer;
}

export function bufferToBase64url(buffer: ArrayBuffer): string {
	const bytes = new Uint8Array(buffer);
	let binary = '';
	for (let i = 0; i < bytes.length; i++) {
		binary += String.fromCharCode(bytes[i]);
	}
	return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export async function startRegistration(options: Record<string, unknown>): Promise<Record<string, unknown>> {
	const publicKey = { ...options } as Record<string, unknown>;

	publicKey.challenge = base64urlToBuffer(options.challenge as string);

	const user = { ...(options.user as Record<string, unknown>) };
	user.id = base64urlToBuffer(user.id as string);
	publicKey.user = user;

	if (Array.isArray(options.excludeCredentials)) {
		publicKey.excludeCredentials = options.excludeCredentials.map((cred: Record<string, unknown>) => ({
			...cred,
			id: base64urlToBuffer(cred.id as string)
		}));
	}

	const credential = await navigator.credentials.create({ publicKey: publicKey as unknown as PublicKeyCredentialCreationOptions });
	if (!credential) throw new Error('navigator.credentials.create returned null');

	const pkc = credential as PublicKeyCredential;
	const response = pkc.response as AuthenticatorAttestationResponse;

	return {
		id: pkc.id,
		rawId: bufferToBase64url(pkc.rawId),
		type: pkc.type,
		response: {
			clientDataJSON: bufferToBase64url(response.clientDataJSON),
			attestationObject: bufferToBase64url(response.attestationObject)
		}
	};
}

export async function startAuthentication(options: Record<string, unknown>): Promise<Record<string, unknown>> {
	const publicKey = { ...options } as Record<string, unknown>;

	publicKey.challenge = base64urlToBuffer(options.challenge as string);

	if (Array.isArray(options.allowCredentials)) {
		publicKey.allowCredentials = options.allowCredentials.map((cred: Record<string, unknown>) => ({
			...cred,
			id: base64urlToBuffer(cred.id as string)
		}));
	}

	const credential = await navigator.credentials.get({ publicKey: publicKey as unknown as PublicKeyCredentialRequestOptions });
	if (!credential) throw new Error('navigator.credentials.get returned null');

	const pkc = credential as PublicKeyCredential;
	const response = pkc.response as AuthenticatorAssertionResponse;

	return {
		id: pkc.id,
		rawId: bufferToBase64url(pkc.rawId),
		type: pkc.type,
		response: {
			clientDataJSON: bufferToBase64url(response.clientDataJSON),
			authenticatorData: bufferToBase64url(response.authenticatorData),
			signature: bufferToBase64url(response.signature)
		}
	};
}
