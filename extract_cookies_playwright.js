#!/usr/bin/env node
/**
 * Extract ALL cookies including httpOnly li_at using Playwright for Node.js
 * This uses Playwright's context.cookies() method which can access httpOnly cookies
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

async function extractLinkedInCookies() {
    console.log("=".repeat(60));
    console.log("Playwright Node.js Cookie Extraction");
    console.log("=".repeat(60));
    console.log();

    const browser = await chromium.launch({
        headless: false,
        args: ['--disable-blink-features=AutomationControlled']
    });

    try {
        // Create a new context
        const context = await browser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });

        // Create a new page
        const page = await context.newPage();

        // Navigate to LinkedIn
        console.log("🌐 Navigating to LinkedIn...");
        await page.goto('https://www.linkedin.com/login', { waitUntil: 'domcontentloaded', timeout: 60000 });

        // Check if we need to login
        const currentUrl = page.url();
        
        if (currentUrl.includes('feed')) {
            console.log("✅ Already logged in!");
        } else {
            console.log("📝 Logging in...");
            
            // Fill in credentials
            const email = process.env.LINKEDIN_USERNAME || 'your_email@example.com';
            const password = process.env.LINKEDIN_PASSWORD || 'your_password';
            await page.fill('input[name="session_key"]', email);
            await page.fill('input[name="session_password"]', password);
            
            // Click login button
            await page.click('button[type="submit"]');
            
            console.log("⏳ Waiting for login...");
            
            try {
                // Wait for navigation to feed
                await page.waitForURL('**/feed/**', { timeout: 10000 });
                console.log("✅ Login successful!");
            } catch (error) {
                // Check if 2FA is required
                if (page.url().includes('checkpoint') || page.url().includes('challenge')) {
                    console.log("🔐 2FA required - please complete in browser");
                    console.log("   Waiting for manual authentication (60 seconds)...");
                    await page.waitForURL('**/feed/**', { timeout: 60000 });
                    console.log("✅ Authentication successful!");
                }
            }
        }

        // EXTRACT ALL COOKIES INCLUDING HTTPONLY
        console.log("\n🍪 Extracting ALL cookies using Playwright context.cookies()...");
        const allCookies = await context.cookies();
        
        console.log(`✅ Found ${allCookies.length} total cookies`);
        
        // Find li_at and other httpOnly cookies
        let liAtCookie = null;
        const httpOnlyCookies = [];
        
        for (const cookie of allCookies) {
            if (cookie.httpOnly) {
                httpOnlyCookies.push(cookie);
                if (cookie.name === 'li_at') {
                    liAtCookie = cookie;
                    console.log("\n🎯 FOUND li_at cookie!");
                    console.log(`   Value: ${cookie.value.substring(0, 50)}...`);
                    console.log(`   Domain: ${cookie.domain}`);
                    console.log(`   HttpOnly: ${cookie.httpOnly}`);
                    console.log(`   Secure: ${cookie.secure}`);
                }
            }
        }
        
        console.log(`\n📊 Found ${httpOnlyCookies.length} httpOnly cookies`);
        
        // Format cookies for Selenium/Docker
        const seleniumCookies = allCookies.map(cookie => ({
            name: cookie.name,
            value: cookie.value,
            domain: cookie.domain,
            path: cookie.path,
            secure: cookie.secure || false,
            httpOnly: cookie.httpOnly || false,
            sameSite: cookie.sameSite || 'None',
            ...(cookie.expires && cookie.expires !== -1 ? { expiry: cookie.expires } : {})
        }));
        
        // Create output object
        const output = {
            extraction_date: new Date().toISOString(),
            extraction_method: "playwright_nodejs_context_cookies",
            authenticated_user: email.split('@')[0],
            email: email,
            li_at_found: liAtCookie !== null,
            li_at_value: liAtCookie ? liAtCookie.value : null,
            total_cookies: allCookies.length,
            httponly_cookies: httpOnlyCookies.length,
            cookies: seleniumCookies,
            raw_playwright_cookies: allCookies
        };
        
        // Save to file
        const filename = "linkedin_cookies_complete_nodejs.json";
        await fs.writeFile(filename, JSON.stringify(output, null, 2));
        console.log(`\n✅ Saved all cookies to ${filename}`);
        
        if (liAtCookie) {
            console.log("\n🎉 SUCCESS! li_at cookie extracted!");
            console.log(`   Full value: ${liAtCookie.value}`);
            
            // Save li_at separately
            await fs.writeFile('li_at_token.txt', liAtCookie.value);
            console.log("✅ li_at token saved to li_at_token.txt");
            
            // Create simple cookie file for Docker
            const dockerCookies = {
                li_at: liAtCookie.value,
                JSESSIONID: allCookies.find(c => c.name === 'JSESSIONID')?.value || null,
                lidc: allCookies.find(c => c.name === 'lidc')?.value || null,
                bcookie: allCookies.find(c => c.name === 'bcookie')?.value || null,
            };
            
            await fs.writeFile('linkedin_docker_cookies.json', JSON.stringify(dockerCookies, null, 2));
            console.log("✅ Simple cookie dict saved to linkedin_docker_cookies.json");
        }
        
        // Print all httpOnly cookies found
        console.log("\n📋 All httpOnly cookies found:");
        for (const cookie of httpOnlyCookies) {
            console.log(`   🔒 ${cookie.name}: ${cookie.value.substring(0, 30)}...`);
        }
        
        // Take a screenshot for verification
        await page.screenshot({ path: 'linkedin_logged_in.png' });
        console.log("\n📸 Screenshot saved to linkedin_logged_in.png");
        
        return output;
        
    } catch (error) {
        console.error("❌ Error:", error.message);
        console.error(error.stack);
        return null;
    } finally {
        // Keep browser open for a moment
        console.log("\n⏸️  Browser will close in 5 seconds...");
        await new Promise(resolve => setTimeout(resolve, 5000));
        await browser.close();
        console.log("✅ Browser closed");
    }
}

// Main execution
async function main() {
    console.log("This script uses Playwright's context.cookies() to extract ALL cookies");
    console.log("including httpOnly cookies like li_at");
    console.log();
    console.log("Requirements: playwright");
    console.log("Install with: npm install playwright");
    console.log();
    
    try {
        const result = await extractLinkedInCookies();
        
        if (result && result.li_at_found) {
            console.log("\n" + "=".repeat(60));
            console.log("✅ SUCCESS! All cookies extracted including li_at");
            console.log("=".repeat(60));
            console.log("\nFiles created:");
            console.log("  - linkedin_cookies_complete_nodejs.json (all cookies)");
            console.log("  - li_at_token.txt (just the li_at value)");
            console.log("  - linkedin_docker_cookies.json (simple format for Docker)");
            console.log("\nYou can now use these in Docker for LinkedIn automation!");
        } else {
            console.log("\n" + "=".repeat(60));
            console.log("⚠️  Could not extract li_at cookie");
            console.log("=".repeat(60));
        }
    } catch (error) {
        console.error("❌ Fatal error:", error.message);
        process.exit(1);
    }
}

// Check if playwright is installed
try {
    require('playwright');
    main();
} catch (error) {
    console.error("❌ Playwright not installed");
    console.error("Please run: npm install playwright");
    console.error("\nOr install globally: npm install -g playwright");
    process.exit(1);
}