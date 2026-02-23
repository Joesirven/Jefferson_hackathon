# src/flows/ingestion.py
"""Data ingestion flows for surveys, ACS data, and news."""

import asyncio
from typing import Any, Dict, List, Optional

from prefect import flow, get_run_logger, task

from src.models.persona import Education, Ideology, Persona, PoliticalParty, Race

# ============================================================================
# SURVEY DATA INGESTION
# ============================================================================


@task(name="parse_top_survey")
async def parse_top_survey(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse TOP (Tracking of Polls) survey data.

    Expected columns:
    - AGE_GROUPS, EDUCATION, gender, race, faminc_new, etc.
    - PARTY_ID_COMBINED, IDEO5, ideo3
    - FAVOR04_*: policy position questions
    - issues_top5_*: ranked issue importance
    - SOURCES1_*: news sources
    """
    import pandas as pd

    logger = get_run_logger()

    logger.info(f"Parsing TOP survey from {file_path}")
    df = pd.read_csv(file_path, sep="\t")

    # Map survey codes to values
    mappings = get_top_survey_mappings()

    records = []
    for _, row in df.iterrows():
        record = {
            "age_group": row.get("AGE_GROUPS"),
            "education": mappings.get("education", {}).get(
                row.get("EDUCATION"), row.get("EDUCATION")
            ),
            "gender": mappings.get("gender", {}).get(row.get("gender"), row.get("gender")),
            "race": mappings.get("race", {}).get(row.get("RACE"), row.get("RACE")),
            "income": mappings.get("income", {}).get(row.get("faminc_new"), row.get("faminc_new")),
            "party_id": mappings.get("party", {}).get(
                row.get("PARTY_ID_COMBINED"), row.get("PARTY_ID_COMBINED")
            ),
            "ideology": mappings.get("ideology", {}).get(row.get("IDEO5"), row.get("IDEO5")),
            "vote_history": extract_vote_history(row),
            "issue_positions": extract_favor04_positions(row),
            "top_issues": extract_top_issues(row),
            "news_sources": extract_news_sources(row),
        }
        records.append(record)

    logger.info(f"Parsed {len(records)} survey responses")
    return records


@task(name="save_survey_to_db")
async def save_survey_to_db(survey_data: List[Dict[str, Any]], table: str = "survey_responses"):
    """Save parsed survey data to Supabase."""
    from src.tasks.database import get_supabase_client

    logger = get_run_logger()

    # Insert in batches
    batch_size = 1000
    inserted = 0

    for i in range(0, len(survey_data), batch_size):
        batch = survey_data[i : i + batch_size]
        result = get_supabase_client().table(table).insert(batch).execute()
        inserted += len(batch)
        logger.info(f"Inserted {inserted}/{len(survey_data)} records")

    logger.info(f"Saved {len(survey_data)} survey responses to {table}")
    return {"table": table, "count": len(survey_data)}


def get_top_survey_mappings() -> Dict[str, Dict]:
    """Return code-to-value mappings for TOP survey."""
    return {
        "education": {
            1: "Less than High School",
            2: "High School",
            3: "Some College",
            4: "College Degree",
            5: "Postgraduate Degree",
        },
        "gender": {1: "Male", 2: "Female"},
        "party": {1: "Democrat", 2: "Republican", 3: "Independent", 4: "Other"},
        "ideology": {
            1: "Very Liberal",
            2: "Liberal",
            3: "Moderate",
            4: "Conservative",
            5: "Very Conservative",
        },
    }


def extract_vote_history(row) -> Dict:
    """Extract vote history from survey row."""
    return {
        "2020_president": row.get("VOTE_CHOICE_INDEX_2020"),
        "congress_vote": row.get("GENERIC_CONGRESS_VOTE_W_LEAN"),
    }


def extract_favor04_positions(row) -> Dict:
    """Extract FAVOR04 issue positions."""
    positions = {}
    for col in row.index:
        if col.startswith("FAVOR04_"):
            positions[col] = row.get(col)
    return positions


def extract_top_issues(row) -> List[str]:
    """Extract top issues from issues_top5 columns."""
    issues = []
    for col in sorted([c for c in row.index if c.startswith("issues_top5_")]):
        if pd.notna(row.get(col)):
            issues.append(row.get(col))
    return issues[:5]


def extract_news_sources(row) -> List[str]:
    """Extract news sources from SOURCES1 columns."""
    sources = []
    for col in sorted([c for c in row.index if c.startswith("SOURCES1_")]):
        if row.get(col) == 1:  # Assuming 1 means they use this source
            source_name = col.replace("SOURCES1_", "").replace("_", " ").title()
            sources.append(source_name)
    return sources


# ============================================================================
# ACS DATA INGESTION
# ============================================================================


@task(name="fetch_acs_data")
async def fetch_acs_data(state: str, county: str, tables: List[str] = None) -> Dict[str, Any]:
    """
    Fetch ACS data from Census API for a county.

    Tables: DP05 (demographics), DP03 (economic), DP02 (social)
    """
    import census

    logger = get_run_logger()

    if tables is None:
        tables = ["DP05", "DP03", "DP02"]

    logger.info(f"Fetching ACS data for {county}, {state}")

    # You'd need to install: pip install census
    # And get API key from: https://api.census.gov/data/key_signup.html

    results = {}
    for table in tables:
        # Placeholder - implement actual Census API call
        results[table] = {"data": "census_data_placeholder"}

    return results


@task(name="map_census_to_precincts")
async def map_census_to_precincts(
    census_data: Dict[str, Any], precinct_shapefile: str
) -> Dict[str, Any]:
    """Map census block groups to precincts using spatial overlap."""
    import geopandas as gpd

    # Load precinct boundaries
    precincts = gpd.read_file(precinct_shapefile)

    # For each census block group, find which precinct it falls in
    # Return mapping: {precinct_id: {demographics: {...}}}

    return {"mapping": "to_be_implemented"}


# ============================================================================
# PERSONA GENERATION
# ============================================================================


@task(name="generate_personas_for_precinct")
async def generate_personas_for_precinct(
    precinct_id: str,
    census_demographics: Dict[str, Any],
    survey_data: List[Dict[str, Any]],
    num_voters: int,
    use_socrates_prior: bool = True,
) -> List[Persona]:
    """
    Generate synthetic personas for a precinct.

    Strategy:
    1. Get demographic distribution from census
    2. Find matching survey respondents for each demographic bin
    3. Use survey responses to build persona templates
    4. Generate N personas matching the distribution
    5. Optionally: use SOCSCI210 priors for missing data
    """
    logger = get_run_logger()
    logger.info(f"Generating {num_voters} personas for precinct {precinct_id}")

    personas = []

    # Build demographic bins from census data
    # Match to survey respondents
    # Generate personas

    # Placeholder implementation
    for i in range(min(num_voters, 10)):  # Limit for demo
        personas.append(
            Persona(
                age=35 + i % 30,
                gender="Male" if i % 2 else "Female",
                race=Race.WHITE,
                education=Education.COLLEGE,
                income_bracket="$75-100K",
                employment_status="Employed",
                marital_status="Married",
                precinct_id=precinct_id,
                county="San Francisco",
                party_id=PoliticalParty.DEMOCRAT,
                ideology=Ideology.LIBERAL,
                top_issues=["Housing", "Transportation", "Climate"],
                news_sources=["SF Chronicle", "Twitter"],
                socrates_prior=use_socrates_prior,
            )
        )

    logger.info(f"Generated {len(personas)} personas")
    return personas


# ============================================================================
# MAIN INGESTION FLOW
# ============================================================================


@flow(name="ingest_all_data")
async def ingest_all_data(
    survey_files: List[str], precinct_ids: List[str], use_socrates: bool = True
) -> Dict[str, Any]:
    """
    Main ingestion flow: surveys, ACS data, generate personas.
    """
    logger = get_run_logger()

    results = {"surveys": {}, "acs": {}, "personas": {}}

    # Ingest survey data
    for survey_file in survey_files:
        logger.info(f"Ingesting survey: {survey_file}")
        survey_data = await parse_top_survey(survey_file)
        save_result = await save_survey_to_db(survey_data)
        results["surveys"][survey_file] = save_result

    # Fetch and map ACS data for each county
    for county in ["San Francisco", "Miami-Dade"]:
        acs_data = await fetch_acs_data("CA", county)
        results["acs"][county] = acs_data

    # Generate personas for each precinct
    for precinct_id in precinct_ids:
        personas = await generate_personas_for_precinct(
            precinct_id=precinct_id,
            census_demographics={},
            survey_data=[],
            num_voters=1000,
            use_socrates_prior=use_socrates,
        )
        # Save personas to database
        results["personas"][precinct_id] = len(personas)

    return results


# ============================================================================
# NEWS INGESTION
# ============================================================================


@task(name="ingest_news")
async def ingest_news(county: str, hours_back: int = 48) -> List[Dict[str, Any]]:
    """Scrape and ingest recent news for a county."""
    from src.tasks.news import NewsScraper

    logger = get_run_logger()

    scraper = NewsScraper()
    articles = await scraper.scrape_local_news(county, hours_back)

    logger.info(f"Ingested {len(articles)} articles for {county}")

    # Save to database
    from src.tasks.database import get_supabase_client

    for article in articles:
        article["county"] = county
        get_supabase_client().table("news_articles").upsert(article).execute()

    return articles
