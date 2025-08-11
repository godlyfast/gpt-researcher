# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GPT Researcher is an LLM-based autonomous agent that conducts comprehensive web and local research on any topic, generating detailed reports with citations. The system uses a multi-agent architecture with specialized agents for research planning, execution, and report generation.

## Development Commands

### Backend (Python/FastAPI)
```bash
# Start the FastAPI server
python -m uvicorn main:app --reload

# Run Python tests
python -m pytest

# Install Python dependencies
pip install -r requirements.txt

# Run a single test
python -m pytest tests/test_specific.py::TestClass::test_method

# Quick research test
python quick-test.py
```

### Frontend (Next.js)
```bash
# Navigate to frontend directory first
cd frontend/nextjs

# Start development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Start production server
npm start
```

### Docker Operations
```bash
# Start all services
docker-compose up --build

# Run without rebuild
docker compose up

# Run tests in container
docker-compose run gpt-researcher-tests
```

### Playwright Testing
```bash
# Run Playwright tests
npm test

# Run with UI
npm run test:ui

# Debug mode
npm run test:debug

# Show test report
npm run test:report
```

## Architecture Overview

### Core Research Flow
1. **Entry Point**: User query enters through CLI (`cli.py`) or web interface
2. **Research Initialization**: `GPTResearcher` class (`gpt_researcher/agent.py`) orchestrates the research
3. **Query Processing**: Research questions are generated and distributed
4. **Information Gathering**: Multiple retrieval methods fetch relevant data
5. **Report Generation**: Collected information is synthesized into structured reports
6. **Output Delivery**: Reports are formatted and delivered via WebSocket or direct response

### Multi-Agent System
The system uses specialized agents coordinated by a `ChiefEditorAgent`:
- **Researcher**: Gathers information from various sources
- **Writer**: Creates initial report drafts
- **Editor**: Refines and structures content
- **Reviewer**: Validates accuracy and completeness
- **Reviser**: Makes final improvements
- **Publisher**: Formats final output

### Key Components
- **gpt_researcher/**: Core research logic and agent implementations
- **multi_agents/**: LangGraph-based multi-agent orchestration
- **backend/**: FastAPI server and report generation
- **frontend/**: Next.js user interface with real-time WebSocket updates

### Communication Architecture
- **WebSocket Protocol**: Real-time streaming of research progress
- **Event Types**: logs, report, sources, content, path
- **Async Processing**: Non-blocking research execution
- **State Management**: Context preservation across research phases

## Environment Configuration

Required environment variables:
```bash
# LLM Configuration
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here  # For web search

# Optional configurations
DOC_PATH=./my-docs  # For local document research
RETRIEVER=tavily,mcp  # Enable hybrid retrieval
```

## Testing Strategy

### Running Tests
```bash
# Backend tests
python -m pytest tests/

# Frontend tests (from frontend/nextjs)
npm test

# E2E Playwright tests
npm run test:headed  # See browser interactions
```

### Test Coverage Areas
- Unit tests for individual components
- Integration tests for agent interactions
- End-to-end research workflow tests
- WebSocket communication tests

## Code Quality Standards

### Python Code
- Follow PEP 8 conventions
- Use type hints for function signatures
- Async/await for I/O operations
- Error handling with try/except blocks

### TypeScript/JavaScript
- Strict TypeScript mode enabled
- ESLint and Prettier configurations enforced
- React hooks best practices
- Tailwind CSS for styling

## Common Development Tasks

### Adding a New Research Agent
1. Create agent class in `multi_agents/agents/`
2. Implement required methods (run, review_task)
3. Register in agent factory
4. Update workflow in chief editor

### Modifying Report Templates
1. Templates located in `backend/report_type/`
2. Use Jinja2 templating syntax
3. Update corresponding report generator

### Adding New Retrieval Method
1. Implement retriever in `gpt_researcher/retrievers/`
2. Add to retriever factory in `gpt_researcher/actions/retriever.py`
3. Update configuration options
4. Add to `__init__.py` in retrievers module

### LinkedIn Sales Navigator Integration
The system supports LinkedIn Sales Navigator as a data source for finding leads and companies. Uses cookie-based authentication for reliable access.

**Quick Setup:**
1. Extract LinkedIn cookies (includes httpOnly `li_at` token):
   ```bash
   node extract_cookies_playwright.js
   ```
   This opens a browser for manual login and 2FA, then extracts ALL cookies.

2. Enable LinkedIn retriever in `.env`:
   ```bash
   RETRIEVER=tavily,linkedin
   ```

**Cookie Extraction Details:**
- Uses Playwright's `context.cookies()` to extract httpOnly cookies
- Handles 2FA authentication flow interactively
- Saves cookies to multiple formats:
  - `linkedin_cookies_complete_nodejs.json` - Full cookie data
  - `linkedin_docker_cookies.json` - Docker-ready format
  - `li_at_token.txt` - Just the authentication token

**Features:**
- Searches for leads (people) and companies
- Filters by location, company size, job function, seniority
- Multi-language support (including Ukrainian)
- Returns structured data with profiles and contact info

**Technical Implementation:**
- Cookie-based authentication (more reliable than password login)
- Playwright for cookie extraction (Node.js)
- Selenium WebDriver for data retrieval (Python)
- Automatic rate limiting and session management
- Cookies valid for ~1 year (re-extract when expired)

**Documentation:**
See `docs/LINKEDIN_SETUP.md` for comprehensive setup and troubleshooting guide.

## Performance Considerations

- Use parallel processing for multiple research queries
- Implement caching for frequently accessed sources
- Stream responses to frontend for better UX
- Monitor token usage for cost optimization
- Use vector stores for efficient similarity search

## Security Notes

- Never commit API keys or secrets
- Validate all user inputs
- Sanitize HTML content before rendering
- Use environment variables for sensitive configuration
- Implement rate limiting for API endpoints
- always use dockerized setup to test anything
- use serena when possible
- for testing use playwright -> localhost:3000