#!/usr/bin/env python
"""Quick mock test of CLI without needing full setup."""

import asyncio
from src.models.persona import (
    Persona, PollQuestion, PoliticalParty, Ideology, Race, Education, Gender
)


async def mock_poll_test():
    """Test polling with mock personas (no DB needed)."""

    # Create mock personas
    personas = [
        Persona(
            age=25, gender="Female", race=Race.WHITE,
            education=Education.COLLEGE,
            income_bracket="$50-75K",
            employment_status="Employed",
            marital_status="Single",
            precinct_id="test_001",
            county="San Francisco",
            neighborhood="Mission",
            party_id=PoliticalParty.DEMOCRAT,
            ideology=Ideology.VERY_LIBERAL,
            top_issues=["Housing", "Climate", "Abortion"],
            news_sources=["Twitter", "Reddit"],
        ),
        Persona(
            age=55, gender="Male", race=Race.HISPANIC,
            education=Education.HIGH_SCHOOL,
            income_bracket="$30-50K",
            employment_status="Employed",
            marital_status="Married",
            precinct_id="test_001",
            county="San Francisco",
            neighborhood="Excelsior",
            party_id=PoliticalParty.DEMOCRAT,
            ideology=Ideology.MODERATE,
            top_issues=["Economy", "Immigration", "Education"],
            news_sources=["Facebook", "Local News"],
        ),
    ]

    # Test persona prompts
    print("=" * 60)
    print("TESTING PERSONA PROMPTS")
    print("=" * 60)

    for i, persona in enumerate(personas, 1):
        print(f"\nPersona {i}:")
        print(f"  {persona.age}yo {persona.race.value} {persona.gender}")
        print(f"  Party: {persona.party_id.value}, Ideology: {persona.ideology.value}")
        print(f"  Issues: {', '.join(persona.top_issues)}")
        print(f"\n  Prompt Preview:")
        print(f"  {persona.to_prompt()[:200]}...")

    # Test question format
    print("\n" + "=" * 60)
    print("TESTING POLL QUESTIONS")
    print("=" * 60)

    questions = [
        PollQuestion(
            id="q1",
            question="On a scale of 1-7, how would you rate the job performance of SF's mayor?",
            question_type="scale",
            scale_range=(1, 7)
        ),
        PollQuestion(
            id="q2",
            question="Which candidate would you vote for in the upcoming primary?",
            question_type="choice",
            options=["Candidate A", "Candidate B", "Undecided"]
        ),
    ]

    for q in questions:
        print(f"\nQuestion: {q.question}")
        print(f"  Type: {q.question_type}")
        print(f"  Options/Scale: {q.options or q.scale_range}")

    # Test LLM call (if you have API key)
    print("\n" + "=" * 60)
    print("TESTING LLM CALL")
    print("=" * 60)

    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("ZHIPUAI_API_KEY")

    if api_key:
        print("API key found - testing LLM call...")

        from src.tasks.llm import get_llm_client

        client = get_llm_client()
        persona = personas[0]

        prompt = f"""{persona.to_prompt()}

Question: On a scale of 1-7, how concerned are you about housing in San Francisco?
Respond with just the number."""

        try:
            response = await client.generate(prompt)
            print(f"\nPersona: {persona.age}yo {persona.gender}, {persona.ideology.value}")
            print(f"Question: Housing concern (1-7)")
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error calling LLM: {e}")
    else:
        print("No API key found - skipping LLM test")
        print("Set GEMINI_API_KEY or ZHIPUAI_API_KEY in .env to test")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(mock_poll_test())
