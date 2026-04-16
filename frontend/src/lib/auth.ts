import type { User } from './types';

async function authFetch(path: string, options?: RequestInit): Promise<Response> {
	return fetch(path, {
		...options,
		credentials: 'include'
	});
}

async function throwOnError(res: Response): Promise<void> {
	if (!res.ok) {
		let detail: string | undefined;
		try {
			const body = await res.json();
			detail = body?.detail;
		} catch {
			// body not JSON
		}
		throw new Error(detail ?? `Request failed: ${res.status}`);
	}
}

export async function bootstrap(
	username: string,
	displayName: string
): Promise<{ options: any; user: User }> {
	const res = await authFetch('/api/v1/auth/bootstrap', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username, display_name: displayName })
	});
	await throwOnError(res);
	return res.json();
}

export async function registerOptions(username: string): Promise<{ options: any; user: User }> {
	const res = await authFetch('/api/v1/auth/register/options', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username })
	});
	await throwOnError(res);
	return res.json();
}

export async function registerVerify(
	username: string,
	credential: any
): Promise<{ user: User }> {
	const res = await authFetch('/api/v1/auth/register/verify', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username, credential })
	});
	await throwOnError(res);
	return res.json();
}

export async function loginOptions(username: string): Promise<{ options: any }> {
	const res = await authFetch('/api/v1/auth/login/options', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username })
	});
	await throwOnError(res);
	return res.json();
}

export async function loginVerify(
	username: string,
	credential: any
): Promise<{ user: User }> {
	const res = await authFetch('/api/v1/auth/login/verify', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username, credential })
	});
	await throwOnError(res);
	return res.json();
}

export async function logout(): Promise<void> {
	const res = await authFetch('/api/v1/auth/logout', { method: 'POST' });
	await throwOnError(res);
}

export async function me(): Promise<User | null> {
	const res = await authFetch('/api/v1/auth/me');
	if (res.status === 401) {
		return null;
	}
	await throwOnError(res);
	const body = await res.json();
	return body.user as User;
}
