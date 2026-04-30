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
		baseURL: 'http://localhost:5174',
	},
	// Playwright manages the Vite dev server to guarantee a fresh module cache per run.
	// reuseExistingServer lets local developers running `make up` avoid a double start.
	webServer: {
		command: 'npm run dev -- --port 5174',
		url: 'http://localhost:5174',
		reuseExistingServer: !process.env.CI,
	},
});
