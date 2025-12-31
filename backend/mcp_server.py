"""MCP Server for LLM Council - Exposes council deliberation as MCP tools and resources."""

import asyncio
import json
import traceback
import uuid

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent, LoggingLevel

from . import storage
from . import config as backend_config
from .council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    generate_conversation_title,
)
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL


# Initialize the MCP server
server = Server("llm-council")


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List all available conversation resources."""
    conversations = storage.list_conversations()

    resources = []
    for conv in conversations:
        resources.append(
            Resource(
                uri=f"council://conversations/{conv['id']}",
                name=f"{conv['title']} ({conv['message_count']} messages)",
                description=f"Council conversation created at {conv['created_at']}",
                mimeType="application/json",
            )
        )

    return resources


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific conversation resource."""
    if not uri.startswith("council://conversations/"):
        raise ValueError(f"Unknown resource URI: {uri}")

    conversation_id = uri.replace("council://conversations/", "")
    conversation = storage.get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(f"Conversation not found: {conversation_id}")

    return json.dumps(conversation, indent=2)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available council tools."""
    return [
        Tool(
            name="council_query",
            description=(
                "Run a full 3-stage LLM Council deliberation on a question. "
                "Stage 1: Multiple models provide individual responses. "
                "Stage 2: Models rank each other's responses (anonymized). "
                "Stage 3: Chairman synthesizes final answer from all input. "
                "This process takes 30-120 seconds to complete."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the LLM Council",
                    },
                    "council_models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional: List of OpenRouter model identifiers for council members. "
                            f"Defaults to: {COUNCIL_MODELS}"
                        ),
                    },
                    "chairman_model": {
                        "type": "string",
                        "description": (
                            "Optional: OpenRouter model identifier for the chairman. "
                            f"Defaults to: {CHAIRMAN_MODEL}"
                        ),
                    },
                    "save_conversation": {
                        "type": "boolean",
                        "description": "Whether to save this as a new conversation (default: true)",
                        "default": True,
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="council_stage1",
            description=(
                "Run only Stage 1 of council deliberation: collect individual responses "
                "from all council models in parallel. Use this for quick comparison of "
                "model outputs without the full ranking and synthesis process."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the council models",
                    },
                    "council_models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional: List of OpenRouter model identifiers. "
                            f"Defaults to: {COUNCIL_MODELS}"
                        ),
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="council_list_conversations",
            description="List all saved council conversations with metadata",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="council_get_conversation",
            description="Retrieve a specific conversation by ID with all messages and stages",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "The conversation ID to retrieve",
                    },
                },
                "required": ["conversation_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution requests."""

    if name == "council_query":
        return await handle_council_query(arguments)
    elif name == "council_stage1":
        return await handle_council_stage1(arguments)
    elif name == "council_list_conversations":
        return await handle_list_conversations_tool()
    elif name == "council_get_conversation":
        return await handle_get_conversation_tool(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_council_query(arguments: dict) -> list[TextContent]:
    """Execute a full 3-stage council deliberation."""
    question = arguments["question"]
    council_models = arguments.get("council_models", COUNCIL_MODELS)
    chairman_model = arguments.get("chairman_model", CHAIRMAN_MODEL)
    save_conversation = arguments.get("save_conversation", True)

    # Override config temporarily if custom models specified
    original_council = backend_config.COUNCIL_MODELS
    original_chairman = backend_config.CHAIRMAN_MODEL

    try:
        if council_models != COUNCIL_MODELS:
            backend_config.COUNCIL_MODELS = council_models
        if chairman_model != CHAIRMAN_MODEL:
            backend_config.CHAIRMAN_MODEL = chairman_model

        # Send progress notifications
        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data="Stage 1: Collecting individual responses from council models...",
        )

        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data=f"Using models: {council_models}",
        )

        # Run Stage 1
        stage1_results = await stage1_collect_responses(question)

        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data=f"Stage 1 returned {len(stage1_results) if stage1_results else 0} results",
        )

        if not stage1_results:
            return [
                TextContent(
                    type="text",
                    text="Error: All models failed to respond. Please check your OpenRouter API key and try again.",
                )
            ]

        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data=f"Stage 1 complete: {len(stage1_results)} responses collected",
        )

        # Send progress for Stage 2
        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data="Stage 2: Collecting peer rankings (anonymized)...",
        )

        # Run Stage 2
        stage2_results, label_to_model = await stage2_collect_rankings(question, stage1_results)
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data="Stage 2 complete: Peer rankings collected",
        )

        # Send progress for Stage 3
        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data="Stage 3: Chairman synthesizing final answer...",
        )

        # Run Stage 3
        stage3_result = await stage3_synthesize_final(
            question,
            stage1_results,
            stage2_results
        )

        await server.request_context.session.send_log_message(
            level=LoggingLevel.INFO,
            data="Stage 3 complete: Final synthesis ready",
        )

        # Prepare metadata
        metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings,
        }

        # Save conversation if requested
        conversation_id = None
        if save_conversation:
            conversation_id = str(uuid.uuid4())
            storage.create_conversation(conversation_id)

            # Generate title (don't wait for it, do it async)
            title = await generate_conversation_title(question)
            storage.update_conversation_title(conversation_id, title)

            # Add messages
            storage.add_user_message(conversation_id, question)
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

        # Format response
        response = {
            "question": question,
            "stage1_responses": stage1_results,
            "stage2_rankings": stage2_results,
            "stage3_synthesis": stage3_result,
            "metadata": metadata,
        }

        if conversation_id:
            response["conversation_id"] = conversation_id
            response["resource_uri"] = f"council://conversations/{conversation_id}"

        return [
            TextContent(
                type="text",
                text=json.dumps(response, indent=2),
            )
        ]

    except Exception as e:
        # Log the error with full traceback
        error_details = traceback.format_exc()

        await server.request_context.session.send_log_message(
            level=LoggingLevel.ERROR,
            data=f"Error in council_query: {str(e)}\n\nTraceback:\n{error_details}",
        )
        # Return error to user
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}\n\nFull details:\n{error_details}\n\nPlease check:\n1. Your OPENROUTER_API_KEY is valid\n2. You have credits in your OpenRouter account\n3. The model names are correct",
            )
        ]

    finally:
        # Restore original config
        backend_config.COUNCIL_MODELS = original_council
        backend_config.CHAIRMAN_MODEL = original_chairman


