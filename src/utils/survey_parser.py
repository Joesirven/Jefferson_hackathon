"""TOP Survey Data Parser and Persona Matcher.

This module handles loading, parsing, and matching TOP survey data
for generating realistic voter personas.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SurveyRespondent:
    """A single survey respondent with all relevant fields."""

    # ===== IDENTITY =====
    dwid: str  # Unique identifier from survey

    # ===== DEMOGRAPHICS =====
    age_group: str  # e.g., "40-49"
    gender: str  # e.g., "Woman", "Man"
    race: str  # e.g., "White", "Black", "Hispanic", "Asian"
    education: str  # e.g., "College degree", "High school"
    income: str  # e.g., "$100,000 - $149,999"
    employment_status: str  # e.g., "Employed full time"
    marital_status: str  # e.g., "Married", "Never married"

    # ===== POLITICAL =====
    party_id: str  # e.g., "Strong Democrat", "Lean Republican"
    ideology: str  # e.g., "Very Liberal", "Moderate", "Very Conservative"

    # ===== VOTING HISTORY =====
    vote_2024: str  # e.g., "Kamala Harris", "Donald Trump"
    vote_2022: str  # e.g., "Joe Biden"
    vote_history: str  # e.g., "4 / 4 votes"

    # ===== ISSUE POSITIONS (FAVOR04_*) =====
    issue_positions: Dict[str, str] = field(default_factory=dict)

    # ===== RANKED ISSUES (issues_top5_*) =====
    top_issues: List[str] = field(default_factory=list)

    # ===== NEWS SOURCES (SOURCES1_*) =====
    news_sources: List[str] = field(default_factory=list)

    # ===== VALUES CLUSTER =====
    values_cluster: Optional[str] = None  # e.g., "Super Seculars"

    # ===== LOCATION =====
    survey_state: str = ""  # e.g., "CA", "FL", "NY"
    inputzip: Optional[str] = None  # ZIP code
    county: Optional[str] = None  # County name (can derive from ZIP)

    # ===== RAW DATA =====
    raw_data: Dict[str, Any] = field(default_factory=dict)


class TOPSurveyParser:
    """Parser for TOP (Tracking of Polls) survey data."""

    def __init__(self, survey_dir: str):
        """
        Initialize parser with survey data directory.

        Args:
            survey_dir: Path to data/surveys/ directory
        """
        self.survey_dir = Path(survey_dir)
        self.survey_waves = {}  # {wave_name: List[SurveyRespondent]}
        self.all_respondents = []  # Flattened list of all respondents

        logger.info(f"Initialized TOPSurveyParser with directory: {survey_dir}")

    def load_all_waves(self) -> None:
        """Load all available survey waves from survey directory."""
        logger.info("Loading all survey waves...")

        # Find all survey directories (TOP Oct 2025, TOP Dec 2025, TOP Jan 2026)
        wave_dirs = [d for d in self.survey_dir.iterdir() if d.is_dir()]

        for wave_dir in wave_dirs:
            wave_name = wave_dir.name
            logger.info(f"Loading wave: {wave_name}")

            # Find the data file (top_recodes_recent_wave_*.txt)
            data_files = list(wave_dir.glob("top_recodes_recent_wave_*.txt"))

            if not data_files:
                logger.warning(f"No data file found in {wave_name}")
                continue

            data_file = data_files[0]  # Take first match
            respondents = self._parse_survey_file(data_file)

            self.survey_waves[wave_name] = respondents
            self.all_respondents.extend(respondents)

            logger.info(f"Loaded {len(respondents)} respondents from {wave_name}")

        logger.info(f"Total respondents loaded: {len(self.all_respondents)}")

    def _parse_survey_file(self, file_path: Path) -> List[SurveyRespondent]:
        """
        Parse a single survey data file.

        The files are tab-separated with headers in first row.
        """
        logger.info(f"Parsing file: {file_path}")

        try:
            # Read tab-separated file
            df = pd.read_csv(file_path, sep="\t", low_memory=False)

            logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

            respondents = []

            for _, row in df.iterrows():
                respondent = self._parse_row(row)
                if respondent:  # Skip if parsing failed
                    respondents.append(respondent)

            logger.info(f"Parsed {len(respondents)} valid respondents")
            return respondents

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _parse_row(self, row: pd.Series) -> Optional[SurveyRespondent]:
        """
        Parse a single row of survey data.

        Extracts all relevant fields for persona generation.
        """
        try:
            # ===== IDENTITY =====
            dwid = str(row.get("DWID", ""))

            # ===== DEMOGRAPHICS =====
            age_group = str(row.get("AGE_GROUPS", "")).strip()
            gender = str(row.get("gender", "")).strip()
            race = str(row.get("RACE", "")).strip()
            education = str(row.get("EDUCATION", "")).strip()
            income = str(row.get("faminc_new", "")).strip()
            employment_status = str(row.get("EMPLOYMENT_STATUS", "")).strip()
            marital_status = str(row.get("MARITAL_STATUS", "")).strip()

            # ===== POLITICAL =====
            party_id = str(row.get("PARTY_ID_COMBINED", "")).strip()
            ideology = str(row.get("IDEO5", "")).strip()

            # ===== VOTING HISTORY =====
            vote_2024 = str(row.get("VOTE_CHOICE_INDEX_2024", "")).strip()
            vote_2022 = str(row.get("VOTE_CHOICE_INDEX_2022", "")).strip()
            vote_history = str(row.get("vote_history", "")).strip()

            # ===== ISSUE POSITIONS (FAVOR04_*) =====
            issue_positions = {}
            favor04_cols = [col for col in row.index if col.startswith("FAVOR04_")]
            for col in favor04_cols:
                value = str(row[col]).strip()
                if value and value not in ["N/A", "nan", ""]:
                    # Clean up the issue name
                    issue_name = col.replace("FAVOR04_", "").replace("_", " ").title()
                    issue_positions[issue_name] = value

            # ===== RANKED ISSUES (issues_top5_*) =====
            top_issues = []
            issue_cols = [col for col in row.index if col.startswith("issues_top5_")]
            for col in sorted(issue_cols):
                value = str(row[col]).strip()
                if value and value not in ["N/A", "nan", ""]:
                    top_issues.append(value)

            # ===== NEWS SOURCES (SOURCES1_*) =====
            news_sources = []
            source_cols = [col for col in row.index if col.startswith("SOURCES1_")]
            for col in sorted(source_cols):
                # These are "selected" or "not selected"
                value = str(row[col]).strip()
                if value == "selected":
                    # Clean up the source name
                    source_name = col.replace("SOURCES1_", "").replace("_", " ").title()
                    news_sources.append(source_name)

            # ===== VALUES CLUSTER =====
            values_cluster = str(row.get("PEORIA_VALUES_CLUSTER_2_0", "")).strip()
            if values_cluster in ["N/A", "nan", ""]:
                values_cluster = None

            # ===== LOCATION =====
            survey_state = str(row.get("STATE", "")).strip()
            inputzip = str(row.get("inputzip", "")).strip()

            # Derive county from survey_state (simplified)
            # In production, you'd use a ZIP-to-county lookup
            county_map = {
                "CA": "California",
                "FL": "Florida",
                "NY": "New York",
                "PA": "Pennsylvania",
                "TX": "Texas",
                "IL": "Illinois",
                "GA": "Georgia",
                "NC": "North Carolina",
                "MI": "Michigan",
            }
            county = county_map.get(survey_state)

            # Skip if missing critical fields
            if not all([age_group, gender, race, party_id]):
                return None

            # Store raw data for reference
            raw_data = row.to_dict()

            return SurveyRespondent(
                dwid=dwid,
                age_group=age_group,
                gender=gender,
                race=race,
                education=education,
                income=income,
                employment_status=employment_status,
                marital_status=marital_status,
                party_id=party_id,
                ideology=ideology,
                vote_2024=vote_2024,
                vote_2022=vote_2022,
                vote_history=vote_history,
                issue_positions=issue_positions,
                top_issues=top_issues,
                news_sources=news_sources,
                values_cluster=values_cluster,
                survey_state=survey_state,
                inputzip=inputzip,
                county=county,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            return None

    def find_matches(
        self,
        age_group: str,
        race: str,
        gender: str,
        education: str,
        party_id: Optional[str] = None,
        values_cluster: Optional[str] = None,
        county: Optional[str] = None,
        max_matches: int = 20,
    ) -> List[SurveyRespondent]:
        """
        Find survey respondents matching given demographics.

        Args:
            age_group: e.g., "40-49"
            race: e.g., "White"
            gender: e.g., "Woman"
            education: e.g., "College"
            party_id: Optional - party affiliation
            values_cluster: Optional - PEORIA values cluster
            county: Optional - county/state filter
            max_matches: Maximum number of matches to return

        Returns:
            List of matching SurveyRespondent objects
        """
        matches = []

        for respondent in self.all_respondents:
            # Check demographics
            if not self._match_field(respondent.age_group, age_group):
                continue
            if not self._match_field(respondent.race, race):
                continue
            if not self._match_field(respondent.gender, gender):
                continue
            if not self._match_field(respondent.education, education):
                continue

            # Check optional filters
            if party_id and not self._match_field(respondent.party_id, party_id):
                continue

            if values_cluster and respondent.values_cluster != values_cluster:
                continue

            if county:
                # Check if respondent is from relevant state
                state_map = {"San Francisco": "CA", "Miami-Dade": "FL"}
                target_state = state_map.get(county)
                if respondent.survey_state != target_state:
                    continue

            matches.append(respondent)

            if len(matches) >= max_matches:
                break

        logger.info(
            f"Found {len(matches)} matches for {age_group}, {race}, {gender}, {education}"
        )
        return matches

    def _match_field(self, a: str, b: str) -> bool:
        """Check if two field values match (fuzzy matching for some fields)."""
        # Normalize strings
        a_norm = a.strip().lower()
        b_norm = b.strip().lower()

        # Exact match
        if a_norm == b_norm:
            return True

        # Fuzzy match for education
        if "education" in a_norm.lower() or "education" in b_norm.lower():
            # Map education terms
            edu_map = {
                "college": ["college degree", "some college", "postgraduate"],
                "high": ["high school", "less than high school"],
                "post": ["postgraduate", "post-grad"],
            }
            for key, vals in edu_map.items():
                if any(key in a_norm.lower() or key in b_norm.lower() for val in vals):
                    return True

        return False

    def get_persona_template(
        self,
        age_group: str,
        race: str,
        gender: str,
        education: str,
        party_id: Optional[str] = None,
        values_cluster: Optional[str] = None,
        county: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a persona template by aggregating matching survey respondents.

        Returns a dictionary with averaged/clustered values.
        """
        # Find matching respondents
        matches = self.find_matches(
            age_group=age_group,
            race=race,
            gender=gender,
            education=education,
            party_id=party_id,
            values_cluster=values_cluster,
            county=county,
            max_matches=50,
        )

        if not matches:
            logger.warning(
                f"No matches found for {age_group}, {race}, {gender}, {education}"
            )
            return {}

        # Aggregate issue positions (most common)
        issue_positions = {}
        all_issues = set()
        for respondent in matches:
            for issue, position in respondent.issue_positions.items():
                all_issues.add(issue)

        for issue in all_issues:
            positions = [r.issue_positions.get(issue, "") for r in matches]
            # Get most common non-empty position
            valid_positions = [p for p in positions if p]
            if valid_positions:
                # Use most common
                from collections import Counter

                issue_positions[issue] = Counter(valid_positions).most_common(1)[0][0]

        # Aggregate top issues (rank by frequency)
        all_top_issues = []
        for respondent in matches:
            all_top_issues.extend(respondent.top_issues)

        from collections import Counter

        top_10_issues = [
            issue for issue, count in Counter(all_top_issues).most_common(10)
        ]

        # Aggregate news sources (rank by frequency)
        all_news_sources = []
        for respondent in matches:
            all_news_sources.extend(respondent.news_sources)

        top_8_sources = [
            source for source, count in Counter(all_news_sources).most_common(8)
        ]

        # Aggregate voting behavior (most common)
        vote_2024_common = Counter(
            [r.vote_2024 for r in matches if r.vote_2024]
        ).most_common(1)
        vote_2024_result = vote_2024_common[0][0] if vote_2024_common else "Unknown"

        # Build template
        template = {
            "demographics": {
                "age_group": age_group,
                "race": race,
                "gender": gender,
                "education": education,
                "party_id": party_id or "Unknown",
                "values_cluster": values_cluster or "Unknown",
            },
            "issue_positions": issue_positions,
            "top_issues": top_10_issues,
            "news_sources": top_8_sources,
            "voting_behavior": {
                "vote_2024": vote_2024_result,
                "num_matches": len(matches),
            },
        }

        logger.info(f"Built persona template from {len(matches)} matches")
        return template


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def load_survey_data(survey_dir: str) -> TOPSurveyParser:
    """
    Convenience function to load all survey data.

    Args:
        survey_dir: Path to data/surveys/ directory

    Returns:
        Initialized TOPSurveyParser with all data loaded
    """
    parser = TOPSurveyParser(survey_dir)
    parser.load_all_waves()
    return parser


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python survey_parser.py <survey_directory>")
        sys.exit(1)

    survey_dir = sys.argv[1]
    parser = load_survey_data(survey_dir)

    print(
        f"\nLoaded {len(parser.all_respondents)} respondents from {len(parser.survey_waves)} waves"
    )

    # Example: Find matches
    matches = parser.find_matches(
        age_group="40-49", race="White", gender="Woman", education="College degree"
    )

    print(f"\nFound {len(matches)} matching respondents")
    if matches:
        print(f"\nExample match:")
        print(f"  Age Group: {matches[0].age_group}")
        print(f"  Party: {matches[0].party_id}")
        print(f"  Ideology: {matches[0].ideology}")
        print(f"  Top Issues: {matches[0].top_issues[:3]}")
        print(f"  News Sources: {matches[0].news_sources[:3]}")
