#!/usr/bin/env python3
"""
MCP Council Server - Multi-LLM Council for Claude Code

This MCP server provides Claude Code with access to an LLM council
that can consult multiple models for complex decisions.

Usage:
    1. Add to Claude Code settings (~/.claude/settings.json):
       {
         "mcpServers": {
           "council": {
             "command": "python",
             "args": ["/path/to/mcp_council_server.py"],
             "env": {
               "OPENAI_API_KEY": "sk-...",
               "ANTHROPIC_API_KEY": "sk-ant-...",
               "GOOGLE_API_KEY": "AIza..."
             }
           }
         }
       }

    2. Restart Claude Code
    3. Use: "Ask the council to review this code"
"""

import os
import json
import asyncio
import concurrent.futures
from typing import Any

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# LLM Clients
from openai import OpenAI
import anthropic
from dotenv import load_dotenv

try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

load_dotenv(override=True)

# Initialize server
server = Server("council")

# LLM Clients
openai_client = None
anthropic_client = None
google_client = None

def init_clients():
    """Initialize LLM clients."""
    global openai_client, anthropic_client, google_client

    if os.getenv("OPENAI_API_KEY"):
        openai_client = OpenAI()
    if os.getenv("ANTHROPIC_API_KEY"):
        anthropic_client = anthropic.Anthropic()
    if GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def call_openai(prompt: str, system: str) -> dict:
    """Call OpenAI o3."""
    if not openai_client:
        return {"model": "o3", "response": None, "error": "Not configured"}
    try:
        response = openai_client.chat.completions.create(
            model="o3",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
        )
        return {
            "model": "o3 (OpenAI)",
            "response": response.choices[0].message.content,
            "error": None
        }
    except Exception as e:
        return {"model": "o3 (OpenAI)", "response": None, "error": str(e)}


def call_anthropic(prompt: str, system: str) -> dict:
    """Call Claude Opus 4."""
    if not anthropic_client:
        return {"model": "Claude Opus 4", "response": None, "error": "Not configured"}
    try:
        response = anthropic_client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "model": "Claude Opus 4 (Anthropic)",
            "response": response.content[0].text,
            "error": None
        }
    except Exception as e:
        return {"model": "Claude Opus 4 (Anthropic)", "response": None, "error": str(e)}


def call_google(prompt: str, system: str) -> dict:
    """Call Gemini 2.5 Pro."""
    if not google_client:
        return {"model": "Gemini 2.5 Pro", "response": None, "error": "Not configured"}
    try:
        full_prompt = f"{system}\n\n{prompt}"
        response = google_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=full_prompt,
        )
        return {
            "model": "Gemini 2.5 Pro (Google)",
            "response": response.text,
            "error": None
        }
    except Exception as e:
        return {"model": "Gemini 2.5 Pro (Google)", "response": None, "error": str(e)}


def aggregate_responses(task: str, responses: list) -> str:
    """Use Claude Opus 4 to aggregate council responses."""
    successful = [r for r in responses if r["response"]]

    if not successful:
        return "Error: No successful responses from council members"

    if len(successful) == 1:
        return f"**{successful[0]['model']}:**\n\n{successful[0]['response']}"

    # Build aggregation prompt
    responses_text = "\n\n".join([
        f"=== {r['model']} ===\n{r['response']}"
        for r in successful
    ])

    aggregation_prompt = f"""You are synthesizing responses from multiple AI models about: {task}

RESPONSES FROM COUNCIL:
{responses_text}

INSTRUCTIONS:
1. Identify the key insights from each response
2. Note any disagreements or different perspectives
3. Synthesize the best elements into a comprehensive answer
4. If there are conflicts, explain the trade-offs

Provide a clear, actionable synthesis."""

    if anthropic_client:
        try:
            response = anthropic_client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=8192,
                messages=[{"role": "user", "content": aggregation_prompt}],
            )
            return response.content[0].text
        except:
            pass

    # Fallback: return all responses
    return responses_text


