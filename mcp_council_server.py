#!/usr/bin/env python3
"""
MCP Council Server - Multi-LLM Council for Claude Code

Calls GPT-5.4, Claude Opus 4.7, and Gemini 3 Pro in parallel. Returns the
three raw responses to Claude Code, which does the synthesis step itself.
Optional `council_research_*` variants enable web search on all three
providers.

Usage:
    Add to Claude Code settings (~/.claude/settings.json):
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

    Then in any session: "Ask the council to review this code"
"""

import os
import asyncio
import concurrent.futures
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from openai import OpenAI
import anthropic
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types as genai_types
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

load_dotenv(override=True)

server = Server("council")

openai_client = None
anthropic_client = None
google_client = None

# Current model IDs. Update here when providers ship newer flagships.
MODEL_OPENAI = "gpt-5.4"
MODEL_ANTHROPIC = "claude-opus-4-7"
MODEL_GOOGLE = "gemini-3-pro-preview"

# Web-search caps (per call) when research variants are used.
WEB_SEARCH_MAX_USES = 4


def init_clients():
    """Initialize LLM clients from environment variables."""
    global openai_client, anthropic_client, google_client

    if os.getenv("OPENAI_API_KEY"):
        openai_client = OpenAI()
    if os.getenv("ANTHROPIC_API_KEY"):
        anthropic_client = anthropic.Anthropic()
    if GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# ---------- Model callers ----------

def call_openai(prompt: str, system: str, *, web_search: bool = False) -> dict:
    """Call OpenAI GPT-5.4. Uses Responses API when web_search is on."""
    label = f"GPT-5.4 (OpenAI{'  +web' if web_search else ''})"
    if not openai_client:
        return {"model": label, "response": None, "error": "Not configured"}
    try:
        if web_search:
            # Responses API supports the hosted web_search tool.
            r = openai_client.responses.create(
                model=MODEL_OPENAI,
                tools=[{"type": "web_search"}],
                instructions=system,
                input=prompt,
            )
            text = getattr(r, "output_text", None) or ""
        else:
            r = openai_client.chat.completions.create(
                model=MODEL_OPENAI,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )
            text = r.choices[0].message.content or ""
        return {"model": label, "response": text.strip(), "error": None}
    except Exception as e:
        return {"model": label, "response": None, "error": str(e)}


