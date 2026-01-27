import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI to avoid timeouts/overload */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. */
  reporter: 'html',

  /* Shared settings for all the projects below. */
  use: {
    /* * CRITICAL: This allows the CI/CD pipeline to inject the Vercel/Azure URL.
     * If BASE_URL is not set (e.g., running locally), it falls back to localhost.
     */
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  /* * LOCAL DEVELOPMENT ONLY:
   * This optional block spins up your local server when you run 'npx playwright test'
   * on your machine.
   * * NOTE: We wrap this in a check so it DOES NOT run in your GitHub CI.
   * Your CI pipeline validates the *deployed* site, not a local server.
   */
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});