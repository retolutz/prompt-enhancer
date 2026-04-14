#!/usr/bin/env python3
"""
Prompt Enhancer CLI
Transform basic prompts into professional-grade prompts using o3.
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import print as rprint

from enhancer import PromptEnhancer
from strategies import STRATEGY_DESCRIPTIONS, ALL_STRATEGIES

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
[bold cyan]╔═══════════════════════════════════════════════════════════╗
║           🚀 PROMPT ENHANCER v1.0                         ║
║     Transform basic prompts into professional-grade       ║
║          prompts using o3                             ║
╚═══════════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def print_strategies():
    """Print available strategies."""
    table = Table(title="Available Enhancement Strategies", show_header=True)
    table.add_column("Strategy", style="cyan", width=12)
    table.add_column("Description", style="white")

    for key, desc in STRATEGY_DESCRIPTIONS.items():
        if key == "master":
            table.add_row(f"[bold green]{key}[/]", f"[bold]{desc}[/]")
        else:
            table.add_row(key, desc)

    console.print(table)
    console.print("\n[dim]Use --strategy <name> to select a specific strategy[/dim]")


@click.group()
def cli():
    """Prompt Enhancer - Transform prompts into professional-grade instructions."""
    pass


@cli.command()
@click.argument("prompt", required=False)
@click.option("--strategy", "-s", default="master", help="Enhancement strategy to use")
@click.option("--file", "-f", type=click.Path(exists=True), help="Read prompt from file")
@click.option("--output", "-o", type=click.Path(), help="Write enhanced prompt to file")
@click.option("--temperature", "-t", default=0.7, help="Creativity level (0.0-1.0)")
@click.option("--compare", "-c", is_flag=True, help="Show comparison analysis")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
def enhance(prompt, strategy, file, output, temperature, compare, interactive):
    """
    Enhance a prompt using o3.

    Examples:
        prompt-enhancer enhance "Write a poem about nature"
        prompt-enhancer enhance -f prompt.txt -o enhanced.txt
        prompt-enhancer enhance -s role "Create a marketing plan"
        prompt-enhancer enhance -i  # Interactive mode
    """
    print_banner()

    # Interactive mode
    if interactive:
        console.print("\n[bold]Interactive Enhancement Mode[/bold]")
        console.print("[dim]Type 'quit' to exit, 'strategies' to see options[/dim]\n")

        try:
            enhancer = PromptEnhancer()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

        while True:
            prompt = Prompt.ask("\n[cyan]Enter prompt[/cyan]")

            if prompt.lower() == "quit":
                console.print("[yellow]Goodbye![/yellow]")
                break

            if prompt.lower() == "strategies":
                print_strategies()
                continue

            if not prompt.strip():
                continue

            with console.status("[bold green]Enhancing prompt..."):
                result = enhancer.enhance(prompt, strategy=strategy, temperature=temperature)

            console.print(Panel(
                result.enhanced_prompt,
                title="[bold green]Enhanced Prompt[/bold green]",
                border_style="green"
            ))
            console.print(f"[dim]Strategy: {result.strategy_used} | Tokens: {result.tokens_used}[/dim]")

        return

    # Get prompt from file or argument
    if file:
        with open(file, "r") as f:
            prompt = f.read().strip()
    elif not prompt:
        console.print("[red]Error: Please provide a prompt or use --file/-f to read from file[/red]")
        console.print("[dim]Use --interactive/-i for interactive mode[/dim]")
        sys.exit(1)

    # Validate strategy
    if strategy not in ALL_STRATEGIES:
        console.print(f"[red]Error: Unknown strategy '{strategy}'[/red]\n")
        print_strategies()
        sys.exit(1)

    # Initialize enhancer
    try:
        enhancer = PromptEnhancer()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Set your API key:[/yellow]")
        console.print("  export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Show original prompt
    console.print(Panel(
        prompt,
        title="[bold blue]Original Prompt[/bold blue]",
        border_style="blue"
    ))

    # Enhance
    with console.status(f"[bold green]Enhancing with '{strategy}' strategy..."):
        result = enhancer.enhance(prompt, strategy=strategy, temperature=temperature)

    # Show enhanced prompt
    console.print(Panel(
        result.enhanced_prompt,
        title="[bold green]Enhanced Prompt[/bold green]",
        border_style="green"
    ))

    console.print(f"\n[dim]Strategy: {result.strategy_used} | Tokens used: {result.tokens_used}[/dim]")

    # Compare if requested
    if compare:
        console.print("\n[bold]Analyzing improvements...[/bold]")
        with console.status("[bold cyan]Comparing prompts..."):
            comparison = enhancer.compare(prompt, result.enhanced_prompt)

        if "improvements" in comparison:
            console.print("\n[bold cyan]Improvements Made:[/bold cyan]")
            for imp in comparison.get("improvements", []):
                console.print(f"  • {imp}")

            console.print(f"\n[bold]Scores:[/bold]")
            console.print(f"  Original: {comparison.get('original_score', 'N/A')}/10")
            console.print(f"  Enhanced: {comparison.get('enhanced_score', 'N/A')}/10")
        else:
            console.print(comparison.get("raw_comparison", "Analysis not available"))

    # Write to file if requested
    if output:
        with open(output, "w") as f:
            f.write(result.enhanced_prompt)
        console.print(f"\n[green]Enhanced prompt saved to: {output}[/green]")


@cli.command()
@click.argument("prompt", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read prompt from file")
def analyze(prompt, file):
    """
    Analyze a prompt without enhancing it.

    Shows: intent, entities, constraints, ambiguities, and suggestions.
    """
    print_banner()

    if file:
        with open(file, "r") as f:
            prompt = f.read().strip()
    elif not prompt:
        console.print("[red]Error: Please provide a prompt or use --file/-f[/red]")
        sys.exit(1)

    try:
        enhancer = PromptEnhancer()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    console.print(Panel(prompt, title="[bold blue]Prompt to Analyze[/bold blue]", border_style="blue"))

    with console.status("[bold green]Analyzing prompt..."):
        analysis = enhancer.analyze(prompt)

    if "intent" in analysis:
        console.print("\n[bold cyan]Intent:[/bold cyan]", analysis.get("intent"))

        if analysis.get("entities"):
            console.print("\n[bold cyan]Key Entities:[/bold cyan]")
            for e in analysis["entities"]:
                console.print(f"  • {e}")

        if analysis.get("explicit_constraints"):
            console.print("\n[bold cyan]Explicit Constraints:[/bold cyan]")
            for c in analysis["explicit_constraints"]:
                console.print(f"  • {c}")

        if analysis.get("implicit_constraints"):
            console.print("\n[bold cyan]Implicit Constraints:[/bold cyan]")
            for c in analysis["implicit_constraints"]:
                console.print(f"  • {c}")

        if analysis.get("ambiguities"):
            console.print("\n[bold yellow]Potential Ambiguities:[/bold yellow]")
            for a in analysis["ambiguities"]:
                console.print(f"  ⚠ {a}")

        console.print(f"\n[bold]Quality Score:[/bold] {analysis.get('quality_score', 'N/A')}/10")

        if analysis.get("suggestions"):
            console.print("\n[bold green]Suggestions:[/bold green]")
            for s in analysis["suggestions"]:
                console.print(f"  → {s}")
    else:
        console.print(analysis.get("raw_analysis", "Analysis not available"))


@cli.command()
@click.argument("prompt", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read prompt from file")
@click.option("--output", "-o", type=click.Path(), help="Write enhanced prompt to file")
def iterative(prompt, file, output):
    """
    Apply multiple strategies iteratively for maximum enhancement.

    Applies: role -> constraint -> chain-of-thought -> output specification
    """
    print_banner()

    if file:
        with open(file, "r") as f:
            prompt = f.read().strip()
    elif not prompt:
        console.print("[red]Error: Please provide a prompt or use --file/-f[/red]")
        sys.exit(1)

    try:
        enhancer = PromptEnhancer()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    console.print(Panel(prompt, title="[bold blue]Original Prompt[/bold blue]", border_style="blue"))

    with console.status("[bold green]Applying iterative enhancement..."):
        result = enhancer.enhance_iterative(prompt)

    console.print(Panel(
        result.enhanced_prompt,
        title="[bold green]Enhanced Prompt (Iterative)[/bold green]",
        border_style="green"
    ))

    console.print(f"\n[dim]Pipeline: {result.strategy_used}[/dim]")
    console.print(f"[dim]Total tokens: {result.tokens_used}[/dim]")

    if output:
        with open(output, "w") as f:
            f.write(result.enhanced_prompt)
        console.print(f"\n[green]Enhanced prompt saved to: {output}[/green]")


@cli.command()
def strategies():
    """List all available enhancement strategies."""
    print_banner()
    print_strategies()


if __name__ == "__main__":
    cli()
