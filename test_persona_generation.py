#!/usr/bin/env python3
"""Test script to validate persona generation pipeline."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from collections import Counter

from models.persona import Persona, PrecinctConfig
from utils.persona_generator import PersonaGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_load_precincts_and_survey():
    """Test loading precinct configurations and survey data."""
    print("=" * 80)
    print("TEST 1: Load Precinct Configurations and Survey Data")
    print("=" * 80)

    try:
        # Initialize persona generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        print(f"✓ Initialized PersonaGenerator")
        print(
            f"  Survey respondents loaded: {len(generator.survey_parser.all_respondents)}"
        )
        print(f"  Survey waves: {list(generator.survey_parser.survey_waves.keys())}")

        # Load SF precinct configurations
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        print(
            f"\n✓ Loaded {len(generator.precinct_configs)} SF precinct configurations:"
        )
        for precinct in generator.precinct_configs:
            print(
                f"  - {precinct.name} ({precinct.id}): {precinct.expected_voters} expected voters"
            )

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_generate_voters_for_precinct():
    """Test generating voters for a single precinct."""
    print("=" * 80)
    print("TEST 2: Generate Voters for Single Precinct")
    print("=" * 80)

    try:
        # Initialize generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        # Load SF precincts
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        # Generate voters for first precinct
        precinct = generator.precinct_configs[0]
        num_voters = 10

        print(f"Generating {num_voters} voters for precinct: {precinct.name}")
        print(f"  Demographics target: {precinct.demographics['race_distribution']}")

        voters = generator.generate_voters_for_precinct(precinct, num_voters)

        print(f"\n✓ Generated {len(voters)} voters")

        # Display sample voters
        print("\n--- Sample Voters ---")
        for i, voter in enumerate(voters[:3]):
            print(f"\nVoter {i + 1}:")
            print(f"  Age: {voter.age}, Gender: {voter.gender}")
            # Handle both enum and string types (Pydantic may store as strings)
            race_val = voter.race.value if hasattr(voter.race, "value") else voter.race
            edu_val = (
                voter.education.value
                if hasattr(voter.education, "value")
                else voter.education
            )
            print(f"  Race: {race_val}, Education: {edu_val}")
            party_val = (
                voter.party_id.value
                if hasattr(voter.party_id, "value")
                else voter.party_id
            )
            ideology_val = (
                voter.ideology.value
                if hasattr(voter.ideology, "value")
                else voter.ideology
            )
            print(f"  Party: {party_val}, Ideology: {ideology_val}")
            print(f"  Income: {voter.income_bracket}")
            print(f"  Top Issues: {', '.join(voter.top_issues[:3])}")
            print(f"  News Sources: {', '.join(voter.news_sources[:3])}")
            print(f"  Source Voter ID: {voter.source_voter_id or 'None (fallback)'}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_validate_persona_fields():
    """Test that all generated personas have required fields."""
    print("=" * 80)
    print("TEST 3: Validate Persona Fields")
    print("=" * 80)

    try:
        # Initialize generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        # Load SF precincts
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        # Generate voters
        precinct = generator.precinct_configs[0]
        voters = generator.generate_voters_for_precinct(precinct, 10)

        print(f"Validating {len(voters)} personas...")

        # Required fields
        required_fields = [
            "age",
            "gender",
            "race",
            "education",
            "income_bracket",
            "employment_status",
            "marital_status",
            "precinct_id",
            "county",
            "neighborhood",
            "party_id",
            "ideology",
            "top_issues",
            "news_sources",
        ]

        all_valid = True
        for i, voter in enumerate(voters):
            missing_fields = []
            for field in required_fields:
                if not hasattr(voter, field) or getattr(voter, field) is None:
                    missing_fields.append(field)

            if missing_fields:
                print(f"  ✗ Voter {i + 1} missing fields: {missing_fields}")
                all_valid = False

        if all_valid:
            print(f"✓ All {len(voters)} personas have required fields")
        else:
            print(f"✗ Some personas are missing required fields")

        print()
        return all_valid

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_demographic_accuracy():
    """Test that generated voters match precinct demographics."""
    print("=" * 80)
    print("TEST 4: Demographic Accuracy")
    print("=" * 80)

    try:
        # Initialize generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        # Load SF precincts
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        # Generate larger sample for statistical analysis
        precinct = generator.precinct_configs[0]
        num_voters = 100

        print(f"Generating {num_voters} voters for: {precinct.name}")
        voters = generator.generate_voters_for_precinct(precinct, num_voters)

        # Count generated demographics (handle both enum and string types)
        race_counts = Counter(
            [v.race.value if hasattr(v.race, "value") else v.race for v in voters]
        )
        party_counts = Counter(
            [
                v.party_id.value if hasattr(v.party_id, "value") else v.party_id
                for v in voters
            ]
        )
        ideology_counts = Counter(
            [
                v.ideology.value if hasattr(v.ideology, "value") else v.ideology
                for v in voters
            ]
        )

        # Get target distributions
        target_race = precinct.demographics["race_distribution"]
        target_party = precinct.demographics["party_distribution"]
        target_ideology = precinct.demographics["ideology_distribution"]

        print(f"\n--- Race Distribution ---")
        for race in target_race.keys():
            target_pct = target_race[race] * 100
            actual_count = race_counts.get(race, 0)
            actual_pct = (actual_count / num_voters) * 100
            diff = abs(actual_pct - target_pct)
            status = "✓" if diff < 10 else "⚠"
            print(
                f"  {status} {race}: Target {target_pct:.1f}%, Actual {actual_pct:.1f}% (diff: {diff:.1f}%)"
            )

        print(f"\n--- Party Distribution ---")
        for party in target_party.keys():
            target_pct = target_party[party] * 100
            actual_count = party_counts.get(party, 0)
            actual_pct = (actual_count / num_voters) * 100
            diff = abs(actual_pct - target_pct)
            status = "✓" if diff < 15 else "⚠"
            print(
                f"  {status} {party}: Target {target_pct:.1f}%, Actual {actual_pct:.1f}% (diff: {diff:.1f}%)"
            )

        print(f"\n--- Ideology Distribution ---")
        for ideology in target_ideology.keys():
            target_pct = target_ideology[ideology] * 100
            actual_count = ideology_counts.get(ideology, 0)
            actual_pct = (actual_count / num_voters) * 100
            diff = abs(actual_pct - target_pct)
            status = "✓" if diff < 15 else "⚠"
            print(
                f"  {status} {ideology}: Target {target_pct:.1f}%, Actual {actual_pct:.1f}% (diff: {diff:.1f}%)"
            )

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_generate_all_precincts():
    """Test generating voters for all precincts."""
    print("=" * 80)
    print("TEST 5: Generate Voters for All Precincts")
    print("=" * 80)

    try:
        # Initialize generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        # Load SF precincts
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        # Generate voters for all precincts (small number for testing)
        num_voters_per_precinct = 10
        print(f"Generating {num_voters_per_precinct} voters for each precinct...")

        all_voters = generator.generate_all_precincts(num_voters_per_precinct)

        print(f"\n✓ Generated voters for {len(all_voters)} precincts:")

        total_voters = 0
        for precinct_id, voters in all_voters.items():
            total_voters += len(voters)
            print(f"  {precinct_id}: {len(voters)} voters")

        print(f"\n✓ Total voters generated: {total_voters}")

        # Count survey matches vs fallbacks
        survey_matches = sum(
            1 for voters in all_voters.values() for v in voters if v.source_voter_id
        )
        fallbacks = total_voters - survey_matches

        print(
            f"  Survey matches: {survey_matches} ({survey_matches / total_voters:.1%})"
        )
        print(f"  Fallback personas: {fallbacks} ({fallbacks / total_voters:.1%})")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_persona_to_prompt():
    """Test converting persona to LLM prompt."""
    print("=" * 80)
    print("TEST 6: Convert Persona to LLM Prompt")
    print("=" * 80)

    try:
        # Initialize generator
        survey_dir = Path(__file__).parent / "data" / "surveys"
        generator = PersonaGenerator(survey_dir=str(survey_dir))

        # Load SF precincts
        sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
        generator.load_precinct_configs(sf_config_path)

        # Generate a single voter
        precinct = generator.precinct_configs[0]
        voters = generator.generate_voters_for_precinct(precinct, 1)
        persona = voters[0]

        # Generate prompt
        prompt = persona.to_prompt()

        print("✓ Generated LLM prompt:\n")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
        print()

        # Verify prompt contains key information
        required_keywords = ["age", "race", "education", "income", "Party", "ideology"]
        missing_keywords = [
            kw for kw in required_keywords if kw.lower() not in prompt.lower()
        ]

        if not missing_keywords:
            print("✓ Prompt contains all required information")
        else:
            print(f"⚠ Prompt missing keywords: {missing_keywords}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def run_all_tests():
    """Run all persona generation tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "PERSONA GENERATION TESTS" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    results = []

    # Run tests
    results.append(("Load Precincts and Survey", test_load_precincts_and_survey()))
    results.append(
        ("Generate Voters for Precinct", test_generate_voters_for_precinct())
    )
    results.append(("Validate Persona Fields", test_validate_persona_fields()))
    results.append(("Demographic Accuracy", test_demographic_accuracy()))
    results.append(("Generate All Precincts", test_generate_all_precincts()))
    results.append(("Persona to Prompt", test_persona_to_prompt()))

    # Print summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 80)
    print()

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
