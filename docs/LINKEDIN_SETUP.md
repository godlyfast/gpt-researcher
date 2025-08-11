# LinkedIn Sales Navigator Integration

## Overview

GPT Researcher now supports LinkedIn Sales Navigator as a data source for finding leads, companies, and professional information. This integration uses cookie-based authentication to access LinkedIn data programmatically.

## Prerequisites

- LinkedIn account with Sales Navigator access (optional but recommended)
- Node.js installed (for cookie extraction)
- Docker (for running in containerized environment)

## Setup Instructions

### 1. Environment Configuration

Add your LinkedIn credentials to `.env`:

```bash
# LinkedIn Sales Navigator Credentials
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Enable LinkedIn retriever
RETRIEVER=tavily,linkedin
```

### 2. Cookie Extraction

LinkedIn uses httpOnly cookies for authentication. We need to extract these using Playwright:

#### Install Dependencies

```bash
npm install playwright
npx playwright install chromium
```

#### Extract Cookies

Run the extraction script:

```bash
node extract_cookies_playwright.js
```

This script will:
1. Open a browser window
2. Navigate to LinkedIn login
3. Log in with your credentials
4. Handle 2FA if required (complete in browser)
5. Extract ALL cookies including the httpOnly `li_at` token
6. Save cookies to multiple formats

#### Output Files

- `linkedin_cookies_complete_nodejs.json` - Full cookie data with all metadata
- `linkedin_docker_cookies.json` - Simplified key-value format for Docker
- `li_at_token.txt` - Just the li_at authentication token

### 3. Using the Integration

#### Python Script

```python
from gpt_researcher.retrievers.linkedin import LinkedInSalesNavigator

# The retriever will automatically use cookies from the JSON files
retriever = LinkedInSalesNavigator(
    query="Find JavaScript developers in Valencia",
    headers={},
    topic="Tech Talent Search"
)

results = retriever.search(query)
```

#### Docker Environment

The cookies are automatically mounted in Docker:

```bash
docker-compose up --build
```

### 4. Cookie Management

#### Cookie Lifespan
- LinkedIn cookies typically expire after 1 year
- The `li_at` token is the primary authentication token
- Re-run extraction when authentication fails

#### Important Cookies
- `li_at` - Main authentication token (httpOnly)
- `JSESSIONID` - Session identifier
- `lidc` - LinkedIn data center cookie
- `bcookie` - Browser verification cookie

## Features

The LinkedIn retriever supports:

- **Lead Search**: Find people by job title, location, company
- **Company Search**: Search companies by size, industry, location
- **Filters**:
  - Location (cities, regions, countries)
  - Company size (1-10, 11-50, 51-200, etc.)
  - Job function and seniority level
  - Industry and keywords
- **Multi-language**: Works with queries in any language
- **Rate Limiting**: Built-in delays to avoid detection

## Query Examples

```python
# Find CTOs in Barcelona
"Find CTOs of tech companies in Barcelona"

# Search for startups
"Find startup founders in Spain with 10-50 employees"

# Industry-specific search
"Search for fintech companies in Europe"

# Multi-language support
"Знайти JavaScript розробників в Україні"
```

## Troubleshooting

### Authentication Issues

If authentication fails:
1. Re-run the cookie extraction script
2. Ensure 2FA is completed if required
3. Check that cookies haven't expired

### Rate Limiting

The system includes automatic rate limiting. If you encounter blocks:
- Reduce query frequency
- Add longer delays between searches
- Use residential proxies if needed

### Cookie Extraction Fails

If the extraction script fails:
1. Update Playwright: `npm update playwright`
2. Clear browser cache and retry
3. Manually complete any CAPTCHAs in the browser

## Technical Details

### Architecture

```
User Query → GPT Researcher → LinkedIn Retriever → Selenium/Requests → LinkedIn API
                                       ↓
                              Cookie Authentication
                                       ↓
                              Results Processing → Formatted Output
```

### File Structure

```
gpt_researcher/
├── retrievers/
│   └── linkedin/
│       ├── __init__.py
│       └── linkedin_sales_navigator.py
├── extract_cookies_playwright.js  # Cookie extraction script
└── linkedin_cookies_complete_nodejs.json  # Extracted cookies
```

### Security Notes

- Never commit cookies or credentials to version control
- The `.gitignore` includes all LinkedIn cookie files
- Use environment variables for sensitive data
- Rotate credentials regularly

## API Response Format

The LinkedIn retriever returns structured data:

```json
{
  "title": "John Doe",
  "company": "Tech Corp",
  "location": "Barcelona, Spain",
  "description": "CTO with 10+ years experience...",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "company_size": "51-200 employees",
  "industry": "Technology"
}
```

## Integration with GPT Researcher

LinkedIn data is automatically integrated into research reports when:
- Query mentions LinkedIn or professional profiles
- Research topic involves company or people search
- Sales/recruiting research is requested

The system intelligently combines LinkedIn data with other sources for comprehensive reports.

## Compliance and Ethics

- Respect LinkedIn's Terms of Service
- Use for legitimate business purposes only
- Don't scrape personal data without consent
- Implement appropriate data protection measures
- Consider GDPR/privacy regulations

## Support

For issues or questions:
- Check the [main documentation](../README.md)
- Review the [troubleshooting guide](#troubleshooting)
- Submit issues on GitHub