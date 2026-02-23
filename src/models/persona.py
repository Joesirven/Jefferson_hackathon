# src/models/persona.py
"""Synthetic voter persona model."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PrecinctConfig(BaseModel):
    """Configuration for a voting precinct with census demographics."""

    id: str  # Unique precinct identifier (e.g., "SF-P01-Mission")
    name: str  # Human-readable name (e.g., "Mission District")
    state: str  # State code (e.g., "CA", "FL")
    county: str  # County name (e.g., "San Francisco", "Miami-Dade")
    neighborhood: str  # Neighborhood name

    # Census demographics for this precinct
    demographics: Dict[str, Any] = Field(default_factory=dict)

    # Expected number of voters in this precinct
    expected_voters: int = 1000

    # Additional metadata
    description: Optional[str] = None


class PoliticalParty(str, Enum):
    DEMOCRAT = "Democrat"
    REPUBLICAN = "Republican"
    INDEPENDENT = "Independent"
    OTHER = "Other"


class Ideology(str, Enum):
    VERY_LIBERAL = "Very Liberal"
    LIBERAL = "Liberal"
    MODERATE = "Moderate"
    CONSERVATIVE = "Conservative"
    VERY_CONSERVATIVE = "Very Conservative"


class Race(str, Enum):
    WHITE = "White"
    BLACK = "Black"
    HISPANIC = "Hispanic"
    ASIAN = "Asian"
    OTHER = "Other"
    MULTIRACIAL = "Multiracial"


class Education(str, Enum):
    LESS_THAN_HS = "Less than High School"
    HIGH_SCHOOL = "High School"
    SOME_COLLEGE = "Some College"
    COLLEGE = "College Degree"
    POSTGRAD = "Postgraduate Degree"


class Persona(BaseModel):
    """A synthetic voter persona."""

    # Core demographics
    age: int = Field(..., ge=18, le=100)
    gender: str
    race: Race
    education: Education
    income_bracket: str  # e.g., "$50-75K"
    employment_status: str
    marital_status: str

    # Location
    precinct_id: str
    census_block_group: Optional[str] = None
    county: str  # "San Francisco" or "Miami-Dade"
    neighborhood: Optional[str] = None

    # Political
    party_id: PoliticalParty
    ideology: Ideology
    vote_history: Optional[dict] = None  # {"2020": "Biden", "2022": "Democrat"}

    # Issue positions (from survey matching or SOCSCI210 priors)
    top_issues: List[str] = Field(default_factory=list)
    issue_positions: dict = Field(
        default_factory=dict
    )  # {"abortion": "pro-choice", "economy": 6}

    # News sources
    news_sources: List[str] = Field(default_factory=list)

    # Metadata
    source_voter_id: Optional[str] = None  # ID from survey if matched
    socrates_prior: bool = False  # Whether SOCSCI210 data was used
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_prompt(self, news_context: str = "") -> str:
        """Convert persona to LLM prompt."""
        # Handle both enum and string types (due to use_enum_values = True)
        race_val = self.race.value if hasattr(self.race, "value") else self.race
        edu_val = (
            self.education.value if hasattr(self.education, "value") else self.education
        )
        party_val = (
            self.party_id.value if hasattr(self.party_id, "value") else self.party_id
        )
        ideology_val = (
            self.ideology.value if hasattr(self.ideology, "value") else self.ideology
        )

        return f"""You are a {self.age}-year-old {race_val} {self.gender} from {self.neighborhood or self.county}.

Personal details:
- Education: {edu_val}
- Income: {self.income_bracket}
- Employment: {self.employment_status}
- Marital status: {self.marital_status}

Political views:
- Party: {party_val}
- Ideology: {ideology_val}
- Top issues you care about: {", ".join(self.top_issues[:3])}
- You primarily get news from: {", ".join(self.news_sources[:3])}

{f"Recent local news context:\n{news_context}\n" if news_context else ""}

Answer as this voter would respond, based on your demographics, ideology, and life experience."""

    class Config:
        use_enum_values = True


class AgentState(BaseModel):
    """Runtime state of an agent during simulation."""

    persona: Persona
    current_opinions: dict = Field(default_factory=dict)
    interactions_count: int = 0
    last_news_update: Optional[datetime] = None


class PollQuestion(BaseModel):
    """A poll question to ask agents."""

    id: str
    question: str
    question_type: str  # "choice", "scale", "open"
    options: Optional[List[str]] = None  # For choice questions
    scale_range: Optional[tuple] = None  # For scale questions (1, 7)


class PollResponse(BaseModel):
    """An agent's response to a poll question."""

    agent_id: str
    question_id: str
    response: str
    confidence: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
