#!/usr/bin/env python3
"""Test script to validate TOP survey parser functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.survey_parser import TOPSurveyParser, load_survey_data


def test_import_survey_respondent():
    """Test that SurveyRespondent dataclass can be imported and instantiated."""
    print("=" * 80)
    print("TEST 1: Import SurveyRespondent dataclass")
    print("=" * 80)

    from utils.survey_parser import SurveyRespondent

    # Create a simple test respondent
    respondent = SurveyRespondent(
        dwid="TEST001",
        age_group="40-49",
        gender="Woman",
        race="White",
        education="College degree",
        income="$100,000 - $149,999",
        employment_status="Employed full time",
        marital_status="Married",
        party_id="Strong Democrat",
        ideology="Moderate",
        vote_2024="Kamala Harris",
        vote_2022="Joe Biden",
        vote_history="4 / 4 votes",
    )

    print(f"✓ Created SurveyRespondent: {respondent.dwid}")
    print(f"  Age: {respondent.age_group}, Gender: {respondent.gender}")
    print(f"  Party: {respondent.party_id}, 2024 Vote: {respondent.vote_2024}")
    print()
    return True


def test_load_survey_data():
    """Test loading survey data from all three waves."""
    print("=" * 80)
    print("TEST 2: Load survey data from all waves")
    print("=" * 80)

    survey_dir = Path(__file__).parent / "data" / "surveys"

    try:
        parser = load_survey_data(survey_dir)

        print(f"✓ Loaded TOP survey data")
        print(f"  Total waves: {len(parser.survey_waves)}")

        for wave_name, respondents in parser.survey_waves.items():
            print(f"  Wave '{wave_name}': {len(respondents)} respondents")

        total_respondents = sum(
            len(respondents) for respondents in parser.survey_waves.values()
        )
        print(f"\n✓ Total respondents across all waves: {total_respondents}")

        print(f"✓ All respondents accessible: {len(parser.all_respondents)}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR loading survey data: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_parse_respondents():
    """Test parsing individual survey respondents."""
    print("=" * 80)
    print("TEST 3: Parse individual survey respondents")
    print("=" * 80)

    survey_dir = Path(__file__).parent / "data" / "surveys"

    try:
        parser = load_survey_data(survey_dir)

        # Access all parsed respondents
        all_respondents = parser.all_respondents

        print(f"✓ Parsed {len(all_respondents)} respondents")

        # Display a few sample respondents
        print("\n--- Sample Respondents ---")
        for i, respondent in enumerate(all_respondents[:3]):
            print(f"\nRespondent {i + 1}: {respondent.dwid}")
            print(
                f"  Demographics: {respondent.age_group} {respondent.gender}, {respondent.race}"
            )
            print(f"  Education: {respondent.education}, Income: {respondent.income}")
            print(f"  Party: {respondent.party_id}, Ideology: {respondent.ideology}")
            print(f"  2024 Vote: {respondent.vote_2024}")
            print(f"  State: {respondent.survey_state or 'N/A'}")
            print(f"  Values Cluster: {respondent.values_cluster or 'N/A'}")
            print(f"  Issue Positions: {len(respondent.issue_positions)}")
            print(f"  Top Issues: {len(respondent.top_issues)}")
            print(f"  News Sources: {len(respondent.news_sources)}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR parsing respondents: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_find_matches():
    """Test finding matching survey respondents."""
    print("=" * 80)
    print("TEST 4: Find demographic matches")
    print("=" * 80)

    survey_dir = Path(__file__).parent / "data" / "surveys"

    try:
        parser = load_survey_data(survey_dir)

        # Define a target demographic to search for (using broader criteria)
        age_group = "50-64"
        gender = "Man"
        race = "White"
        education = "High school graduate"
        party_id = "Strong Republican"

        print(f"Searching for matches:")
        print(f"  age_group: {age_group}")
        print(f"  gender: {gender}")
        print(f"  race: {race}")
        print(f"  education: {education}")
        print(f"  party_id: {party_id}")

        # Find matches
        matches = parser.find_matches(
            age_group=age_group,
            race=race,
            gender=gender,
            education=education,
            party_id=party_id,
            max_matches=15,
        )

        print(f"\n✓ Found {len(matches)} matching respondents")

        if matches:
            print("\n--- Sample Match ---")
            match = matches[0]
            print(f"  ID: {match.dwid}")
            print(f"  Age: {match.age_group}, Gender: {match.gender}")
            print(f"  Education: {match.education}")
            print(f"  Party: {match.party_id}")
            print(f"  2024 Vote: {match.vote_2024}")
            print(f"  State: {match.survey_state or 'N/A'}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR finding matches: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_get_persona_template():
    """Test generating persona template from matches."""
    print("=" * 80)
    print("TEST 5: Generate persona template from matches")
    print("=" * 80)

    survey_dir = Path(__file__).parent / "data" / "surveys"

    try:
        parser = load_survey_data(survey_dir)

        # Define a target demographic (using broader criteria)
        age_group = "50-64"
        gender = "Man"
        race = "White"
        education = "High school graduate"
        party_id = "Strong Republican"

        # Generate persona template (method internally finds matches)
        persona = parser.get_persona_template(
            age_group=age_group,
            race=race,
            gender=gender,
            education=education,
            party_id=party_id,
        )

        if not persona:
            print("✗ No persona template generated")
            return False

        print("✓ Generated persona template:")
        print(f"  Matches used: {persona['voting_behavior']['num_matches']}")
        print(f"  Most common 2024 vote: {persona['voting_behavior']['vote_2024']}")
        print(f"  Issue positions: {len(persona['issue_positions'])} positions")
        print(f"  Top issues: {persona['top_issues'][:5]}")
        print(f"  News sources: {persona['news_sources'][:5]}")

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR generating persona template: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def run_all_tests():
    """Run all validation tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "TOP SURVEY PARSER VALIDATION TESTS" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    results = []

    # Run tests
    results.append(("Import SurveyRespondent", test_import_survey_respondent()))
    results.append(("Load Survey Data", test_load_survey_data()))
    results.append(("Parse Respondents", test_parse_respondents()))
    results.append(("Find Matches", test_find_matches()))
    results.append(("Get Persona Template", test_get_persona_template()))

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
