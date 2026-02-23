# src/tasks/database.py
"""Database connection and queries using Supabase."""

import os
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from src.models.persona import Persona

# Supabase client
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client."""
    global _supabase_client

    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")  # or service role key

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment. "
                "Get them from your Supabase project settings."
            )

        _supabase_client = create_client(supabase_url, supabase_key)

    return _supabase_client


# ============================================================================
# PERSONA QUERIES
# ============================================================================


async def get_personas_by_precinct(precinct_id: str) -> List[Persona]:
    """Get all personas for a precinct."""
    client = get_supabase_client()

    response = client.table("personas").select("*").eq("precinct_id", precinct_id).execute()

    personas = [Persona(**row) for row in response.data]
    return personas


async def save_persona(persona: Persona) -> Dict:
    """Save a persona to the database."""
    client = get_supabase_client()

    response = client.table("personas").insert(persona.dict()).execute()
    return response.data[0]


async def save_personas_batch(personas: List[Persona]) -> List[Dict]:
    """Save multiple personas in a batch."""
    client = get_supabase_client()

    data = [p.dict() for p in personas]
    response = client.table("personas").insert(data).execute()
    return response.data


async def get_persona_count(precinct_id: Optional[str] = None) -> int:
    """Get count of personas, optionally filtered by precinct."""
    client = get_supabase_client()

    query = client.table("personas").select("*", count="exact")
    if precinct_id:
        query = query.eq("precinct_id", precinct_id)

    response = query.execute()
    return response.count


# ============================================================================
# SIMULATION RESULTS
# ============================================================================


async def save_simulation_results(simulation_id: str, results: Dict[str, Any]) -> Dict:
    """Save simulation results."""
    client = get_supabase_client()

    data = {"simulation_id": simulation_id, "results": results, "status": "completed"}

    response = client.table("simulations").upsert(data).execute()
    return response.data[0]


async def get_simulation_results(simulation_id: str) -> Optional[Dict]:
    """Get simulation results by ID."""
    client = get_supabase_client()

    response = client.table("simulations").select("*").eq("simulation_id", simulation_id).execute()

    if response.data:
        return response.data[0]
    return None


async def list_simulations(limit: int = 50) -> List[Dict]:
    """List recent simulations."""
    client = get_supabase_client()

    response = (
        client.table("simulations")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


# ============================================================================
# NEWS CONTEXT
# ============================================================================


async def get_latest_news_context(county: str, hours: int = 24) -> str:
    """Get latest news context for a county."""
    client = get_supabase_client()

    response = (
        client.table("news_articles")
        .select("*")
        .eq("county", county)
        .order("published_at", desc=True)
        .limit(10)
        .execute()
    )

    if not response.data:
        return ""

    # Format as context
    articles = response.data
    context = f"Recent news from {county}:\n"
    for article in articles:
        context += f"- {article.get('title', '')}: {article.get('summary', '')[:100]}...\n"

    return context


# ============================================================================
# SURVEY DATA
# ============================================================================


async def get_matching_survey_respondents(
    age_range: tuple, education: str, race: str, county: Optional[str] = None
) -> List[Dict]:
    """Get survey respondents matching demographics (for persona building)."""
    client = get_supabase_client()

    query = client.table("survey_responses").select("*")

    # Apply filters (simplified - you'd want more sophisticated matching)
    if county:
        query = query.eq("county", county)

    # Note: Supabase doesn't support complex range queries easily
    # You might want to use Postgres RPC functions for this

    response = query.execute()
    return response.data


# ============================================================================
# SCHEMA SETUP (for reference)
# ============================================================================

"""
SQL for Supabase (run in SQL Editor):

-- Personas table
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    race TEXT NOT NULL,
    education TEXT NOT NULL,
    income_bracket TEXT NOT NULL,
    employment_status TEXT NOT NULL,
    marital_status TEXT NOT NULL,
    precinct_id TEXT NOT NULL,
    census_block_group TEXT,
    county TEXT NOT NULL,
    neighborhood TEXT,
    party_id TEXT NOT NULL,
    ideology TEXT NOT NULL,
    vote_history JSONB,
    top_issues TEXT[],
    issue_positions JSONB,
    news_sources TEXT[],
    source_voter_id TEXT,
    socrates_prior BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on precinct_id for faster queries
CREATE INDEX idx_personas_precinct ON personas(precinct_id);
CREATE INDEX idx_personas_county ON personas(county);

-- Simulations table
CREATE TABLE simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id TEXT UNIQUE NOT NULL,
    results JSONB NOT NULL,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Survey responses table
CREATE TABLE survey_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    age_group TEXT,
    education TEXT,
    gender TEXT,
    race TEXT,
    income TEXT,
    party_id TEXT,
    ideology TEXT,
    vote_history JSONB,
    issue_positions JSONB,
    top_issues TEXT[],
    news_sources TEXT[],
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- News articles table
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    content TEXT,
    source TEXT,
    county TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for news queries
CREATE INDEX idx_news_county_date ON news_articles(county, published_at DESC);
"""
