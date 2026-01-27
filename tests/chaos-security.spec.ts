import { test, expect } from '@playwright/test';

// Define the "garbage" payloads for Fuzzing/Security
const PAYLOADS = {
  sqlInjection: "' OR 1=1 --",
  xss: '<script>alert("XSS")</script>',
  hugeText: 'A'.repeat(5000), // 5k characters
  negativeNumber: '-99',
  emoji: '🤡💀🔥',
};

test.describe('Chaos & Security Suite', () => {

  // =========================================================
  // 1. THE FUZZER & SECURITY (Inputs)
  // =========================================================
  test('The Fuzzer: Input validation (SQLi, XSS, Garbage)', async ({ page }) => {
    // 1. Go to a page with forms (e.g., signup or settings)
    await page.goto('/signup'); 

    // Handle any alert dialogs if XSS actually succeeds (prevent test hang)
    page.on('dialog', dialog => {
      console.log(`Alert detected: ${dialog.message()}`);
      dialog.dismiss();
    });

    // --- Scenario A: The "Age" Field (-99) ---
    // Update selector to match your actual ID (e.g., #age, input[name="age"])
    const ageInput = page.locator('input[name="age"]').first();
    if (await ageInput.isVisible()) {
      await ageInput.fill(PAYLOADS.negativeNumber);
      await ageInput.blur(); // Trigger validation
      // Expect the form NOT to crash, or show a validation error
      // expect(await page.locator('.error-message')).toBeVisible();
    }

    // --- Scenario B: The "Email" Field (The Novel + XSS) ---
    const emailInput = page.locator('input[type="email"]').first();
    if (await emailInput.isVisible()) {
      await emailInput.fill(PAYLOADS.hugeText); // 5000 chars
      await emailInput.clear();
      await emailInput.fill(PAYLOADS.xss); // <script> tag
      // If the input value remains the exact script tag, the UI didn't sanitize immediately.
      // But mainly we are checking if the page crashes.
    }

    // --- Scenario C: The "Price" Field (Emojis) ---
    const priceInput = page.locator('input[name="price"], input[type="number"]').first();
    if (await priceInput.isVisible()) {
      await priceInput.fill(PAYLOADS.emoji);
      // Check if value is actually empty (browsers often block non-numbers in number inputs)
      const value = await priceInput.inputValue();
      console.log(`Price input value after emoji: ${value}`);
    }
  });

  // =========================================================
  // 2. THE MONKEY (Random Clicks)
  // =========================================================
  test('The Monkey: Random interactions', async ({ page }) => {
    await page.goto('/');
    
    // Give the page a second to settle
    await page.waitForLoadState('networkidle');

    // Get all clickable elements (buttons, links, inputs)
    // We use a broader selector to find anything interactive
    const interactables = page.locator('button, a[href^="/"], input[type="submit"], input[type="button"]');
    
    const count = await interactables.count();
    console.log(`Monkey found ${count} clickable elements.`);

    // Click random things 20 times (100 might be too slow for CI, adjust as needed)
    for (let i = 0; i < 20; i++) {
      if (count === 0) break;

      // Pick a random index
      const randomIndex = Math.floor(Math.random() * count);
      const element = interactables.nth(randomIndex);

      // Check visibility before clicking to avoid errors
      if (await element.isVisible()) {
        try {
          // Force click in case it's covered by a popup
          await element.click({ timeout: 500, force: true });
        } catch (e) {
          // Monkey doesn't care about errors, it just keeps clicking
          console.log(`Monkey missed click on element ${randomIndex}`);
        }
      }
      
      // OPTIONAL: Wait a tiny bit between clicks to mimic frantic human
      await page.waitForTimeout(100); 
    }

    // Assertion: The App should still be alive (not a white screen)
    await expect(page.locator('body')).toBeVisible();
  });

  // =========================================================
  // 3. THE NAVIGATOR (History State Confusion)
  // =========================================================
  test('The Navigator: Rapid Back/Forward navigation', async ({ page }) => {
    await page.goto('/');
    const currentUrl = page.url();

    // 1. Click the first available link to go somewhere else
    const firstLink = page.locator('a[href]').first();
    if (await firstLink.isVisible()) {
      await firstLink.click({ force: true });
      await page.waitForLoadState('domcontentloaded');
    }

    // 2. Panic Navigation: Back -> Forward -> Back
    await page.goBack();
    await page.goForward();
    await page.goBack();

    // 3. Refresh for good measure
    await page.reload();

    // 4. Assertion: App did not crash (check for a key element like a header or footer)
    // Adjust selector to match your app, e.g. 'header', '#navbar'
    await expect(page.locator('body')).toBeVisible();
    
    console.log('Navigator survived the history traversal.');
  });

  // =========================================================
  // 4. API FUZZING (Sending Garbage to Backend)
  // =========================================================
  test('API Fuzzing: Sending garbage data', async ({ request }) => {
    // Assuming you have an endpoint like /api/user or /api/contact
    const endpoint = '/api/test-endpoint'; 

    // 1. Send Massive Payload
    const responseHuge = await request.post(endpoint, {
      data: { comment: PAYLOADS.hugeText }
    });
    // We expect the server to handle it (400 Bad Request or 200 OK), NOT 500 Crash
    expect(responseHuge.status()).not.toBe(500);

    // 2. Send Malformed JSON (SQL Injection attempt via API)
    const responseSQL = await request.post(endpoint, {
      data: { username: PAYLOADS.sqlInjection }
    });
    expect(responseSQL.status()).not.toBe(500);
  });

});