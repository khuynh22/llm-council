# LLM Council - AI Coding Agent Instructions

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer questions via OpenRouter. Think "ChatGPT but with a panel of experts who debate and synthesize answers."

**Available in Two Modes:**
1. **Web Application**: Interactive React UI with FastAPI backend
2. **MCP Server**: Model Context Protocol server for Claude Desktop, VS Code, etc.

**Core Flow:**
1. **Stage 1**: Parallel queries to all council models (defined in [backend/config.py](../backend/config.py))
2. **Stage 2**: Each model ranks anonymized responses (prevents favoritism)
3. **Stage 3**: Chairman model synthesizes final answer from all inputs + rankings

## Critical Architecture Decisions

### Anonymization Strategy
- Stage 2 uses "Response A", "Response B" labels to prevent model bias
- Backend creates `label_to_model` mapping for de-anonymization
- Frontend displays real model names **client-side** in bold (e.g., "**gpt-5.1**")
- This is intentional: models judge anonymously, users see transparently

### Metadata NOT Persisted
Key gotcha: `label_to_model` and `aggregate_rankings` are computed per-request but **NOT saved to JSON**. They exist only in API responses and frontend state. See [backend/main.py](../backend/main.py) POST endpoint and [backend/storage.py](../backend/storage.py).

### Port Configuration
Backend runs on **port 8001** (not 8000). This was a deliberate user choice due to port conflicts. CORS allows localhost:5173 (Vite) and localhost:3000.

## Development Workflow

### Running the App
```bash
# Web App: Use start script
./start.sh

# Web App: Manual (two terminals)
# Terminal 1: uv run llm-council-web
# Terminal 2: cd frontend && npm run dev

# MCP Server: For Claude Desktop / VS Code
uv run llm-council-mcp
```

### Dependencies
- **Backend**: `uv sync` (Python 3.10+, FastAPI, httpx)
- **Frontend**: `cd frontend && npm install` (React 19, Vite, react-markdown)

### Environment Setup
Create `.env` in root with:
```
OPENROUTER_API_KEY=sk-or-v1-...
```

## Code Patterns & Conventions

### MCP Server Architecture (backend/mcp_server.py)
The MCP server exposes council deliberation as tools and resources:
- **Tools**: `council_query`, `council_stage1`, `council_list_conversations`, `council_get_conversation`
- **Resources**: `council://conversations/{id}` for accessing saved deliberations
- **Progress Notifications**: Uses MCP's `send_log_message` to report stage progress
- **Stateful**: Reuses existing [backend/storage.py](../backend/storage.py) for conversation persistence
- **Model Customization**: Tools accept optional `council_models` and `chairman_model` parameters to override [backend/config.py](../backend/config.py) defaults

### Stage 2 Prompt Format (Strict Parsing)
See [backend/council.py](../backend/council.py) `stage2_collect_rankings()`. The prompt enforces:
```
FINAL RANKING:
1. Response C
2. Response A
```
No extra text after ranking. This enables `parse_ranking_from_text()` to reliably extract results.

### Async Parallelism
All model queries use `asyncio.gather()` for speed. See [backend/openrouter.py](../backend/openrouter.py) `query_models_parallel()`.

### Graceful Degradation
If a model fails in Stage 1, continue with successful responses. Returns `None` on failure, filters before proceeding.

### React Component Structure
- [frontend/src/App.jsx](../frontend/src/App.jsx): Conversation orchestration
- [frontend/src/components/Stage1.jsx](../frontend/src/components/Stage1.jsx): Tab view of individual responses
- [frontend/src/components/Stage2.jsx](../frontend/src/components/Stage2.jsx): Peer rankings + aggregate scores ("Street Cred")
- [frontend/src/components/Stage3.jsx](../frontend/src/components/Stage3.jsx): Final synthesized answer (green background #f0fff0)

### Styling
- **Light mode** theme (not dark mode)
- Primary blue: #4a90e2
- All markdown wrapped in `.markdown-content` class with 12px padding (prevents cluttered look)
- See [frontend/src/index.css](../frontend/src/index.css) for global markdown styles

## Common Tasks

### Changing Council Models
Edit [backend/config.py](../backend/config.py) `COUNCIL_MODELS` and `CHAIRMAN_MODEL`. Use OpenRouter model identifiers (e.g., "anthropic/claude-sonnet-4.5").

### Adding a New Stage
1. Add async function to [backend/council.py](../backend/council.py)
2. Update [backend/main.py](../backend/main.py) POST endpoint to call it
3. Add response data to storage schema if persisting (else just return via API)
4. Create React component in [frontend/src/components/](../frontend/src/components/)
5. Import and render in [frontend/src/components/ChatInterface.jsx](../frontend/src/components/ChatInterface.jsx)

### Debugging API Responses
Check [backend/main.py](../backend/main.py) POST `/api/conversations/{id}/message`. Returns full response with `stage1`, `stage2`, `stage3` + metadata. Frontend stores metadata in state but backend doesn't persist it.

## Project Philosophy

Per [README.md](../README.md): "99% vibe coded as a fun Saturday hack." This means:
- Prioritize working code over perfect architecture
- Code is meant to be ephemeral - customize freely
- No long-term support planned
- JSON file storage is intentionally simple (not a database)

When making changes, maintain the spirit: fast iterations, clear stage boundaries, and transparent multi-LLM deliberation.
