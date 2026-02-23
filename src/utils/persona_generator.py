"""Persona generation utility for creating synthetic voters."""

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from models.persona import (
    Education,
    Ideology,
    Persona,
    PoliticalParty,
    PrecinctConfig,
    Race,
)
from utils.survey_parser import TOPSurveyParser, load_survey_data

logger = logging.getLogger(__name__)


class PersonaGenerator:
    """Generate synthetic voter personas from precinct configs and survey data."""

    def __init__(self, survey_dir: str):
        """
        Initialize persona generator.

        Args:
            survey_dir: Path to survey data directory
        """
        self.survey_parser = load_survey_data(survey_dir)
        self.precinct_configs: List[PrecinctConfig] = []

        logger.info(
            f"Initialized PersonaGenerator with survey data: {len(self.survey_parser.all_respondents)} respondents"
        )

    def load_precinct_configs(self, config_path: Path) -> None:
        """
        Load precinct configurations from JSON file.

        Args:
            config_path: Path to JSON config file (e.g., precincts_sf.json)
        """
        with open(config_path, "r") as f:
            data = json.load(f)

        for precinct_data in data["precincts"]:
            precinct = PrecinctConfig(**precinct_data)
            self.precinct_configs.append(precinct)

        logger.info(
            f"Loaded {len(self.precinct_configs)} precinct configurations from {config_path}"
        )

    def generate_voters_for_precinct(
        self, precinct: PrecinctConfig, num_voters: int
    ) -> List[Persona]:
        """
        Generate synthetic voters for a precinct.

        Args:
            precinct: Precinct configuration
            num_voters: Number of voters to generate

        Returns:
            List of Persona objects
        """
        logger.info(
            f"Generating {num_voters} voters for precinct {precinct.id} ({precinct.name})"
        )

        voters = []

        for i in range(num_voters):
            # Sample demographics from precinct distribution
            voter_demographics = self._sample_demographics(precinct)

            # Find matching survey respondents
            matches = self.survey_parser.find_matches(
                age_group=voter_demographics["age_group"],
                race=voter_demographics["race"],
                gender=voter_demographics["gender"],
                education=voter_demographics["education"],
                party_id=voter_demographics.get("party_id"),
                max_matches=20,
            )

            if not matches:
                # If no matches found, create fallback persona with demographic priors only
                persona = self._create_fallback_persona(precinct, voter_demographics, i)
            else:
                # Select a random match from the matches
                match = random.choice(matches)
                # Create persona from survey match (use survey demographics as priors)
                persona = self._create_persona_from_match(
                    precinct, voter_demographics, match, i
                )

            voters.append(persona)

        logger.info(f"Generated {len(voters)} voters for {precinct.id}")
        return voters

    def _sample_demographics(self, precinct: PrecinctConfig) -> Dict[str, str]:
        """
        Sample demographic attributes from precinct distributions.

        Args:
            precinct: Precinct configuration

        Returns:
            Dictionary of sampled demographic attributes
        """
        demographics = precinct.demographics

        # Sample from each distribution
        age_group = self._sample_from_distribution(
            demographics.get("age_distribution", {})
        )
        race = self._sample_from_distribution(demographics.get("race_distribution", {}))
        gender = self._sample_gender(demographics.get("race_distribution", {}), race)
        education = self._sample_from_distribution(
            demographics.get("education_distribution", {})
        )
        income_bracket = self._sample_from_distribution(
            demographics.get("income_distribution", {})
        )
        employment_status = self._sample_from_distribution(
            demographics.get("employment_status", {})
        )
        marital_status = self._sample_from_distribution(
            demographics.get("marital_status", {})
        )
        party_id = self._sample_from_distribution(
            demographics.get("party_distribution", {})
        )
        ideology = self._sample_from_distribution(
            demographics.get("ideology_distribution", {})
        )

        # Convert age_group to specific age (midpoint of range)
        age = self._convert_age_group_to_age(age_group)

        return {
            "age": age,
            "age_group": age_group,
            "gender": gender,
            "race": race,
            "education": education,
            "income_bracket": income_bracket,
            "employment_status": employment_status,
            "marital_status": marital_status,
            "party_id": party_id,
            "ideology": ideology,
        }

    def _sample_from_distribution(self, distribution: Dict[str, float]) -> str:
        """
        Sample a value from a probability distribution.

        Args:
            distribution: Dictionary mapping values to probabilities

        Returns:
            Sampled value
        """
        if not distribution:
            return "Unknown"

        values = list(distribution.keys())
        probabilities = list(distribution.values())

        # Normalize probabilities
        total = sum(probabilities)
        if total > 0:
            probabilities = [p / total for p in probabilities]

        return random.choices(values, weights=probabilities, k=1)[0]

    def _sample_gender(self, race_dist: Dict[str, float], sampled_race: str) -> str:
        """
        Sample gender based on race demographics.

        Args:
            race_dist: Race distribution for precinct
            sampled_race: The sampled race value

        Returns:
            Sampled gender
        """
        # Base gender distribution (slightly more women in surveys)
        gender_dist = {"Man": 0.48, "Woman": 0.52}

        # Adjust based on race (simplified)
        if sampled_race == "Asian":
            gender_dist = {"Man": 0.50, "Woman": 0.50}
        elif sampled_race == "Black":
            gender_dist = {"Man": 0.46, "Woman": 0.54}

        return self._sample_from_distribution(gender_dist)

    def _convert_age_group_to_age(self, age_group: str) -> int:
        """
        Convert age group string to specific age (midpoint).

        Args:
            age_group: Age group string (e.g., "18-29", "30-44")

        Returns:
            Specific age integer
        """
        age_map = {
            "18-29": 24,
            "30-39": 35,
            "40-49": 45,
            "50-64": 57,
            "65+": 72,
        }

        # Add some randomness around midpoint
        midpoint = age_map.get(age_group, 40)
        variation = random.randint(-3, 3)
        return max(18, min(100, midpoint + variation))

    def _create_persona_from_match(
        self,
        precinct: PrecinctConfig,
        voter_demographics: Dict[str, Any],
        match: Any,
        index: int,
    ) -> Persona:
        """
        Create a Persona object from a survey match.

        Uses census demographics for base attributes, but incorporates
        survey data for issue positions, news sources, and values.

        Args:
            precinct: Precinct configuration
            voter_demographics: Sampled census demographics
            match: Matching SurveyRespondent object
            index: Index for unique ID

        Returns:
            Persona object
        """
        # Map race to enum
        race_map = {
            "White": Race.WHITE,
            "Black": Race.BLACK,
            "Hispanic": Race.HISPANIC,
            "Asian": Race.ASIAN,
            "Other": Race.OTHER,
            "Multiracial": Race.MULTIRACIAL,
        }
        race_enum = race_map.get(voter_demographics["race"], Race.OTHER)

        # Map education to enum (matching survey data values)
        edu_map = {
            "No HS": Education.LESS_THAN_HS,
            "High school graduate": Education.HIGH_SCHOOL,
            "2-year": Education.SOME_COLLEGE,
            "4-year": Education.COLLEGE,
            "Post-grad": Education.POSTGRAD,
        }
        edu_enum = edu_map.get(voter_demographics["education"], Education.SOME_COLLEGE)

        # Map party to enum
        party_map = {
            "Strong Democrat": PoliticalParty.DEMOCRAT,
            "Democrat": PoliticalParty.DEMOCRAT,
            "Independent/Lean Democrat": PoliticalParty.INDEPENDENT,
            "Independent/Lean Republican": PoliticalParty.INDEPENDENT,
            "Republican": PoliticalParty.REPUBLICAN,
            "Strong Republican": PoliticalParty.REPUBLICAN,
        }
        party_enum = party_map.get(
            voter_demographics["party_id"], PoliticalParty.INDEPENDENT
        )

        # Map ideology to enum
        ideology_map = {
            "Very Liberal": Ideology.VERY_LIBERAL,
            "Liberal": Ideology.LIBERAL,
            "Moderate": Ideology.MODERATE,
            "Conservative": Ideology.CONSERVATIVE,
            "Very Conservative": Ideology.VERY_CONSERVATIVE,
        }
        ideology_enum = ideology_map.get(
            voter_demographics["ideology"], Ideology.MODERATE
        )

        # Create persona
        persona = Persona(
            age=voter_demographics["age"],
            gender=voter_demographics["gender"],
            race=race_enum,
            education=edu_enum,
            income_bracket=voter_demographics["income_bracket"],
            employment_status=voter_demographics["employment_status"],
            marital_status=voter_demographics["marital_status"],
            precinct_id=precinct.id,
            county=precinct.county,
            neighborhood=precinct.neighborhood,
            party_id=party_enum,
            ideology=ideology_enum,
            # Use survey data for issue positions and news sources
            top_issues=match.top_issues[:10] if match.top_issues else [],
            issue_positions=match.issue_positions,
            news_sources=match.news_sources[:8] if match.news_sources else [],
            source_voter_id=match.dwid,
            socrates_prior=False,  # Using TOP survey data
        )

        return persona

    def _create_fallback_persona(
        self, precinct: PrecinctConfig, voter_demographics: Dict[str, Any], index: int
    ) -> Persona:
        """
        Create a fallback Persona when no survey match is found.

        Uses only census demographics with generic issue positions.

        Args:
            precinct: Precinct configuration
            voter_demographics: Sampled census demographics
            index: Index for unique ID

        Returns:
            Persona object
        """
        # Map race to enum
        race_map = {
            "White": Race.WHITE,
            "Black": Race.BLACK,
            "Hispanic": Race.HISPANIC,
            "Asian": Race.ASIAN,
            "Other": Race.OTHER,
            "Multiracial": Race.MULTIRACIAL,
        }
        race_enum = race_map.get(voter_demographics["race"], Race.OTHER)

        # Map education to enum (matching survey data values)
        edu_map = {
            "No HS": Education.LESS_THAN_HS,
            "High school graduate": Education.HIGH_SCHOOL,
            "2-year": Education.SOME_COLLEGE,
            "4-year": Education.COLLEGE,
            "Post-grad": Education.POSTGRAD,
        }
        edu_enum = edu_map.get(voter_demographics["education"], Education.SOME_COLLEGE)

        # Map party to enum
        party_map = {
            "Strong Democrat": PoliticalParty.DEMOCRAT,
            "Democrat": PoliticalParty.DEMOCRAT,
            "Independent/Lean Democrat": PoliticalParty.INDEPENDENT,
            "Independent/Lean Republican": PoliticalParty.INDEPENDENT,
            "Republican": PoliticalParty.REPUBLICAN,
            "Strong Republican": PoliticalParty.REPUBLICAN,
        }
        party_enum = party_map.get(
            voter_demographics["party_id"], PoliticalParty.INDEPENDENT
        )

        # Map ideology to enum
        ideology_map = {
            "Very Liberal": Ideology.VERY_LIBERAL,
            "Liberal": Ideology.LIBERAL,
            "Moderate": Ideology.MODERATE,
            "Conservative": Ideology.CONSERVATIVE,
            "Very Conservative": Ideology.VERY_CONSERVATIVE,
        }
        ideology_enum = ideology_map.get(
            voter_demographics["ideology"], Ideology.MODERATE
        )

        # Generate generic top issues based on ideology
        top_issues = self._generate_generic_issues(ideology_enum)

        # Generate generic news sources
        news_sources = self._generate_generic_news_sources(
            ideology_enum, voter_demographics["age"]
        )

        persona = Persona(
            age=voter_demographics["age"],
            gender=voter_demographics["gender"],
            race=race_enum,
            education=edu_enum,
            income_bracket=voter_demographics["income_bracket"],
            employment_status=voter_demographics["employment_status"],
            marital_status=voter_demographics["marital_status"],
            precinct_id=precinct.id,
            county=precinct.county,
            neighborhood=precinct.neighborhood,
            party_id=party_enum,
            ideology=ideology_enum,
            top_issues=top_issues,
            issue_positions={},  # Empty - no survey match
            news_sources=news_sources,
            source_voter_id=None,  # No survey match
            socrates_prior=False,
        )

        return persona

    def _generate_generic_issues(self, ideology: Ideology) -> List[str]:
        """
        Generate generic top issues based on ideology.

        Args:
            ideology: Voter ideology

        Returns:
            List of issue strings
        """
        issue_sets = {
            Ideology.VERY_LIBERAL: [
                "Climate change",
                "Social justice",
                "Healthcare access",
                "Economic inequality",
                "Voting rights",
            ],
            Ideology.LIBERAL: [
                "Healthcare",
                "Education",
                "Economy",
                "Climate change",
                "Social services",
            ],
            Ideology.MODERATE: [
                "Economy",
                "Healthcare",
                "Immigration",
                "Education",
                "National security",
            ],
            Ideology.CONSERVATIVE: [
                "Economy",
                "National security",
                "Immigration",
                "Gun rights",
                "Tax reform",
            ],
            Ideology.VERY_CONSERVATIVE: [
                "Gun rights",
                "Immigration",
                "National debt",
                "Traditional values",
                "Energy independence",
            ],
        }

        issues = issue_sets.get(ideology, issue_sets[Ideology.MODERATE])
        return random.sample(issues, min(5, len(issues)))

    def _generate_generic_news_sources(self, ideology: Ideology, age: int) -> List[str]:
        """
        Generate generic news sources based on ideology and age.

        Args:
            ideology: Voter ideology
            age: Voter age

        Returns:
            List of news source strings
        """
        # Younger voters use different sources
        if age < 35:
            young_sources = [
                "Twitter/X",
                "TikTok",
                "Instagram",
                "YouTube",
                "CNN",
                "MSNBC",
                "Fox News",
                "Reuters",
            ]
            return random.sample(young_sources, 3)
        else:
            older_sources = [
                "Cable news",
                "Local TV news",
                "Newspapers",
                "Facebook",
                "Fox News",
                "CNN",
                "MSNBC",
                "NPR",
            ]
            return random.sample(older_sources, 3)

    def generate_all_precincts(
        self, num_voters_per_precinct: int = 50
    ) -> Dict[str, List[Persona]]:
        """
        Generate voters for all loaded precincts.

        Args:
            num_voters_per_precinct: Number of voters to generate per precinct

        Returns:
            Dictionary mapping precinct_id to list of Persona objects
        """
        logger.info(
            f"Generating {num_voters_per_precinct} voters for each of {len(self.precinct_configs)} precincts"
        )

        all_voters = {}

        for precinct in self.precinct_configs:
            voters = self.generate_voters_for_precinct(
                precinct, num_voters_per_precinct
            )
            all_voters[precinct.id] = voters

        total_voters = sum(len(voters) for voters in all_voters.values())
        logger.info(
            f"Generated total of {total_voters} voters across {len(all_voters)} precincts"
        )

        return all_voters
