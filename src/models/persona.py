# src/models/persona.py
"""Synthetic voter persona model."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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
        return f"""You are a {self.age}-year-old {self.race.value} {self.gender} from {self.neighborhood or self.county}.

Personal details:
- Education: {self.education.value}
- Income: {self.income_bracket}
- Employment: {self.employment_status}
- Marital status: {self.marital_status}

Political views:
- Party: {self.party_id.value}
- Ideology: {self.ideology.value}
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