def call_anthropic(prompt: str, system: str, *, web_search: bool = False) -> dict:
    """Call Claude Opus 4.7. Enables server-side web_search tool when requested."""
    label = f"Claude Opus 4.7 (Anthropic{'  +web' if web_search else ''})"
    if not anthropic_client:
        return {"model": label, "response": None, "error": "Not configured"}
    try:
        kwargs = {
            "model": MODEL_ANTHROPIC,
            "max_tokens": 8192,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if web_search:
            kwargs["tools"] = [{
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": WEB_SEARCH_MAX_USES,
            }]
        r = anthropic_client.messages.create(**kwargs)
        # Concatenate all text blocks (server-tool blocks return no text).
        chunks = [b.text for b in r.content if getattr(b, "type", None) == "text"]
        text = "\n".join(c for c in chunks if c).strip()
        return {"model": label, "response": text, "error": None}
    except Exception as e:
        return {"model": label, "response": None, "error": str(e)}


def call_google(prompt: str, system: str, *, web_search: bool = False) -> dict:
    """Call Gemini 3 Pro. Adds google_search grounding when requested."""
    label = f"Gemini 3 Pro (Google{'  +web' if web_search else ''})"
    if not google_client:
        return {"model": label, "response": None, "error": "Not configured"}
    try:
        full_prompt = f"{system}\n\n{prompt}"
        config = None
        if web_search:
            config = genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        r = google_client.models.generate_content(
            model=MODEL_GOOGLE,
            contents=full_prompt,
            config=config,
        )
        return {"model": label, "response": (r.text or "").strip(), "error": None}
    except Exception as e:
        return {"model": label, "response": None, "error": str(e)}


# ---------- Council orchestration ----------

SYSTEM_PROMPTS = {
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
Be thorough, specific, and actionable.""",
}


def run_council(task: str, context: str, council_type: str, *, web_search: bool = False) -> str:
    """Run all three models in parallel and return their raw responses.

    Claude Code (the calling session) is expected to synthesize these into
    a single recommendation. No server-side aggregation.
    """
    system = SYSTEM_PROMPTS.get(council_type, SYSTEM_PROMPTS["general"])
    if web_search:
        system += (
            "\n\nYou have access to live web search. Use it to verify versions, "
            "prices, recent changes, and anything that may have shifted since "
            "your training cutoff. Cite concrete sources in your response."
        )
    prompt = f"{task}\n\nContext/Code:\n{context}" if context else task

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(call_openai, prompt, system, web_search=web_search),
            executor.submit(call_anthropic, prompt, system, web_search=web_search),
            executor.submit(call_google, prompt, system, web_search=web_search),
        ]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Deterministic order in output: OpenAI, Anthropic, Google.
    order = {"GPT-5.4 (OpenAI": 0, "Claude Opus 4.7 (Anthropic": 1, "Gemini 3 Pro (Google": 2}
    responses.sort(key=lambda r: next((v for k, v in order.items() if r["model"].startswith(k)), 99))

    # Build structured output for Claude Code to synthesize.
    mode = "Research mode (live web search enabled)" if web_search else "Standard mode"
    parts = [
        f"# Council Raw Responses",
        f"_Mode: {mode}_",
        "",
        "Three independent expert perspectives follow. Synthesize them for",
        "the user: state the consensus, highlight any disagreement and its",
        "root cause, then give your own recommendation grounded in project context.",
        "",
    ]

    for r in responses:
        parts.append(f"## {r['model']}")
        if r["response"]:
            parts.append(r["response"])
        else:
            parts.append(f"_error: {r['error']}_")
        parts.append("")

    # Status footer for transparency on partial responses.
    ok = sum(1 for r in responses if r["response"])
    parts.append(f"---")
    parts.append(f"_{ok}/{len(responses)} council members responded successfully._")

    return "\n".join(parts)


# ---------- MCP Tool registration ----------

def _tool(name: str, description: str, properties: dict, required: list[str]) -> Tool:
    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available council tools."""
    STD_SUFFIX = " (GPT-5.4 + Claude Opus 4.7 + Gemini 3 Pro). Returns three raw responses for you to synthesize."
    RESEARCH_SUFFIX = " WITH LIVE WEB SEARCH enabled on all three models. Slower and more expensive than the standard variant; use only when recency of information matters."

    return [
        # --- Standard tools (no web search) ---
        _tool("council_review",
              "Get a code review from the LLM council." + STD_SUFFIX,
              {
                  "code": {"type": "string", "description": "The code to review"},
                  "focus": {"type": "string", "description": "Optional: specific focus area (security, performance, style)"},
              },
              ["code"]),
        _tool("council_architecture",
              "Get architecture advice from the LLM council." + STD_SUFFIX,
              {
                  "question": {"type": "string", "description": "The architecture question or decision"},
                  "context": {"type": "string", "description": "Relevant context about the system"},
              },
              ["question"]),
        _tool("council_debug",
              "Get debugging help from the LLM council." + STD_SUFFIX,
              {
                  "problem": {"type": "string", "description": "Description of the bug/problem"},
                  "code": {"type": "string", "description": "Relevant code"},
                  "error": {"type": "string", "description": "Error message if any"},
              },
              ["problem"]),
        _tool("council_security",
              "Get a security audit from the LLM council." + STD_SUFFIX,
              {
                  "code": {"type": "string", "description": "The code to audit"},
                  "context": {"type": "string", "description": "Context about the application (web app, API, etc.)"},
              },
              ["code"]),
        _tool("council_refactor",
              "Get refactoring suggestions from the LLM council." + STD_SUFFIX,
              {
                  "code": {"type": "string", "description": "The code to refactor"},
                  "goals": {"type": "string", "description": "Refactoring goals (simplify, modularize, etc.)"},
              },
              ["code"]),
        _tool("council_ask",
              "Ask a general question to the LLM council." + STD_SUFFIX,
              {
                  "question": {"type": "string", "description": "The question to ask"},
                  "context": {"type": "string", "description": "Additional context"},
              },
              ["question"]),

        # --- Research variants (web search enabled) ---
        _tool("council_research_ask",
              "Ask a general question to the LLM council." + RESEARCH_SUFFIX,
              {
                  "question": {"type": "string", "description": "The question to ask"},
                  "context": {"type": "string", "description": "Additional context"},
              },
              ["question"]),
        _tool("council_research_architecture",
              "Get architecture advice from the LLM council." + RESEARCH_SUFFIX,
              {
                  "question": {"type": "string", "description": "The architecture question or decision"},
                  "context": {"type": "string", "description": "Relevant context about the system"},
              },
              ["question"]),
        _tool("council_research_security",
              "Get a security audit from the LLM council." + RESEARCH_SUFFIX,
              {
                  "code": {"type": "string", "description": "The code to audit"},
                  "context": {"type": "string", "description": "Context about the application (web app, API, etc.)"},
              },
              ["code"]),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route each MCP tool call to run_council with the right parameters."""
    web_search = name.startswith("council_research_")

    # Standard tools
    if name in ("council_review",):
        code = arguments.get("code", "")
        focus = arguments.get("focus", "")
        task = "Review this code" + (f" with focus on {focus}" if focus else "")
        result = run_council(task, code, "code_review", web_search=web_search)

    elif name in ("council_architecture", "council_research_architecture"):
        question = arguments.get("question", "")
        context = arguments.get("context", "")
        result = run_council(question, context, "architecture", web_search=web_search)

    elif name == "council_debug":
        problem = arguments.get("problem", "")
        code = arguments.get("code", "")
        error = arguments.get("error", "")
        ctx = f"Code:\n{code}\n\nError:\n{error}" if code or error else ""
        result = run_council(problem, ctx, "debug", web_search=web_search)

    elif name in ("council_security", "council_research_security"):
        code = arguments.get("code", "")
        context = arguments.get("context", "")
        full_ctx = f"{context}\n\nCode:\n{code}" if context else code
        result = run_council("Perform a security audit on this code", full_ctx, "security", web_search=web_search)

    elif name == "council_refactor":
        code = arguments.get("code", "")
        goals = arguments.get("goals", "improve code quality")
        result = run_council(f"Suggest refactoring to {goals}", code, "refactor", web_search=web_search)

    elif name in ("council_ask", "council_research_ask"):
        question = arguments.get("question", "")
        context = arguments.get("context", "")
        result = run_council(question, context, "general", web_search=web_search)

    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


async def main():
    """Run the MCP server over stdio."""
    init_clients()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
