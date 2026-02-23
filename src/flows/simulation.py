# src/flows/simulation.py
"""Prefect flows for running simulations."""

from prefect import flow, task, get_run_logger
from prefect.concurrency.asyncio import concurrency
from typing import List, Dict, Any
import asyncio

from src.models.persona import Persona, PollQuestion, PollResponse


# ============================================================================
# TASKS - Individual units of work
# ============================================================================

@task(name="poll_agent")
async def poll_agent(
    persona: Persona,
    question: PollQuestion,
    news_context: str,
    llm_client: Any
) -> PollResponse:
    """Poll a single agent on a question."""
    logger = get_run_logger()

    prompt = persona.to_prompt(news_context) + f"\n\nQuestion: {question.question}"
    if question.options:
        prompt += f"\nOptions: {', '.join(question.options)}"

    try:
        response = await llm_client.generate(prompt)
        logger.info(f"Agent {persona.precinct_id}_{persona.age}_{persona.gender}: {response[:50]}...")

        return PollResponse(
            agent_id=f"{persona.precinct_id}_{hash(persona.json()) % 10000}",
            question_id=question.id,
            response=response.strip()
        )
    except Exception as e:
        logger.error(f"Error polling agent: {e}")
        raise


@task(name="update_agent_opinion")
async def update_agent_opinion(
    persona: Persona,
    news_context: str,
    neighbor_influence: Dict[str, float],
    llm_client: Any
) -> Dict[str, Any]:
    """Update an agent's opinion based on news and neighbor influence."""
    logger = get_run_logger()

    prompt = f"""{persona.to_prompt(news_context)}

You've had {len(neighbor_influence)} conversations with neighbors recently.
Their views on key issues: {neighbor_influence}

Considering your own views and these conversations, how (if at all) have your opinions shifted?
Respond with any changes in the format: ISSUE: new_position (or "no change")."""

    try:
        response = await llm_client.generate(prompt)
        return {"persona_id": persona.precinct_id, "opinion_update": response}
    except Exception as e:
        logger.error(f"Error updating agent opinion: {e}")
        return {"persona_id": persona.precinct_id, "opinion_update": "no change"}


@task(name="fetch_news_context")
async def fetch_news_context(county: str) -> str:
    """Fetch recent news for a county."""
    from src.tasks.news import NewsScraper
    scraper = NewsScraper()
    return await scraper.get_local_news_summary(county)


# ============================================================================
# FLOWS - Orchestrate tasks with concurrency control
# ============================================================================

@flow(name="poll_precinct")
async def poll_precinct(
    personas: List[Persona],
    question: PollQuestion,
    news_context: str,
    llm_client: Any,
    max_concurrent: int = 50
) -> List[PollResponse]:
    """
    Poll all agents in a precinct concurrently.

    Args:
        personas: List of persona objects in the precinct
        question: Question to poll
        news_context: Current news context
        llm_client: LLM client instance
        max_concurrent: Max concurrent API calls
    """
    logger = get_run_logger()
    logger.info(f"Polling {len(personas)} agents in precinct")

    responses = []

    # Process in batches to control concurrency
    for i in range(0, len(personas), max_concurrent):
        batch = personas[i:i + max_concurrent]

        # Create tasks for this batch
        tasks = [
            poll_agent(
                persona=persona,
                question=question,
                news_context=news_context,
                llm_client=llm_client
            )
            for persona in batch
        ]

        # Execute batch concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        for result in batch_results:
            if isinstance(result, PollResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed: {result}")

        logger.info(f"Completed batch {i//max_concurrent + 1}, {len(responses)} responses so far")

    return responses


@flow(name="run_simulation")
async def run_simulation(
    precinct_ids: List[str],
    questions: List[PollQuestion],
    num_iterations: int = 1,
    max_concurrent: int = 50
) -> Dict[str, Any]:
    """
    Run a full simulation across multiple precincts.

    Args:
        precinct_ids: List of precinct IDs to simulate
        questions: List of questions to poll
        num_iterations: Number of simulation iterations
        max_concurrent: Max concurrent API calls per precinct
    """
    from src.tasks.database import get_personas_by_precinct, save_results
    from src.tasks.llm import get_llm_client
    from src.tasks.news import get_combined_news_context

    logger = get_run_logger()
    logger.info(f"Starting simulation for {len(precinct_ids)} precincts")

    llm_client = get_llm_client()
    all_results = {}

    # Get news context for all counties
    news_context = await get_combined_news_context(["San Francisco", "Miami-Dade"])

    for precinct_id in precinct_ids:
        logger.info(f"Processing precinct: {precinct_id}")

        # Fetch personas for this precinct
        personas = await get_personas_by_precinct(precinct_id)
        logger.info(f"Loaded {len(personas)} personas for {precinct_id}")

        precinct_results = {
            "precinct_id": precinct_id,
            "num_agents": len(personas),
            "questions": {}
        }

        # Poll on each question
        for question in questions:
            logger.info(f"Polling question: {question.id}")
            responses = await poll_precinct(
                personas=personas,
                question=question,
                news_context=news_context,
                llm_client=llm_client,
                max_concurrent=max_concurrent
            )

            # Aggregate responses
            precinct_results["questions"][question.id] = {
                "question": question.question,
                "responses": len(responses),
                "results": aggregate_responses(responses, question)
            }

        all_results[precinct_id] = precinct_results

    # Save results to database
    await save_results(all_results)

    logger.info("Simulation complete")
    return all_results


def aggregate_responses(responses: List[PollResponse], question: PollQuestion) -> Dict:
    """Aggregate poll responses."""
    if question.question_type == "choice":
        counts = {}
        for r in responses:
            choice = r.response.upper()
            counts[choice] = counts.get(choice, 0) + 1
        return {"type": "counts", "data": counts}
    elif question.question_type == "scale":
        values = []
        for r in responses:
            try:
                values.append(float(r.response))
            except:
                pass
        if values:
            return {
                "type": "stats",
                "data": {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
            }
    return {"type": "raw", "responses": [r.response for r in responses]}


@flow(name="interaction_simulation")
async def interaction_simulation(
    precinct_id: str,
    num_steps: int = 3
) -> Dict[str, Any]:
    """
    Simulate agents interacting with each other over multiple steps.
    Agents influence nearby agents with shared demographics.
    """
    from src.tasks.database import get_personas_by_precinct, save_results
    from src.tasks.llm import get_llm_client

    logger = get_run_logger()
    personas = await get_personas_by_precinct(precinct_id)

    logger.info(f"Running {num_steps} interaction steps for {len(personas)} agents")

    # This is where you'd implement the interaction graph logic
    # For now, return placeholder

    return {"precinct_id": precinct_id, "steps": num_steps, "status": "implemented"}
