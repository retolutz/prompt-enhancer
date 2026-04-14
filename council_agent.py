#!/usr/bin/env python3
"""
Council Agent - Standalone Multi-LLM Council for Complex Tasks

A powerful CLI tool that consults multiple AI models (o3, Claude Opus 4, Gemini 2.5 Pro)
for complex coding and general tasks, then synthesizes the best response.

Usage:
    # Code review
    python council_agent.py review path/to/file.py

    # Architecture decision
    python council_agent.py architect "Should I use microservices or monolith?"

    # Debug help
    python council_agent.py debug "App crashes when user logs in" --code path/to/auth.py

    # Security audit
    python council_agent.py security path/to/api.py

    # General question
    python council_agent.py ask "What's the best approach for caching in a distributed system?"

    # Interactive mode
    python council_agent.py interactive
"""

import os
import sys
import click
import concurrent.futures
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from openai import OpenAI
import anthropic
from dotenv import load_dotenv

try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

load_dotenv(override=True)

console = Console()


@dataclass
class ModelResponse:
    """Response from a single model."""
    name: str
    response: Optional[str]
    error: Optional[str]
    tokens: int = 0


class CouncilAgent:
    """Multi-LLM Council Agent for complex tasks."""

    COUNCIL_TYPES = {
        "review": {
            "name": "Code Review Council",
            "system": """You are an expert code reviewer. Analyze the code for:
- Security vulnerabilities (injection, XSS, authentication issues)
- Performance problems (N+1 queries, memory leaks, inefficiencies)
- Code quality (readability, maintainability, SOLID principles)
- Error handling and edge cases
- Best practices and potential improvements

Be specific, actionable, and prioritize by impact. Use code examples where helpful."""
        },
        "architecture": {
            "name": "Architecture Council",
            "system": """You are a senior software architect. Evaluate for:
- Scalability characteristics and bottlenecks
- Maintainability and separation of concerns
- Security architecture
- Technology trade-offs
- Future extensibility

Consider real-world constraints and provide concrete recommendations with reasoning."""
        },
        "debug": {
            "name": "Debugging Council",
            "system": """You are an expert debugger. Help identify:
- Root cause analysis
- Potential failure modes
- Edge cases and race conditions
- Systematic debugging approach
- Relevant logs/traces to check

Think step-by-step through the problem. Consider multiple hypotheses."""
        },
        "security": {
            "name": "Security Audit Council",
            "system": """You are a security expert. Perform a thorough audit:
- OWASP Top 10 vulnerabilities
- Authentication/authorization flaws
- Input validation and sanitization
- Secrets and sensitive data handling
- Attack surface analysis
- Compliance considerations

Prioritize findings by severity (Critical/High/Medium/Low)."""
        },
        "refactor": {
            "name": "Refactoring Council",
            "system": """You are a refactoring expert. Suggest improvements for:
- Code organization and structure
- Design patterns that could help
- Reducing complexity and duplication
- Improving testability
- Performance optimizations

Provide specific, incremental refactoring steps with before/after examples."""
        },
        "test": {
            "name": "Testing Council",
            "system": """You are a testing expert. Help with:
- Test case generation (unit, integration, e2e)
- Edge cases and boundary conditions
- Mocking and test isolation
- Test coverage improvements
- Testing best practices

Generate concrete test examples and identify gaps in coverage."""
        },
        "general": {
            "name": "General Council",
            "system": """You are a helpful AI assistant participating in a council of experts.
Provide thorough analysis and actionable recommendations.
Consider multiple perspectives and trade-offs.
Be specific and support your conclusions with reasoning."""
        }
    }

    def __init__(self):
        """Initialize the council with available LLM clients."""
        self.openai_client = None
        self.anthropic_client = None
        self.google_client = None

        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI()
        if os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic_client = anthropic.Anthropic()
        if GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            self.google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def get_available_models(self) -> list:
        """Return list of available models."""
        models = []
        if self.openai_client:
            models.append("o3 (OpenAI)")
        if self.anthropic_client:
            models.append("Claude Opus 4 (Anthropic)")
        if self.google_client:
            models.append("Gemini 2.5 Pro (Google)")
        return models

    def _call_openai(self, prompt: str, system: str) -> ModelResponse:
        """Call OpenAI o3."""
        if not self.openai_client:
            return ModelResponse("o3", None, "Not configured")
        try:
            response = self.openai_client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
            )
            return ModelResponse(
                "o3 (OpenAI)",
                response.choices[0].message.content,
                None,
                response.usage.total_tokens
            )
        except Exception as e:
            return ModelResponse("o3 (OpenAI)", None, str(e))

    def _call_anthropic(self, prompt: str, system: str) -> ModelResponse:
        """Call Claude Opus 4."""
        if not self.anthropic_client:
            return ModelResponse("Claude Opus 4", None, "Not configured")
        try:
            response = self.anthropic_client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return ModelResponse(
                "Claude Opus 4 (Anthropic)",
                response.content[0].text,
                None,
                tokens
            )
        except Exception as e:
            return ModelResponse("Claude Opus 4 (Anthropic)", None, str(e))

    def _call_google(self, prompt: str, system: str) -> ModelResponse:
        """Call Gemini 2.5 Pro."""
        if not self.google_client:
            return ModelResponse("Gemini 2.5 Pro", None, "Not configured")
        try:
            full_prompt = f"{system}\n\n{prompt}"
            response = self.google_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=full_prompt,
            )
            return ModelResponse(
                "Gemini 2.5 Pro (Google)",
                response.text,
                None,
                0  # Gemini doesn't report tokens the same way
            )
        except Exception as e:
            return ModelResponse("Gemini 2.5 Pro (Google)", None, str(e))

    def _aggregate(self, task: str, responses: list[ModelResponse]) -> str:
        """Aggregate responses using Claude Opus 4."""
        successful = [r for r in responses if r.response]

        if not successful:
            return "Error: No successful responses from council"

        if len(successful) == 1:
            return successful[0].response

        responses_text = "\n\n".join([
            f"=== {r.name} ===\n{r.response}"
            for r in successful
        ])

        aggregation_prompt = f"""You are synthesizing responses from multiple AI models.

TASK: {task}

RESPONSES FROM COUNCIL:
{responses_text}

YOUR JOB:
1. Identify the unique insights from each model
2. Note any disagreements or different perspectives
3. Synthesize the BEST elements into one comprehensive response
4. If models disagree, explain the trade-offs
5. Structure your response clearly with headers and bullet points

Output a well-organized, actionable synthesis that captures the council's wisdom."""

        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-opus-4-20250514",
                    max_tokens=8192,
                    messages=[{"role": "user", "content": aggregation_prompt}],
                )
                return response.content[0].text
            except:
                pass

        # Fallback
        return responses_text

    def consult(
        self,
        task: str,
        context: str = "",
        council_type: str = "general",
        show_individual: bool = False
    ) -> dict:
        """
        Consult the council on a task.

        Args:
            task: The question or task description
            context: Additional context (code, error messages, etc.)
            council_type: Type of council (review, architecture, debug, etc.)
            show_individual: Whether to include individual responses

        Returns:
            dict with synthesis and optionally individual responses
        """
        config = self.COUNCIL_TYPES.get(council_type, self.COUNCIL_TYPES["general"])
        system = config["system"]
        prompt = f"{task}\n\nContext:\n{context}" if context else task

        # Call all models in parallel
        responses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self._call_openai, prompt, system),
                executor.submit(self._call_anthropic, prompt, system),
                executor.submit(self._call_google, prompt, system),
            ]
            for future in concurrent.futures.as_completed(futures):
                responses.append(future.result())

        # Aggregate
        synthesis = self._aggregate(task, responses)

        result = {
            "council_type": config["name"],
            "synthesis": synthesis,
            "models_consulted": len([r for r in responses if r.response]),
            "total_tokens": sum(r.tokens for r in responses),
        }

        if show_individual:
            result["individual_responses"] = [
                {"model": r.name, "response": r.response, "error": r.error}
                for r in responses
            ]

        return result