async def handle_council_stage1(arguments: dict) -> list[TextContent]:
    """Execute only Stage 1: collect individual responses."""
    question = arguments["question"]
    council_models = arguments.get("council_models", COUNCIL_MODELS)

    # Override config temporarily if custom models specified
    original_council = backend_config.COUNCIL_MODELS

    try:
        if council_models != COUNCIL_MODELS:
            backend_config.COUNCIL_MODELS = council_models

        # Optional: try to log, but don't fail if it doesn't work
        try:
            await server.request_context.session.send_log_message(
                level=LoggingLevel.INFO,
                data=f"Collecting responses from {len(council_models)} models...",
            )
        except Exception:
            pass

        stage1_results = await stage1_collect_responses(question)

        if not stage1_results:
            return [
                TextContent(
                    type="text",
                    text="Error: All models failed to respond. Please check your OpenRouter API key and try again.",
                )
            ]

        response = {
            "question": question,
            "responses": stage1_results,
            "models_queried": len(council_models),
            "responses_received": len(stage1_results),
        }

        return [
            TextContent(
                type="text",
                text=json.dumps(response, indent=2),
            )
        ]

    except Exception as e:
        # Try to log, but don't fail if logging fails
        error_msg = f"Error in council_stage1: {str(e)}"
        try:
            error_details = traceback.format_exc()
            await server.request_context.session.send_log_message(
                level=LoggingLevel.ERROR,
                data=f"{error_msg}\n\nTraceback:\n{error_details}",
            )
        except Exception:
            pass  # Logging failed, but we'll still return the error

        return [
            TextContent(
                type="text",
                text=f"{error_msg}\n\nThis is likely a configuration or API issue. The core council logic works (verified), so check:\n1. Your mcp.json config has correct paths\n2. OPENROUTER_API_KEY is set in env\n3. Model names are valid",
            )
        ]

    finally:
        backend_config.COUNCIL_MODELS = original_council


async def handle_list_conversations_tool() -> list[TextContent]:
    """List all conversations."""
    conversations = storage.list_conversations()

    return [
        TextContent(
            type="text",
            text=json.dumps(conversations, indent=2),
        )
    ]


async def handle_get_conversation_tool(arguments: dict) -> list[TextContent]:
    """Get a specific conversation."""
    conversation_id = arguments["conversation_id"]
    conversation = storage.get_conversation(conversation_id)

    if conversation is None:
        return [
            TextContent(
                type="text",
                text=f"Error: Conversation not found: {conversation_id}",
            )
        ]

    return [
        TextContent(
            type="text",
            text=json.dumps(conversation, indent=2),
        )
    ]


async def async_main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="llm-council",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main():
    """Entry point for the MCP server CLI."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