def run_council(task: str, context: str, council_type: str) -> str:
    """Run the LLM council for a task."""

    # Define system prompts based on council type
    system_prompts = {
        "code_review": """You are an expert code reviewer. Analyze the code for:
- Security vulnerabilities (injection, XSS, auth issues)
- Performance problems (N+1 queries, memory leaks, inefficiencies)
- Code quality (readability, maintainability, SOLID principles)
- Best practices and potential improvements
Be specific and actionable.""",

        "architecture": """You are a senior software architect. Evaluate the architecture for:
- Scalability and performance characteristics
- Maintainability and separation of concerns
- Security considerations
- Trade-offs between different approaches
Provide concrete recommendations.""",

        "debug": """You are an expert debugger. Help identify:
- Root cause of the issue
- Potential failure modes
- Edge cases that might cause problems
- Step-by-step debugging approach
Think systematically through the problem.""",

        "security": """You are a security expert. Perform a security audit:
- OWASP Top 10 vulnerabilities
- Authentication/authorization issues
- Data validation and sanitization
- Secrets management
- Attack surface analysis
Prioritize findings by severity.""",

        "refactor": """You are a refactoring expert. Suggest improvements for:
- Code organization and structure
- Design patterns that could help
- Reducing complexity and duplication
- Improving testability
Provide specific refactoring steps.""",

        "general": """You are a helpful AI assistant participating in a council of experts.
Provide your best analysis and recommendations for the given task.
Be thorough, specific, and actionable."""
    }

    system = system_prompts.get(council_type, system_prompts["general"])
    prompt = f"{task}\n\nContext/Code:\n{context}" if context else task

    # Call all models in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(call_openai, prompt, system),
            executor.submit(call_anthropic, prompt, system),
            executor.submit(call_google, prompt, system),
        ]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Aggregate responses
    result = aggregate_responses(task, responses)

    # Build final output
    output_parts = ["# Council Decision\n"]

    # Show which models responded
    status = []
    for r in responses:
        if r["error"]:
            status.append(f"- {r['model']}: Error - {r['error']}")
        else:
            status.append(f"- {r['model']}: OK")

    output_parts.append("## Council Members\n" + "\n".join(status) + "\n")
    output_parts.append("## Synthesized Response\n" + result)

    return "\n".join(output_parts)


# Define MCP Tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available council tools."""
    return [
        Tool(
            name="council_review",
            description="Get a code review from the LLM council (o3 + Claude Opus 4 + Gemini 2.5 Pro). Use for reviewing code quality, security, and best practices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code to review"},
                    "focus": {"type": "string", "description": "Optional: specific focus area (security, performance, style)"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="council_architecture",
            description="Get architecture advice from the LLM council. Use for system design decisions, technology choices, and architectural trade-offs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The architecture question or decision"},
                    "context": {"type": "string", "description": "Relevant context about the system"}
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="council_debug",
            description="Get debugging help from the LLM council. Use for complex bugs where multiple perspectives would help.",
            inputSchema={
                "type": "object",
                "properties": {
                    "problem": {"type": "string", "description": "Description of the bug/problem"},
                    "code": {"type": "string", "description": "Relevant code"},
                    "error": {"type": "string", "description": "Error message if any"}
                },
                "required": ["problem"]
            }
        ),
        Tool(
            name="council_security",
            description="Get a security audit from the LLM council. Use for identifying vulnerabilities and security best practices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code to audit"},
                    "context": {"type": "string", "description": "Context about the application (web app, API, etc.)"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="council_refactor",
            description="Get refactoring suggestions from the LLM council. Use for improving code structure and design.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code to refactor"},
                    "goals": {"type": "string", "description": "Refactoring goals (simplify, modularize, etc.)"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="council_ask",
            description="Ask a general question to the LLM council. Use for complex decisions that benefit from multiple AI perspectives.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask"},
                    "context": {"type": "string", "description": "Additional context"}
                },
                "required": ["question"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "council_review":
        code = arguments.get("code", "")
        focus = arguments.get("focus", "")
        task = f"Review this code" + (f" with focus on {focus}" if focus else "")
        result = run_council(task, code, "code_review")

    elif name == "council_architecture":
        question = arguments.get("question", "")
        context = arguments.get("context", "")
        result = run_council(question, context, "architecture")

    elif name == "council_debug":
        problem = arguments.get("problem", "")
        code = arguments.get("code", "")
        error = arguments.get("error", "")
        context = f"Code:\n{code}\n\nError:\n{error}" if code or error else ""
        result = run_council(problem, context, "debug")

    elif name == "council_security":
        code = arguments.get("code", "")
        context = arguments.get("context", "")
        task = "Perform a security audit on this code"
        full_context = f"{context}\n\nCode:\n{code}" if context else code
        result = run_council(task, full_context, "security")

    elif name == "council_refactor":
        code = arguments.get("code", "")
        goals = arguments.get("goals", "improve code quality")
        task = f"Suggest refactoring to {goals}"
        result = run_council(task, code, "refactor")

    elif name == "council_ask":
        question = arguments.get("question", "")
        context = arguments.get("context", "")
        result = run_council(question, context, "general")

    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


async def main():
    """Run the MCP server."""
    init_clients()

    # Report available models
    models = []
    if openai_client:
        models.append("o3")
    if anthropic_client:
        models.append("Claude Opus 4")
    if google_client:
        models.append("Gemini 2.5 Pro")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