# CLI Commands
@click.group()
def cli():
    """Council Agent - Multi-LLM Council for Complex Tasks"""
    pass


def print_result(result: dict, show_individual: bool = False):
    """Pretty print the council result."""
    console.print(f"\n[bold magenta]{result['council_type']}[/bold magenta]")
    console.print(f"[dim]Models consulted: {result['models_consulted']} | Tokens: {result['total_tokens']}[/dim]\n")

    if show_individual and "individual_responses" in result:
        for resp in result["individual_responses"]:
            if resp["error"]:
                console.print(Panel(
                    f"[red]Error: {resp['error']}[/red]",
                    title=f"[bold red]{resp['model']}[/bold red]",
                    border_style="red"
                ))
            elif resp["response"]:
                # Truncate for display
                text = resp["response"][:2000] + "..." if len(resp["response"]) > 2000 else resp["response"]
                console.print(Panel(
                    Markdown(text),
                    title=f"[bold yellow]{resp['model']}[/bold yellow]",
                    border_style="yellow"
                ))

    console.print(Panel(
        Markdown(result["synthesis"]),
        title="[bold green]Council Synthesis[/bold green]",
        border_style="green"
    ))


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--focus", "-f", help="Specific focus area (security, performance, style)")
@click.option("--show-all", "-a", is_flag=True, help="Show individual model responses")
def review(file_path: str, focus: str, show_all: bool):
    """Get a code review from the council."""
    code = Path(file_path).read_text()
    task = f"Review this code" + (f" with focus on {focus}" if focus else "")

    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is reviewing..."),
        console=console
    ) as progress:
        progress.add_task("review", total=None)
        result = agent.consult(task, code, "review", show_all)

    print_result(result, show_all)


