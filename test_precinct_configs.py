#!/usr/bin/env python3
"""Test script to validate precinct configuration files."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.persona import PrecinctConfig


def test_load_sf_precincts():
    """Test loading San Francisco precinct configurations."""
    print("=" * 80)
    print("TEST 1: Load SF Precinct Configurations")
    print("=" * 80)

    config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        print(f"✓ Loaded SF precincts from {config_path}")
        print(f"  Total precincts: {len(data['precincts'])}")

        # Validate each precinct
        for i, precinct_data in enumerate(data["precincts"]):
            try:
                precinct = PrecinctConfig(**precinct_data)
                print(f"\n  Precinct {i + 1}: {precinct.name} ({precinct.id})")
                print(f"    State: {precinct.state}, County: {precinct.county}")
                print(f"    Expected voters: {precinct.expected_voters}")
                print(f"    Demographics:")
                print(
                    f"      - Age groups: {len(precinct.demographics.get('age_distribution', {}))}"
                )
                print(
                    f"      - Race categories: {len(precinct.demographics.get('race_distribution', {}))}"
                )
                print(
                    f"      - Education levels: {len(precinct.demographics.get('education_distribution', {}))}"
                )
                print(
                    f"      - Party affiliations: {len(precinct.demographics.get('party_distribution', {}))}"
                )
                print(
                    f"      - Income brackets: {len(precinct.demographics.get('income_distribution', {}))}"
                )

                # Validate distributions sum to ~1.0
                for dist_name, distribution in precinct.demographics.items():
                    if isinstance(distribution, dict) and dist_name.endswith(
                        "_distribution"
                    ):
                        total = sum(distribution.values())
                        if abs(total - 1.0) > 0.01:
                            print(
                                f"    ⚠ WARNING: {dist_name} sums to {total:.3f} (expected 1.0)"
                            )

            except Exception as e:
                print(f"  ✗ ERROR validating precinct {i + 1}: {e}")
                return False

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR loading SF precincts: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_load_miami_precincts():
    """Test loading Miami-Dade precinct configurations."""
    print("=" * 80)
    print("TEST 2: Load Miami-Dade Precinct Configurations")
    print("=" * 80)

    config_path = Path(__file__).parent / "data" / "config" / "precincts_miami.json"

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        print(f"✓ Loaded Miami-Dade precincts from {config_path}")
        print(f"  Total precincts: {len(data['precincts'])}")

        # Validate each precinct
        for i, precinct_data in enumerate(data["precincts"]):
            try:
                precinct = PrecinctConfig(**precinct_data)
                print(f"\n  Precinct {i + 1}: {precinct.name} ({precinct.id})")
                print(f"    State: {precinct.state}, County: {precinct.county}")
                print(f"    Expected voters: {precinct.expected_voters}")
                print(f"    Demographics:")
                print(
                    f"      - Age groups: {len(precinct.demographics.get('age_distribution', {}))}"
                )
                print(
                    f"      - Race categories: {len(precinct.demographics.get('race_distribution', {}))}"
                )
                print(
                    f"      - Education levels: {len(precinct.demographics.get('education_distribution', {}))}"
                )
                print(
                    f"      - Party affiliations: {len(precinct.demographics.get('party_distribution', {}))}"
                )
                print(
                    f"      - Income brackets: {len(precinct.demographics.get('income_distribution', {}))}"
                )

                # Validate distributions sum to ~1.0
                for dist_name, distribution in precinct.demographics.items():
                    if isinstance(distribution, dict) and dist_name.endswith(
                        "_distribution"
                    ):
                        total = sum(distribution.values())
                        if abs(total - 1.0) > 0.01:
                            print(
                                f"    ⚠ WARNING: {dist_name} sums to {total:.3f} (expected 1.0)"
                            )

            except Exception as e:
                print(f"  ✗ ERROR validating precinct {i + 1}: {e}")
                return False

        print()
        return True

    except Exception as e:
        print(f"✗ ERROR loading Miami-Dade precincts: {e}")
        import traceback

        traceback.print_exc()
        print()
        return False


def test_precinct_summary():
    """Generate summary statistics across all precincts."""
    print("=" * 80)
    print("TEST 3: Precinct Summary Statistics")
    print("=" * 80)

    all_precincts = []

    # Load SF precincts
    sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
    with open(sf_config_path, "r") as f:
        sf_data = json.load(f)
        for precinct_data in sf_data["precincts"]:
            all_precincts.append(PrecinctConfig(**precinct_data))

    # Load Miami precincts
    miami_config_path = (
        Path(__file__).parent / "data" / "config" / "precincts_miami.json"
    )
    with open(miami_config_path, "r") as f:
        miami_data = json.load(f)
        for precinct_data in miami_data["precincts"]:
            all_precincts.append(PrecinctConfig(**precinct_data))

    print(f"✓ Loaded total of {len(all_precincts)} precincts")

    # Count by state
    sf_precincts = [p for p in all_precincts if p.state == "CA"]
    miami_precincts = [p for p in all_precincts if p.state == "FL"]

    print(f"\n  By State:")
    print(f"    California (SF): {len(sf_precincts)} precincts")
    print(f"    Florida (Miami-Dade): {len(miami_precincts)} precincts")

    # Total expected voters
    total_voters_sf = sum(p.expected_voters for p in sf_precincts)
    total_voters_miami = sum(p.expected_voters for p in miami_precincts)
    total_voters = total_voters_sf + total_voters_miami

    print(f"\n  Expected Voters:")
    print(f"    SF: {total_voters_sf:,}")
    print(f"    Miami-Dade: {total_voters_miami:,}")
    print(f"    Total: {total_voters:,}")

    # Average party distribution
    print(f"\n  Average Party Distribution:")
    party_avg = {}
    for precinct in all_precincts:
        party_dist = precinct.demographics.get("party_distribution", {})
        for party, pct in party_dist.items():
            if party not in party_avg:
                party_avg[party] = 0
            party_avg[party] += pct

    for party in party_avg:
        party_avg[party] /= len(all_precincts)

    # Sort by percentage
    sorted_parties = sorted(party_avg.items(), key=lambda x: x[1], reverse=True)
    for party, pct in sorted_parties:
        print(f"    {party}: {pct:.1%}")

    print()
    return True


def test_demographic_diversity():
    """Test demographic diversity across precincts."""
    print("=" * 80)
    print("TEST 4: Demographic Diversity Analysis")
    print("=" * 80)

    all_precincts = []

    # Load all precincts
    sf_config_path = Path(__file__).parent / "data" / "config" / "precincts_sf.json"
    with open(sf_config_path, "r") as f:
        sf_data = json.load(f)
        for precinct_data in sf_data["precincts"]:
            all_precincts.append(PrecinctConfig(**precinct_data))

    miami_config_path = (
        Path(__file__).parent / "data" / "config" / "precincts_miami.json"
    )
    with open(miami_config_path, "r") as f:
        miami_data = json.load(f)
        for precinct_data in miami_data["precincts"]:
            all_precincts.append(PrecinctConfig(**precinct_data))

    print(f"✓ Analyzing {len(all_precincts)} precincts")

    # Race diversity
    print(f"\n  Race Diversity:")
    for precinct in all_precincts:
        race_dist = precinct.demographics.get("race_distribution", {})
        sorted_races = sorted(race_dist.items(), key=lambda x: x[1], reverse=True)
        top_race = sorted_races[0] if sorted_races else ("Unknown", 0)
        print(f"    {precinct.name}: {top_race[0]} ({top_race[1]:.1%})")

    # Ideology diversity
    print(f"\n  Ideology Diversity:")
    for precinct in all_precincts:
        ideology_dist = precinct.demographics.get("ideology_distribution", {})
        sorted_ideologies = sorted(
            ideology_dist.items(), key=lambda x: x[1], reverse=True
        )
        top_ideology = sorted_ideologies[0] if sorted_ideologies else ("Unknown", 0)
        print(f"    {precinct.name}: {top_ideology[0]} ({top_ideology[1]:.1%})")

    # Income diversity
    print(f"\n  Income Diversity (High Income >$150K):")
    for precinct in all_precincts:
        income_dist = precinct.demographics.get("income_distribution", {})
        high_income = income_dist.get(">$200K", 0) + income_dist.get("$150K-$200K", 0)
        print(f"    {precinct.name}: {high_income:.1%}")

    print()
    return True


def run_all_tests():
    """Run all precinct configuration tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "PRECINCT CONFIG TESTS" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    results = []

    # Run tests
    results.append(("Load SF Precincts", test_load_sf_precincts()))
    results.append(("Load Miami-Dade Precincts", test_load_miami_precincts()))
    results.append(("Precinct Summary", test_precinct_summary()))
    results.append(("Demographic Diversity", test_demographic_diversity()))

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
