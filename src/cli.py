#!/usr/bin/env python
"""CLI interface for Jefferson AI (for v1 before dashboard)."""

import asyncio
from typing import List, Optional

import click
from dotenv import load_dotenv

from src.flows.ingestion import ingest_all_data, ingest_news
from src.flows.simulation import poll_precinct, run_simulation
from src.models.persona import PollQuestion
from src.tasks.database import get_persona_count, get_personas_by_precinct, list_simulations
from src.tasks.llm import get_llm_client

# Load environment variables from .env file
load_dotenv()


@click.group()
def cli():
    """Jefferson AI - Synthetic Voter Simulation"""
    pass


# ============================================================================
# Data Ingestion Commands
# ============================================================================


@cli.command()
@click.argument("survey_files", nargs=-1, type=click.Path(exists=True))
@click.option("--precincts", "-p", multiple=True, help="Precinct IDs to generate personas for")
@click.option("--socrates/--no-socrates", default=True, help="Use SOCSCI210 priors")
def ingest(survey_files: tuple, precincts: tuple, socrates: bool):
    """Ingest survey data and generate personas."""
    click.echo(f"Ingesting {len(survey_files)} survey files...")
    click.echo(f"Generating personas for {len(precincts)} precincts...")

    result = asyncio.run(
        ingest_all_data(
            survey_files=list(survey_files), precinct_ids=list(precincts), use_socrates=socrates
        )
    )

    click.echo("Ingestion complete!")
    click.echo(f"Results: {result}")


@cli.command()
@click.argument("county")
@click.option("--hours", "-h", default=48, help="Hours back to scrape")
def scrape_news(county: str, hours: int):
    """Scrape recent local news."""
    click.echo(f"Scraping news for {county} (last {hours} hours)...")

    articles = asyncio.run(ingest_news(county, hours))

    click.echo(f"Found {len(articles)} articles")
    for article in articles[:10]:
        click.echo(f"  - {article['title']}")


# ============================================================================
# Persona Commands
# ============================================================================


@cli.command()
@click.option("--precinct", "-p", help="Filter by precinct ID")
def count(precinct: Optional[str] = None):
    """Count personas in database."""
    count = asyncio.run(get_persona_count(precinct))

    if precinct:
        click.echo(f"Personas in precinct {precinct}: {count}")
    else:
        click.echo(f"Total personas: {count}")


@cli.command()
@click.argument("precinct_id")
@click.option("--limit", "-l", default=10, help="Number of personas to show")
def show_personas(precinct_id: str, limit: int):
    """Show personas for a precinct."""
    personas = asyncio.run(get_personas_by_precinct(precinct_id))

    click.echo(f"Showing {min(limit, len(personas))} personas from {precinct_id}:")
    click.echo()

    for persona in personas[:limit]:
        click.echo(f"  {persona.age}yo {persona.race.value} {persona.gender}")
        click.echo(f"    {persona.party_id.value}, {persona.ideology.value}")
        click.echo(f"    Issues: {', '.join(persona.top_issues[:3])}")
        click.echo()


# ============================================================================
# Polling Commands
# ============================================================================


@cli.command()
@click.argument("precinct_id")
@click.argument("question")
@click.option(
    "--type",
    "-t",
    default="open",
    type=click.Choice(["open", "choice", "scale"]),
    help="Question type",
)
@click.option("--options", "-o", multiple=True, help="Options for choice questions")
@click.option("--concurrent", "-c", default=50, help="Max concurrent LLM calls")
def poll(precinct_id: str, question: str, type: str, options: tuple, concurrent: int):
    """Poll a precinct on a question."""
    click.echo(f"Polling precinct {precinct_id}...")

    # Build question object
    question_id = question[:30].lower().replace(" ", "_")
    poll_question = PollQuestion(
        id=question_id,
        question=question,
        question_type=type,
        options=list(options) if options else None,
    )

    # Get personas and run poll
    personas = asyncio.run(get_personas_by_precinct(precinct_id))
    click.echo(f"Found {len(personas)} personas")

    # Get news context
    from src.tasks.news import get_combined_news_context

    news_context = asyncio.run(get_combined_news_context(["San Francisco"]))

    # Run poll
    llm_client = get_llm_client()
    responses = asyncio.run(
        poll_precinct.serve(
            personas=personas,
            question=poll_question,
            news_context=news_context,
            llm_client=llm_client,
            max_concurrent=concurrent,
        )
    )

    click.echo(f"\nReceived {len(responses)} responses:\n")

    for response in responses[:10]:
        click.echo(f"  {response.response[:100]}")

    # Show aggregate if choice question
    if type == "choice":
        counts = {}
        for r in responses:
            choice = r.response.upper()
            counts[choice] = counts.get(choice, 0) + 1
        click.echo("\nAggregate:")
        for choice, count in sorted(counts.items(), key=lambda x: -x[1]):
            pct = count / len(responses) * 100 if responses else 0
            click.echo(f"  {choice}: {count} ({pct:.1f}%)")


