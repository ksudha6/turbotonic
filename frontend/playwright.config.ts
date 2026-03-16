import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: './tests',
	testIgnore: '**/scratch/**',
	projects: [
		{
			name: 'chromium',
			use: { browserName: 'chromium' },
		},
	],
	use: {
		baseURL: 'http://localhost:5173',
	},
});
