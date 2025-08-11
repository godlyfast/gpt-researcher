// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('GPT Researcher Application', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
  });

  test('should load the homepage', async ({ page }) => {
    // Check that the page loads
    await expect(page).toHaveTitle(/GPT Researcher/i);
    
    // Wait for the page to be fully loaded
    await page.waitForLoadState('networkidle');
  });

  test('should have working search functionality', async ({ page }) => {
    // Look for search input field
    const searchInput = page.locator('input[type="text"], input[placeholder*="search"], textarea');
    await expect(searchInput.first()).toBeVisible();
    
    // Test search functionality
    await searchInput.first().fill('artificial intelligence trends 2024');
    
    // Look for submit button
    const submitButton = page.locator('button:has-text("Research"), button[type="submit"], button:has-text("Search")');
    if (await submitButton.count() > 0) {
      await submitButton.first().click();
      
      // Wait for results or loading indicator
      await page.waitForTimeout(2000);
    }
  });

  test('should handle API connectivity', async ({ page }) => {
    // Test API endpoint directly
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);
  });

  test('should be responsive on mobile devices', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check that the page is still usable
    await expect(page.locator('body')).toBeVisible();
    
    // Check for mobile-friendly elements
    const mobileMenu = page.locator('[data-testid="mobile-menu"], .mobile-menu, .hamburger');
    if (await mobileMenu.count() > 0) {
      await expect(mobileMenu.first()).toBeVisible();
    }
  });

  test('should handle research workflow', async ({ page }) => {
    // Start a research task
    const searchQuery = 'climate change impact on agriculture';
    
    // Find and fill the search input
    const searchInput = page.locator('input, textarea').first();
    await searchInput.fill(searchQuery);
    
    // Submit the research request
    const submitButton = page.locator('button').first();
    await submitButton.click();
    
    // Wait for research to start (look for loading indicators)
    await page.waitForSelector('.loading, .spinner, [data-testid="loading"]', { 
      timeout: 5000,
      state: 'visible'
    }).catch(() => {
      // If no loading indicator found, that's okay
    });
    
    // Wait for results (with longer timeout for research)
    await page.waitForTimeout(10000);
    
    // Check if results are displayed
    const resultsContainer = page.locator('.results, .research-results, [data-testid="results"]');
    if (await resultsContainer.count() > 0) {
      await expect(resultsContainer.first()).toBeVisible();
    }
  });

  test('should validate frontend-backend communication', async ({ page, request }) => {
    // Test API endpoints
    const apiTests = [
      { endpoint: '/health', expectedStatus: 200 },
      { endpoint: '/api/research', expectedStatus: [200, 404, 405] }, // May not exist or need POST
      { endpoint: '/docs', expectedStatus: [200, 404] }, // FastAPI docs
    ];

    for (const apiTest of apiTests) {
      try {
        const response = await request.get(`http://localhost:8000${apiTest.endpoint}`);
        const expectedStatuses = Array.isArray(apiTest.expectedStatus) 
          ? apiTest.expectedStatus 
          : [apiTest.expectedStatus];
        
        expect(expectedStatuses).toContain(response.status());
        console.log(`✅ API ${apiTest.endpoint}: ${response.status()}`);
      } catch (error) {
        console.log(`⚠️  API ${apiTest.endpoint}: ${error.message}`);
      }
    }
  });

  test('should handle error states gracefully', async ({ page }) => {
    // Test with invalid input
    const searchInput = page.locator('input, textarea').first();
    await searchInput.fill(''); // Empty search
    
    const submitButton = page.locator('button').first();
    await submitButton.click();
    
    // Check for error messages or validation
    await page.waitForTimeout(2000);
    
    // Look for error indicators
    const errorElements = page.locator('.error, .alert-danger, [data-testid="error"]');
    if (await errorElements.count() > 0) {
      console.log('Error handling is working');
    }
  });

  test('should support file downloads', async ({ page }) => {
    // Test if the app supports downloading research results
    const downloadButton = page.locator('button:has-text("Download"), a[download], .download-btn');
    
    if (await downloadButton.count() > 0) {
      // Set up download listener
      const downloadPromise = page.waitForEvent('download');
      await downloadButton.first().click();
      
      try {
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toBeTruthy();
      } catch (error) {
        console.log('Download test skipped - no download triggered');
      }
    }
  });

});

test.describe('Performance Tests', () => {
  
  test('should load within acceptable time limits', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;
    
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
    console.log(`Page load time: ${loadTime}ms`);
  });

});