@cli.command()
@click.argument("precinct_id")
def interactive_poll(precinct_id: str):
    """Interactive polling mode - ask multiple questions."""
    personas = asyncio.run(get_personas_by_precinct(precinct_id))

    if not personas:
        click.echo(f"No personas found for precinct {precinct_id}")
        return

    click.echo(f"Loaded {len(personas)} personas from {precinct_id}")
    click.echo("Enter questions one at a time (empty line to exit):\n")

    from src.tasks.news import get_combined_news_context

    news_context = asyncio.run(get_combined_news_context(["San Francisco"]))
    llm_client = get_llm_client()

    while True:
        question = click.prompt("\nQuestion", default="", show_default=False)

        if not question:
            break

        q_type = click.prompt("Type (open/choice/scale)", default="open")

        options = []
        if q_type == "choice":
            click.echo("Enter options (empty line when done):")
            while True:
                opt = click.prompt("  Option", default="", show_default=False)
                if not opt:
                    break
                options.append(opt)

        poll_question = PollQuestion(
            id=f"poll_{len(question)}",
            question=question,
            question_type=q_type,
            options=options if options else None,
        )

        click.echo("Polling...")
        responses = asyncio.run(
            poll_precinct.serve(
                personas=personas,
                question=poll_question,
                news_context=news_context,
                llm_client=llm_client,
            )
        )

        click.echo(f"\n{len(responses)} responses received")

        if q_type == "choice":
            counts = {}
            for r in responses:
                choice = r.response.upper()
                counts[choice] = counts.get(choice, 0) + 1
            for choice, count in sorted(counts.items(), key=lambda x: -x[1]):
                pct = count / len(responses) * 100 if responses else 0
                click.echo(f"  {choice}: {pct:.1f}%")
        else:
            for r in responses[:5]:
                click.echo(f"  {r.response[:80]}...")


# ============================================================================
# Simulation Commands
# ============================================================================


@cli.command()
@click.argument("precincts", nargs=-1)
@click.option("--questions", "-q", multiple=True, help="Questions to ask")
@click.option("--iterations", "-i", default=1, help="Number of iterations")
@click.option("--concurrent", "-c", default=50, help="Max concurrent LLM calls")
def simulate(precincts: tuple, questions: tuple, iterations: int, concurrent: int):
    """Run a full simulation."""
    click.echo(f"Starting simulation for {len(precincts)} precincts...")

    # Build question objects
    poll_questions = [
        PollQuestion(id=f"q_{i}", question=q, question_type="open") for i, q in enumerate(questions)
    ]

    if not poll_questions:
        click.echo("No questions provided. Use --questions or -q")
        return

    result = asyncio.run(
        run_simulation.serve(
            precinct_ids=list(precincts),
            questions=poll_questions,
            num_iterations=iterations,
            max_concurrent=concurrent,
        )
    )

    click.echo("\nSimulation complete!")
    click.echo(f"Results: {result}")


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of simulations to show")
def list_sims(limit: int):
    """List recent simulations."""
    simulations = asyncio.run(list_simulations(limit))

    click.echo(f"Recent simulations (last {limit}):")
    for sim in simulations:
        click.echo(f"  {sim['simulation_id']}: {sim['status']}")


if __name__ == "__main__":
    cli()
