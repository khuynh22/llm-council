# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council".

**Now available as both a web app AND an MCP server!**

- **Web App:** Interactive UI that looks like ChatGPT but runs multi-model deliberation
- **MCP Server:** Use LLM Council directly in Claude Desktop, VS Code, or any MCP client

## How It Works

This repo uses OpenRouter to send your query to multiple LLMs, asks them to review and rank each other's work, and produces a final synthesized response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Usage Modes

LLM Council can be used in **two ways**:

### 1. Web Application (Original)
Interactive web UI with chat interface, conversation history, and visual stage display.

### 2. MCP Server (NEW!)
Use LLM Council as a Model Context Protocol server in Claude Desktop, VS Code, or any MCP-compatible client.

## MCP Server Setup

The MCP server exposes LLM Council's deliberation capabilities as tools that can be called from MCP clients.

### Installation

1. **Install dependencies:**
```bash
uv sync
```

2. **Set up your OpenRouter API key:**

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-actual-key
```

3. **Test the MCP server:**
```bash
uv run llm-council-mcp
```

### Configure Claude Desktop

Add this to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "llm-council": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\llm-council", "run", "llm-council-mcp"],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-your-actual-key"
      }
    }
  }
}
```

**Important:** Replace `C:\\path\\to\\llm-council` with the actual absolute path to your LLM Council directory. Use forward slashes (`/`) on macOS/Linux and double backslashes (`\\`) on Windows.

### Configure VS Code

Add this to your VS Code settings (`.vscode/settings.json` or User Settings):

```json
{
  "mcp.servers": {
    "llm-council": {
      "command": "uv",
      "args": ["--directory", "/path/to/llm-council", "run", "llm-council-mcp"],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-your-actual-key"
      }
    }
  }
}
```

### Available MCP Tools

Once configured, you can use these tools in your MCP client:

1. **`council_query`** - Run a full 3-stage deliberation
   - **Parameters:**
     - `question` (required): The question to ask
     - `council_models` (optional): List of OpenRouter model IDs (overrides config defaults)
     - `chairman_model` (optional): Chairman model ID (overrides config default)
     - `save_conversation` (optional): Whether to save to history (default: true)
   - **Returns:** Complete deliberation with all 3 stages, rankings, and metadata

2. **`council_stage1`** - Run only Stage 1 (individual responses)
   - **Parameters:**
     - `question` (required): The question to ask
     - `council_models` (optional): List of model IDs
   - **Returns:** Just the individual model responses (faster, skips ranking/synthesis)

3. **`council_list_conversations`** - List all saved conversations

4. **`council_get_conversation`** - Retrieve a specific conversation by ID

### Available MCP Resources

Access past deliberations as resources:

- `council://conversations/{id}` - Full conversation with all messages and stages

### Example Usage in Claude Desktop

Once configured, you can ask Claude:

> "Use the council_query tool to ask: What are the implications of quantum computing for cryptography?"

Claude will invoke the LLM Council and present the full 3-stage deliberation.

### Customizing Models

You can override the default council models in your query:

> "Use council_query with custom models: ['openai/gpt-4', 'anthropic/claude-3-opus', 'google/gemini-pro'] to answer: What is consciousness?"

## Web Application Setup

### 1. Install Dependencies

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root (or copy from `.env.example`):

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

## Running the Web Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run llm-council-web
# or: uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API, MCP SDK
- **Frontend:** React + Vite, react-markdown for rendering
- **MCP Server:** Model Context Protocol for tool integration
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
