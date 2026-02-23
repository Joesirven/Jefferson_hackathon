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


def extract_abortion_position(row) -> str:
    """Extract abortion stance from survey row."""
    return row.get("ABORTION", "Not specified")


def extract_issue_positions(row) -> Dict:
    """Extract FAVOR04 issue positions and map to readable names."""
    positions = {}

    # Map FAVOR04 columns to issue names and add abortion stance
    for col in row.index:
        if col.startswith("FAVOR04_"):
            issue_map = {
                "FAVOR04_1": "Taxes on goods from other countries",
                "FAVOR04_2": "Growing economy",
                "FAVOR04_3": "Quality of goods",
                "FAVOR04_13": "Tariffs",
                "FAVOR04_14": "Too much government spending",
                "FAVOR04_23": "Abortion",
                "FAVOR04_24": "Health insurance",
                "FAVOR04_26": "Immigration",
                "FAVOR04_36": "Data centers",
            }

            if col in issue_map:
                positions[issue_map[col]] = row.get(col)

    # Add explicit abortion stance
    positions["abortion"] = extract_abortion_position(row)

    return positions


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


# ============================================================================
# PRECINCT CREATION
# ============================================================================


@task(name="create_sf_precincts")
async def create_sf_precincts(survey_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create San Francisco precincts from survey data using ZIP-based clustering."""
    import pandas as pd

    logger = get_run_logger()
    logger.info("Creating SF precincts from survey data")

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(survey_data)

    # Filter to CA only
    sf_data = df[df['party_id'].str.contains('California', case=False, na=False)]

    # Filter to SF ZIP codes (94xxx)
    sf_data = sf_data[sf_data['party_id'].str.contains('94', case=False, na=False)]

    # Create 4 SF precincts based on ZIP code clusters
    precincts = []

    # SF Precinct 1: Mission District (94102-94107) - Younger, diverse, renters
    mission_data = sf_data[sf_data['party_id'].str.match(r'^94[0-7]')]
    precincts.append({
        'id': 'SF-P01-Mission',
        'name': 'Mission District',
        'state': 'CA',
        'county': 'San Francisco',
        'zip_codes': ['94102', '94103', '94104', '94105', '94106', '94107'],
        'demographics': {
            'age_distribution': mission_data['age_group'].value_counts().to_dict() if len(mission_data) > 0 else {},
            'race_distribution': mission_data['race'].value_counts().to_dict() if len(mission_data) > 0 else {},
            'party_distribution': mission_data['party_id'].value_counts().to_dict() if len(mission_data) > 0 else {},
            'ideology_distribution': mission_data['ideology'].value_counts().to_dict() if len(mission_data) > 0 else {},
        },
        'sample_count': len(mission_data) if len(mission_data) > 0 else 0
    })

    # SF Precinct 2: South of Market (94108-94112) - Mid-career professionals, affluent
    soma_data = sf_data[sf_data['party_id'].str.match(r'^94[1-2]')]
    precincts.append({
        'id': 'SF-P02-SoMa',
        'name': 'South of Market',
        'state': 'CA',
        'county': 'San Francisco',
        'zip_codes': ['94108', '94109', '94110', '94111', '94112'],
        'demographics': {
            'age_distribution': soma_data['age_group'].value_counts().to_dict() if len(soma_data) > 0 else {},
            'race_distribution': soma_data['race'].value_counts().to_dict() if len(soma_data) > 0 else {},
            'party_distribution': soma_data['party_id'].value_counts().to_dict() if len(soma_data) > 0 else {},
            'ideology_distribution': soma_data['ideology'].value_counts().to_dict() if len(soma_data) > 0 else {},
        },
        'sample_count': len(soma_data) if len(soma_data) > 0 else 0
    })

    # SF Precinct 3: Richmond District (94114-94118) - Working-class, families
    richmond_data = sf_data[sf_data['party_id'].str.match(r'^94[1-4-5]')]
    precincts.append({
        'id': 'SF-P03-Richmond',
        'name': 'Richmond District',
        'state': 'CA',
        'county': 'San Francisco',
        'zip_codes': ['94114', '94115', '94116', '94117', '94118'],
        'demographics': {
            'age_distribution': richmond_data['age_group'].value_counts().to_dict() if len(richmond_data) > 0 else {},
            'race_distribution': richmond_data['race'].value_counts().to_dict() if len(richmond_data) > 0 else {},
            'party_distribution': richmond_data['party_id'].value_counts().to_dict() if len(richmond_data) > 0 else {},
            'ideology_distribution': richmond_data['ideology'].value_counts().to_dict() if len(richmond_data) > 0 else {},
        },
        'sample_count': len(richmond_data) if len(richmond_data) > 0 else 0
    })

    # SF Precinct 4: Sunset District (94119-94132) - Older, homeowners
    sunset_data = sf_data[sf_data['party_id'].str.match(r'^94[1-9-3]')]
    precincts.append({
        'id': 'SF-P04-Sunset',
        'name': 'Sunset District',
        'state': 'CA',
        'county': 'San Francisco',
        'zip_codes': ['94119', '94120', '94121', '94122', '94123', '94124', '94125', '94126', '94127', '94128', '94129', '94130', '94131', '94132'],
        'demographics': {
            'age_distribution': sunset_data['age_group'].value_counts().to_dict() if len(sunset_data) > 0 else {},
            'race_distribution': sunset_data['race'].value_counts().to_dict() if len(sunset_data) > 0 else {},
            'party_distribution': sunset_data['party_id'].value_counts().to_dict() if len(sunset_data) > 0 else {},
            'ideology_distribution': sunset_data['ideology'].value_counts().to_dict() if len(sunset_data) > 0 else {},
        },
        'sample_count': len(sunset_data) if len(sunset_data) > 0 else 0
    })

    logger.info(f"Created {len(precincts)} SF precincts from survey data")
    return precincts


@task(name="create_miami_precincts")
async def create_miami_precincts(survey_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create Miami-Dade precincts from survey data using ZIP-based clustering."""
    import pandas as pd

    logger = get_run_logger()
    logger.info("Creating Miami-Dade precincts from survey data")

    # Convert to DataFrame
    df = pd.DataFrame(survey_data)

    # Filter to FL
    miami_data = df[df['party_id'].str.contains('Florida', case=False, na=False)]

    # Filter to Miami-Dade ZIP codes (33xxx)
    miami_data = miami_data[miami_data['party_id'].str.contains('33', case=False, na=False)]

    precincts = []

    # Miami Precinct 1: Westchester (33101-33126) - Hispanic majority, working-class
    westchester_data = miami_data[miami_data['party_id'].str.match(r'^33[0-1][0-6]')]
    precincts.append({
        'id': 'MD-P01-Westchester',
        'name': 'Westchester',
        'state': 'FL',
        'county': 'Miami-Dade',
        'zip_codes': ['33101', '33102', '33103', '33124', '33125', '33126'],
        'demographics': {
            'age_distribution': westchester_data['age_group'].value_counts().to_dict() if len(westchester_data) > 0 else {},
            'race_distribution': westchester_data['race'].value_counts().to_dict() if len(westchester_data) > 0 else {},
            'party_distribution': westchester_data['party_id'].value_counts().to_dict() if len(westchester_data) > 0 else {},
            'ideology_distribution': westchester_data['ideology'].value_counts().to_dict() if len(westchester_data) > 0 else {},
        },
        'sample_count': len(westchester_data) if len(westchester_data) > 0 else 0
    })

    # Miami Precinct 2: Coral Gables (33127-33132) - Affluent, mixed demographics
    coral_data = miami_data[miami_data['party_id'].str.match(r'^33[1-3][2-7]')]
    precincts.append({
        'id': 'MD-P02-CoralGables',
        'name': 'Coral Gables',
        'state': 'FL',
        'county': 'Miami-Dade',
        'zip_codes': ['33127', '33128', '33129', '33130', '33131', '33132'],
        'demographics': {
            'age_distribution': coral_data['age_group'].value_counts().to_dict() if len(coral_data) > 0 else {},
            'race_distribution': coral_data['race'].value_counts().to_dict() if len(coral_data) > 0 else {},
            'party_distribution': coral_data['party_id'].value_counts().to_dict() if len(coral_data) > 0 else {},
            'ideology_distribution': coral_data['ideology'].value_counts().to_dict() if len(coral_data) > 0 else {},
        },
        'sample_count': len(coral_data) if len(coral_data) > 0 else 0
    })

    logger.info(f"Created {len(precincts)} Miami-Dade precincts from survey data")
    return precincts


# ============================================================================
# ENHANCED PERSONA GENERATION
# ============================================================================


@task(name="generate_enhanced_personas")
async def generate_enhanced_personas(
    precinct: Dict[str, Any],
    survey_data: List[Dict[str, Any]],
    num_personas: int = 500
) -> List[Persona]:
    """Generate personas enhanced with survey response patterns."""
    import pandas as pd
    import random

    logger = get_run_logger()
    logger.info(f"Generating {num_personas} enhanced personas for precinct {precinct['id']}")

    # Convert to DataFrame for easier sampling
    df = pd.DataFrame(survey_data)

    personas = []

    # Sample from survey data with precinct characteristics in mind
    precinct_zip_codes = set(precinct['zip_codes'])

    # Filter survey data to find matching responses
    matching_responses = df[df['party_id'].str.contains('|'.join(precinct_zip_codes), case=False, na=False)]

    if len(matching_responses) == 0:
        logger.warning(f"No matching survey responses for precinct {precinct['id']}, using general CA/FL data")
        matching_responses = df

    # Generate personas
    for i in range(num_personas):
        # Sample a response as a template
        template = matching_responses.sample(1).iloc[0].to_dict()

        # Create persona with enhanced survey data
        # Map age group to numeric age
        age_map = {
            '18-29': random.randint(20, 29),
            '30-39': random.randint(30, 39),
            '40-49': random.randint(40, 49),
            '50-64': random.randint(50, 64),
            '65+': random.randint(65, 80)
        }
        age = age_map.get(template.get('age_group', '40-49'), 45)

        # Map race
        race_map = {
            'White': Race.WHITE,
            'Black': Race.BLACK,
            'Hispanic': Race.HISPANIC,
            'Asian': Race.ASIAN,
            'Other': Race.OTHER
        }
        race = race_map.get(template.get('race', 'White'), Race.WHITE)

        # Map education
        edu_map = {
            'Less than high school': Education.HIGH_SCHOOL,
            'High school': Education.HIGH_SCHOOL,
            'Some college': Education.SOME_COLLEGE,
            'College degree': Education.COLLEGE,
            'Postgraduate': Education.POSTGRAD
        }
        education = edu_map.get(template.get('education', 'College degree'), Education.COLLEGE)

        # Map party
        party_map = {
            'Democrat': PoliticalParty.DEMOCRAT,
            'Republican': PoliticalParty.REPUBLICAN,
            'Independent': PoliticalParty.INDEPENDENT,
            'Other': PoliticalParty.OTHER
        }
        party = party_map.get(template.get('party_id', 'Democrat'), PoliticalParty.DEMOCRAT)

        # Map ideology
        ideo_map = {
            'Very Liberal': Ideology.VERY_LIBERAL,
            'Liberal': Ideology.LIBERAL,
            'Moderate': Ideology.MODERATE,
            'Conservative': Ideology.CONSERVATIVE,
            'Very Conservative': Ideology.VERY_CONSERVATIVE
        }
        ideology = ideo_map.get(template.get('ideology', 'Moderate'), Ideology.MODERATE

        # Extract top issues
        top_issues = []
        for col in ['issue_positions']:  # This will be populated by extract_favor04_positions
            if col.startswith('issue_') and template.get(col):
                top_issues.append(template[col])

        if not top_issues:
            # Default issues if not available
            if 'ideology' in str(ideology).lower():
                top_issues = ['Housing', 'Economy', 'Education']
            else:
                top_issues = ['Economy', 'Taxes', 'Immigration']

        # Limit to top 3-5 issues
        top_issues = top_issues[:5]

        # Extract policy positions (from FAVOR04_* questions)
        policy_positions = {}
        for col in template.keys():
            if col.startswith('FAVOR04_') and template.get(col):
                issue_name = col.replace('FAVOR04_', '').replace('_', ' ').title()
                policy_positions[issue_name] = template[col]

        # Extract news sources (from SOURCES1_* columns)
        news_sources = []
        for col in template.keys():
            if col.startswith('SOURCES1_') and template.get(col) == 1:
                source_name = col.replace('SOURCES1_', '').replace('_', ' ').title()
                news_sources.append(source_name)

        if not news_sources:
            # Default news sources
            news_sources = ['Local News', 'TV', 'Social Media']
        else:
            news_sources = news_sources[:8]  # Top 8 sources

        # Create persona
        persona = Persona(
            age=age,
            gender=template.get('gender', 'Female'),
            race=race,
            education=education,
            income_bracket=template.get('income', '$60-99K'),
            employment_status=template.get('employment', 'Employed'),
            marital_status=template.get('marital_status', 'Married'),
            precinct_id=precinct['id'],
            county=precinct['county'],
            party_id=party,
            ideology=ideology,
            top_issues=top_issues,
            news_sources=news_sources,
            socrates_prior=True
        )

        personas.append(persona)

    logger.info(f"Generated {len(personas)} personas for precinct {precinct['id']}")
    return personas


# ============================================================================
# MAIN INGESTION FLOW (UPDATED)
# ============================================================================


@flow(name="ingest_all_data")
async def ingest_all_data(
    survey_files: List[str],
    create_precincts: bool = True,
    generate_personas: bool = True
) -> Dict[str, Any]:
    """
    Main ingestion flow: surveys, create precincts, generate personas.
    """
    logger = get_run_logger()

    results = {
        "surveys": {},
        "precincts": {},
        "personas": {}
    }

    # Step 1: Ingest survey data
    for survey_file in survey_files:
        logger.info(f"Ingesting survey: {survey_file}")
        survey_data = await parse_top_survey(survey_file)
        save_result = await save_survey_to_db(survey_data)
        results["surveys"][survey_file] = save_result

    # Step 2: Create precincts from survey data
    if create_precincts:
        logger.info("Creating precincts from survey data...")

        # Create SF precincts
        sf_precincts = await create_sf_precincts(survey_data)
        results["precincts"]["San Francisco"] = {
            "count": len(sf_precincts),
            "precincts": sf_precincts
        }

        # Create Miami-Dade precincts
        miami_precincts = await create_miami_precincts(survey_data)
        results["precincts"]["Miami-Dade"] = {
            "count": len(miami_precincts),
            "precincts": miami_precincts
        }

    # Step 3: Generate personas for each precinct
    if generate_personas and "precincts" in results:
        logger.info("Generating personas for precincts...")

        all_precincts = []
        if "San Francisco" in results["precincts"]:
            all_precincts.extend(results["precincts"]["San Francisco"]["precincts"])
        if "Miami-Dade" in results["precincts"]:
            all_precincts.extend(results["precincts"]["Miami-Dade"]["precincts"])

        for precinct in all_precincts:
            personas = await generate_enhanced_personas(
                precinct=precinct,
                survey_data=survey_data,
                num_personas=500  # 500 personas per precinct
            )
            # Save personas to database
            from src.tasks.database import save_personas_batch
            saved = await save_personas_batch(personas)
            results["personas"][precinct['id']] = {
                "count": len(personas),
                "saved": len(saved)
            }

    logger.info(f"Ingestion complete: {len(results['surveys'])} surveys, {len(all_precincts) if 'precincts' in results else 0} precincts")

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
