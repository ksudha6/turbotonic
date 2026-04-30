// Iter 100: row-action vocabulary for the ADMIN /users page. Lives in a .ts file
// so consumer routes import the type without pulling Svelte component code.
export type UserRowAction =
	| 'edit'
	| 'deactivate'
	| 'reactivate'
	| 'reset-credentials'
	| 'reissue-invite';
