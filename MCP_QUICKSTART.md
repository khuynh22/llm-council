# LLM Council MCP Server - Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure your API key:**

   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
   ```

3. **Test the server:**
   ```bash
   uv run llm-council-mcp
   ```

   The server will start and wait for JSON-RPC input (this is normal - MCP clients communicate via stdin/stdout).

## Claude Desktop Configuration

Add this to your Claude Desktop config:

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

**Important:** Replace `C:\\path\\to\\llm-council` with the actual path to this directory.
- Windows: Use double backslashes `C:\\src\\llm-council`
- macOS/Linux: Use forward slashes `/Users/you/llm-council`

## VS Code Configuration

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

## Usage Examples

Once configured, you can use these tools in your MCP client:

### 1. Full Council Query

In Claude Desktop, ask:

> "Use the council_query tool to answer: What are the key differences between supervised and unsupervised learning?"

This will:
- Stage 1: Get responses from all 4 council models
- Stage 2: Each model ranks the others' responses (anonymized)
- Stage 3: Chairman synthesizes the final answer
- Save the conversation to history

### 2. Quick Model Comparison (Stage 1 Only)

> "Use council_stage1 to compare how different models explain recursion"

This skips ranking and synthesis for faster results.

### 3. Custom Models

> "Use council_query with these models: ['openai/gpt-4', 'anthropic/claude-3-opus', 'google/gemini-pro'] to answer: What is the future of quantum computing?"

### 4. Access Past Conversations

> "List all my saved council conversations using council_list_conversations"

> "Show me the full details of conversation ID abc-123 using council_get_conversation"

## Available Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `council_query` | Full 3-stage deliberation | `question`, `council_models` (optional), `chairman_model` (optional), `save_conversation` (default: true) |
| `council_stage1` | Individual responses only | `question`, `council_models` (optional) |
| `council_list_conversations` | List all saved conversations | None |
| `council_get_conversation` | Get conversation details | `conversation_id` |

## Available Resources

- `council://conversations/{id}` - Access any saved conversation as a resource

## Customizing Default Models

Edit `backend/config.py` to change the default council members:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

These can be overridden per-query using tool parameters.

## Troubleshooting

### Server doesn't start
- Check that your `.env` file exists with a valid `OPENROUTER_API_KEY`
- Verify dependencies are installed: `uv sync`
- Test imports: `uv run python -c "from backend.mcp_server import main; print('OK')"`

### No response from tools
- Council queries take 30-120 seconds to complete (multiple LLM calls)
- Check OpenRouter API key has sufficient credits
- Look for progress notifications in your MCP client logs

### Permission errors on Windows
- Ensure the path in config uses double backslashes: `C:\\src\\llm-council`
- Run VS Code or Claude Desktop with appropriate permissions

## Cost Considerations

Each `council_query` makes 9 LLM API calls:
- Stage 1: 4 council models in parallel
- Stage 2: 4 models ranking in parallel
- Stage 3: 1 chairman model

Using cheaper models or `council_stage1` can reduce costs.
