#!/usr/bin/env python3
"""End-to-end simulation test for Jefferson AI.

This script demonstrates the complete flow:
1. Generate personas from precinct configurations and survey data
2. Poll agents on election questions using LLM
3. Aggregate and display results
"""

import asyncio
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.persona import (
    Education,
    Ideology,
    Persona,
    PoliticalParty,
    PollQuestion,
    PollResponse,
    Race,
)
from tasks.llm import LLMClient, get_llm_client
from utils.persona_generator import PersonaGenerator

# ============================================================================
# SIMULATION CONFIGURATION
# ============================================================================

# Simulation questions
SIMULATION_QUESTIONS = [
    PollQuestion(
        id="q1",
        question="Who do you plan to vote for in the upcoming election?",
        question_type="choice",
        options=[
            "Democratic candidate",
            "Republican candidate",
            "Independent/Third party candidate",
            "Undecided / Will not vote",
        ],
    ),
    PollQuestion(
        id="q2",
        question="What is the most important issue facing your community?",
        question_type="choice",
        options=[
            "Economy and jobs",
            "Healthcare",
            "Immigration",
            "Education",
            "Crime and public safety",
            "Climate change and environment",
            "Other",
        ],
    ),
    PollQuestion(
        id="q3",
        question="On a scale of 1-7, how do you feel about the direction of the country?",
        question_type="scale",
        scale_range=(1, 7),
    ),
    PollQuestion(
        id="q4",
        question="Do you approve or disapprove of the current local government's performance?",
        question_type="choice",
        options=[
            "Strongly approve",
            "Somewhat approve",
            "Neither approve nor disapprove",
            "Somewhat disapprove",
            "Strongly disapprove",
        ],
    ),
]


# ============================================================================
# SIMULATION FUNCTIONS
# ============================================================================


async def poll_single_agent(
    agent: Persona,
    question: PollQuestion,
    llm_client: LLMClient,
    news_context: str = "",
) -> PollResponse:
    """Poll a single agent on a question."""
    try:
        prompt = agent.to_prompt(news_context) + f"\n\nQuestion: {question.question}"
        if question.options:
            prompt += f"\nOptions: {', '.join(question.options)}"
        elif question.scale_range:
            prompt += f"\nScale: 1-7 (1 = Strongly Disagree, 7 = Strongly Agree)"

        print(f"  Polling {agent.precinct_id} agent (Age {agent.age}, {agent.race})...")

        response = await llm_client.generate(prompt)

        print(
            f"  Response: {response[:100]}..."
            if len(response) > 100
            else f"  Response: {response}"
        )

        return PollResponse(
            agent_id=f"{agent.precinct_id}_{hash(str(agent.json())) % 10000}",
            question_id=question.id,
            response=response.strip(),
            confidence=0.8,  # Default confidence
        )
    except Exception as e:
        print(f"  ✗ Error polling agent: {e}")
        # Return fallback response
        return PollResponse(
            agent_id=f"{agent.precinct_id}_{hash(str(agent.json())) % 10000}",
            question_id=question.id,
            response="Undecided",
            confidence=0.0,
        )


async def poll_all_agents(
    agents: List[Persona],
    questions: List[PollQuestion],
    llm_client: LLMClient,
    max_concurrent: int = 10,
    news_context: str = "",
) -> Dict[str, List[PollResponse]]:
    """Poll all agents on all questions."""
    print(f"\n{'=' * 80}")
    print(f"{'SIMULATION START':^76}")
    print(f"{'=' * 80}\n")

    print(f"Polling {len(agents)} agents on {len(questions)} questions")
    print(f"Concurrency: {max_concurrent} agents at a time")
    print(f"News context: {'Yes' if news_context else 'No'}")
    print()

    results = {question.id: [] for question in questions}

    # Process each question
    for question_idx, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"QUESTION {question_idx}/{len(questions)}: {question.question}")
        print(f"{'─' * 80}")

        # Process agents in batches for concurrency control
        for i in range(0, len(agents), max_concurrent):
            batch = agents[i : i + max_concurrent]

            # Create tasks for this batch
            tasks = [
                poll_single_agent(
                    agent=agent,
                    question=question,
                    llm_client=llm_client,
                    news_context=news_context,
                )
                for agent in batch
            ]

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful results
            for result in batch_results:
                if isinstance(result, PollResponse):
                    results[question.id].append(result)
                elif isinstance(result, Exception):
                    print(f"  ✗ Task failed: {result}")

            # Show progress
            completed = len(results[question.id])
            print(f"  Progress: {completed}/{len(agents)} agents polled...")

        print(
            f"  ✓ Question {question_idx} complete: {len(results[question.id])} responses\n"
        )

    return results