@cli.command()
@click.argument("question")
@click.option("--context", "-c", help="Additional context")
@click.option("--show-all", "-a", is_flag=True, help="Show individual responses")
def architect(question: str, context: str, show_all: bool):
    """Get architecture advice from the council."""
    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is deliberating..."),
        console=console
    ) as progress:
        progress.add_task("arch", total=None)
        result = agent.consult(question, context or "", "architecture", show_all)

    print_result(result, show_all)


@cli.command()
@click.argument("problem")
@click.option("--code", "-c", type=click.Path(exists=True), help="Relevant code file")
@click.option("--error", "-e", help="Error message")
@click.option("--show-all", "-a", is_flag=True, help="Show individual responses")
def debug(problem: str, code: str, error: str, show_all: bool):
    """Get debugging help from the council."""
    context_parts = []
    if code:
        context_parts.append(f"Code:\n{Path(code).read_text()}")
    if error:
        context_parts.append(f"Error:\n{error}")
    context = "\n\n".join(context_parts)

    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is debugging..."),
        console=console
    ) as progress:
        progress.add_task("debug", total=None)
        result = agent.consult(problem, context, "debug", show_all)

    print_result(result, show_all)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--context", "-c", help="Application context (web app, API, etc.)")
@click.option("--show-all", "-a", is_flag=True, help="Show individual responses")
def security(file_path: str, context: str, show_all: bool):
    """Get a security audit from the council."""
    code = Path(file_path).read_text()
    full_context = f"{context}\n\nCode:\n{code}" if context else code

    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is auditing security..."),
        console=console
    ) as progress:
        progress.add_task("security", total=None)
        result = agent.consult("Perform a security audit", full_context, "security", show_all)

    print_result(result, show_all)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--goals", "-g", default="improve code quality", help="Refactoring goals")
@click.option("--show-all", "-a", is_flag=True, help="Show individual responses")
def refactor(file_path: str, goals: str, show_all: bool):
    """Get refactoring suggestions from the council."""
    code = Path(file_path).read_text()

    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is analyzing..."),
        console=console
    ) as progress:
        progress.add_task("refactor", total=None)
        result = agent.consult(f"Suggest refactoring to {goals}", code, "refactor", show_all)

    print_result(result, show_all)


@cli.command()
@click.argument("question")
@click.option("--context", "-c", help="Additional context")
@click.option("--show-all", "-a", is_flag=True, help="Show individual responses")
def ask(question: str, context: str, show_all: bool):
    """Ask a general question to the council."""
    agent = CouncilAgent()
    console.print(f"[bold]Council Members:[/bold] {', '.join(agent.get_available_models())}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Council is thinking..."),
        console=console
    ) as progress:
        progress.add_task("ask", total=None)
        result = agent.consult(question, context or "", "general", show_all)

    print_result(result, show_all)


@cli.command()
def interactive():
    """Interactive council session."""
    console.print("\n[bold magenta]Council Agent - Interactive Mode[/bold magenta]")
    console.print("[dim]Commands: review, architect, debug, security, ask, quit[/dim]\n")

    agent = CouncilAgent()
    console.print(f"[bold]Available Models:[/bold] {', '.join(agent.get_available_models())}\n")

    while True:
        try:
            cmd = click.prompt("Council", type=str).strip().lower()

            if cmd == "quit":
                console.print("[yellow]Goodbye![/yellow]")
                break

            elif cmd == "review":
                file_path = click.prompt("File path")
                code = Path(file_path).read_text()
                with console.status("[cyan]Council reviewing..."):
                    result = agent.consult("Review this code", code, "review")
                print_result(result)

            elif cmd == "architect":
                question = click.prompt("Architecture question")
                with console.status("[cyan]Council deliberating..."):
                    result = agent.consult(question, "", "architecture")
                print_result(result)

            elif cmd == "debug":
                problem = click.prompt("Describe the problem")
                with console.status("[cyan]Council debugging..."):
                    result = agent.consult(problem, "", "debug")
                print_result(result)

            elif cmd == "security":
                file_path = click.prompt("File path")
                code = Path(file_path).read_text()
                with console.status("[cyan]Council auditing..."):
                    result = agent.consult("Security audit", code, "security")
                print_result(result)

            elif cmd == "ask":
                question = click.prompt("Your question")
                with console.status("[cyan]Council thinking..."):
                    result = agent.consult(question, "", "general")
                print_result(result)

            else:
                console.print("[red]Unknown command. Use: review, architect, debug, security, ask, quit[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@cli.command()
def status():
    """Check council status and available models."""
    agent = CouncilAgent()

    table = Table(title="Council Status")
    table.add_column("Model", style="cyan")
    table.add_column("Status", style="green")

    models = [
        ("o3 (OpenAI)", agent.openai_client is not None),
        ("Claude Opus 4 (Anthropic)", agent.anthropic_client is not None),
        ("Gemini 2.5 Pro (Google)", agent.google_client is not None),
    ]

    for name, available in models:
        status = "[green]Available[/green]" if available else "[red]Not configured[/red]"
        table.add_row(name, status)

    console.print(table)


if __name__ == "__main__":
    cli()