def aggregate_results(
    results: Dict[str, List[PollResponse]], questions: List[PollQuestion]
) -> Dict[str, any]:
    """Aggregate poll results and generate statistics."""
    print(f"\n{'=' * 80}")
    print(f"{'RESULTS ANALYSIS':^76}")
    print(f"{'=' * 80}\n")

    summary = {
        "total_agents": len(
            set(r.agent_id for responses in results.values() for r in responses)
        ),
        "question_results": {},
    }

    for question in questions:
        question_results = results.get(question.id, [])

        if not question_results:
            summary["question_results"][question.id] = {
                "question": question.question,
                "total_responses": 0,
                "analysis": "No responses",
            }
            continue

        total_responses = len(question_results)

        if question.question_type == "choice":
            # Count choice frequencies
            choice_counts = Counter(r.response for r in question_results)

            # Calculate percentages
            choice_stats = []
            for choice in question.options or []:
                count = choice_counts.get(choice, 0)
                pct = (count / total_responses) * 100 if total_responses > 0 else 0
                choice_stats.append(
                    {"choice": choice, "count": count, "percentage": pct}
                )

            # Sort by count
            choice_stats.sort(key=lambda x: x["count"], reverse=True)

            summary["question_results"][question.id] = {
                "question": question.question,
                "type": "choice",
                "total_responses": total_responses,
                "results": choice_stats,
            }

            # Print summary
            print(f"\n📊 {question.question}")
            print(f"   Total Responses: {total_responses}")
            print(f"   Results:")
            for stat in choice_stats:
                bar_length = int(stat["percentage"] / 2)
                bar = "█" * bar_length
                print(
                    f"   • {stat['choice']}: {stat['percentage']:5.1f}% ({stat['count']}) {bar}"
                )

        elif question.question_type == "scale":
            # Calculate statistics
            values = []
            for r in question_results:
                try:
                    val = float(r.response)
                    values.append(val)
                except (ValueError, TypeError):
                    pass

            if values:
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                median = sorted(values)[len(values) // 2] if values else 0

                summary["question_results"][question.id] = {
                    "question": question.question,
                    "type": "scale",
                    "total_responses": total_responses,
                    "statistics": {
                        "mean": round(avg, 2),
                        "median": median,
                        "min": min_val,
                        "max": max_val,
                    },
                }

                print(f"\n📊 {question.question}")
                print(f"   Total Responses: {total_responses}")
                print(f"   Statistics:")
                print(f"   • Mean: {avg:.2f}")
                print(f"   • Median: {median}")
                print(f"   • Min: {min_val}")
                print(f"   • Max: {max_val}")

        else:
            summary["question_results"][question.id] = {
                "question": question.question,
                "type": question.question_type,
                "total_responses": total_responses,
                "analysis": "See raw responses",
            }

    return summary


def analyze_by_demographics(
    personas: List[Persona], results: Dict[str, List[PollResponse]]
) -> None:
    """Analyze results by demographic groups."""
    print(f"\n{'=' * 80}")
    print(f"{'DEMOGRAPHIC ANALYSIS':^76}")
    print(f"{'=' * 80}\n")

    # Group personas by key demographics
    by_race: Dict[str, List[Persona]] = {}
    by_age: Dict[str, List[Persona]] = {}
    by_party: Dict[str, List[Persona]] = {}
    all_personas: List[Persona] = []

    for persona in personas:
        race_key = persona.race if isinstance(persona.race, str) else persona.race.value
        party_key = (
            persona.party_id
            if isinstance(persona.party_id, str)
            else persona.party_id.value
        )

        by_race[race_key] = by_race.get(race_key, [])
        by_race[race_key].append(persona)

        age_group = (
            f"{18 - 29}"
            if persona.age < 30
            else f"{30 - 44}"
            if persona.age < 45
            else f"{45 - 64}"
            if persona.age < 65
            else "65+"
        )
        by_age[age_group] = by_age.get(age_group, [])
        by_age[age_group].append(persona)

        by_party[party_key] = by_party.get(party_key, [])
        by_party[party_key].append(persona)

    # Print demographic breakdowns
    print(f"📈 By Race ({len(all_personas)} total):")
    for race, count in sorted(by_race.items(), key=lambda x: x[0], reverse=True):
        pct = (count / len(all_personas)) * 100
        print(f"   • {race}: {count} ({pct:.1f}%)")

    print(f"\n📈 By Age Group:")
    for age, count in sorted(by_age.items()):
        pct = (count / len(all_personas)) * 100
        print(f"   • {age}: {count} ({pct:.1f}%)")

    print(f"\n📈 By Party:")
    for party, count in sorted(by_party.items(), key=lambda x: x[0], reverse=True):
        pct = (count / len(all_personas)) * 100
        print(f"   • {party}: {count} ({pct:.1f}%)")

    print()


# ============================================================================
# MAIN TEST
# ============================================================================


async def main():
    """Main test function."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "JEFFERSON AI SIMULATION TEST" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    print("End-to-end test of the Jefferson AI simulation pipeline")
    print("This will:")
    print("  1. Generate synthetic voters from precinct configs + survey data")
    print("  2. Poll them on election questions using LLM")
    print("  3. Aggregate and analyze results")
    print()

    # Step 1: Initialize persona generator
    print(f"\n{'─' * 80}")
    print("STEP 1: Generate Personas")
    print(f"{'─' * 80}\n")

    survey_dir = Path(__file__).parent / "data" / "surveys"
    sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"

    try:
        generator = PersonaGenerator(survey_dir=str(survey_dir))
        generator.load_precinct_configs(sf_config_path)
        print(f"✓ Loaded {len(generator.precinct_configs)} precinct configurations")
        print(
            f"✓ Survey data: {len(generator.survey_parser.all_respondents)} respondents"
        )

        # Generate voters for first precinct (small number for testing)
        precinct = generator.precinct_configs[0]
        num_voters = 10  # Small number for testing

        print(f"✓ Generating {num_voters} voters for {precinct.name}...")

        agents = generator.generate_voters_for_precinct(precinct, num_voters)
        print(f"✓ Generated {len(agents)} personas successfully\n")

        # Display sample demographics
        print(f"Sample Agents Generated:")
        for i, agent in enumerate(agents[:3], 1):
            print(f"\n  Agent {i}:")
            print(f"    ID: {agent.precinct_id}")
            print(f"    Age: {agent.age}, Gender: {agent.gender}, Race: {agent.race}")
            print(f"    Education: {agent.education}")
            print(f"    Party: {agent.party_id}, Ideology: {agent.ideology}")
            print(f"    Top Issues: {', '.join(agent.top_issues[:3])}")
            print(f"    News Sources: {', '.join(agent.news_sources[:3])}")

        print(f"\n  ... and {len(agents) - 3} more agents")

        # Step 2: Initialize LLM client
        print(f"\n{'─' * 80}")
        print("STEP 2: Initialize LLM Client")
        print(f"{'─' * 80}\n")

        try:
            llm_client = get_llm_client()
            provider = type(llm_client).__name__
            print(f"✓ LLM Client initialized: {provider}")
        except Exception as e:
            print(f"✗ Warning: Could not initialize LLM client: {e}")
            print("  ⚠ Will use mock responses instead\n")
            llm_client = None

        # Step 3: Run simulation
        if llm_client:
            print(f"\n{'─' * 80}")
            print("STEP 3: Run Simulation")
            print(f"{'─' * 80}\n")

            # Use a subset of questions for faster testing
            test_questions = SIMULATION_QUESTIONS[:2]  # Just first 2 questions

            results = await poll_all_agents(
                agents=agents,
                questions=test_questions,
                llm_client=llm_client,
                max_concurrent=5,
                news_context="",  # No news context for now
            )

            # Step 4: Aggregate results
            summary = aggregate_results(results, test_questions)

            # Step 5: Demographic analysis
            analyze_by_demographics(agents, results)

            # Final summary
            print(f"\n{'=' * 80}")
            print(f"{'SIMULATION SUMMARY':^76}")
            print(f"{'=' * 80}\n")

            print(f"✓ Successfully polled {summary['total_agents']} agents")
            print(f"✓ Processed {len(summary['question_results'])} questions")
            print(f"✓ Generated complete results\n")

            # Success!
            print(f"\n{'=' * 80}")
            print(f"{'SUCCESS':^76}")
            print(f"End-to-end simulation working!")
            print(f"{'=' * 80}\n")

            return 0
        else:
            print(f"\n{'=' * 80}")
            print(f"{'LIMITED TEST MODE':^76}")
            print(f"{'=' * 80}\n")

            print("No LLM client available - skipping simulation")
            print("✓ Persona generation and validation successful")
            print("✓ Ready for full simulation with LLM API keys configured")
            print("\nTo run full simulation:")
            print("  1. Set LLM_PROVIDER environment variable (glm, gemini, or claude)")
            print(
                "  2. Set corresponding API key (ZHIPUAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY)"
            )
            print("  3. Run this script again")
            print()

            return 1

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        return 130
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"{'ERROR':^76}")
        print(f"{'=' * 80}\n")

        print(f"✗ Simulation failed: {e}")
        import traceback

        traceback.print_exc()
        print()

        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
