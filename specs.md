# Jefferson AI Specs Doc

## What it does
Generates synthetic (silicon) representations of voters using ACS (census) data, polling results, and publicly available data sources to model election results and voter response.

## Research Foundation
Based on these papers:
- **Stanford HAI**: https://hai.stanford.edu/assets/files/hai-policy-brief-simulating-human-behavior-with-ai-agents.pdf
  - Key insight: Interview-based personas achieve 85% accuracy vs 70% for demographic-only
  - For v1: Use rich demographic + issue position data as proxy for "interview" data
- **SOCRATES**: https://arxiv.org/pdf/2509.05830
  - Key insight: Fine-tuning on social science experiments improves prediction by 26%
  - For v2: Fine-tune open-source model (Qwen2.5-14B or LLaMA 3.1-8B)

---

## v1 (Current Scope)

### Simulation Scale
- **4 precincts** to start (2 SF, 2 Miami-Dade)
- **1:1 voter representation** in those precincts (~500-2000 agents per precinct typically)
- Total ~2,000-8,000 synthetic agents for initial simulation

### Data Sources

#### 1. ACS (Census) Data - Recommended Tables
| Table | Description | Why Needed |
|-------|-------------|------------|
| **DP05** | ACS Demographic and Housing Estimates | Age, sex, race, population counts |
| **DP03** | Selected Economic Characteristics | Income, employment, occupation, health insurance |
| **DP02** | Selected Social Characteristics | Education, marital status, grandparents, veterans |
| **S0601** | Selected Population Profile in Defined Poverty Area | Poverty status by demographics |
| **S1901** | Income in the Past 12 Months | Detailed income distributions |
| **S1501** | Educational Attainment | Detailed education levels |

**Geography:** Census block groups → map to precincts using shapefile overlap

#### 2. Survey Data (data/surveys/)
**TOP (Tracking of Polls) surveys:**
- Fields available: age, gender, race, education, income, employment, marital status, religion, party ID, ideology, vote history
- FAVOR04_* questions: Policy positions on 20+ issues
- issues_top5_* : Ranked issue importance
- SOURCES1_* : 26 news sources respondents use
- Use to build "persona templates" that can be matched to ACS demographics

#### 3. Precinct Level Data
- Precinct shapefiles for SF and Miami-Dade
- Historical election results at precinct level
- Voter registration data (if available)

#### 4. News & Social Media
- **Context Embedder approach (v1):**
  - Scrape recent (last 24-48 hours) localized news for each county
  - Sources: local news sites, Reddit subreddits, trending local topics
  - Create "news context" vector for each simulation run
  - Inject as context when polling agents

### LLM Strategy (v1)
- **Primary:** GLM-4 or Gemini Flash (cost-effective for high volume)
- **Prompting strategy:** Persona-based prompts (similar to Stanford paper's demographic baseline)
- **Template:**
  ```
  You are a [age]-year-old [race] [gender] from [neighborhood], [precinct].
  Education: [level], Income: [range], Party: [affiliation], Ideology: [position]
  You primarily get news from [sources].
  Top issues you care about: [issue1], [issue2], [issue3]

  Recent local news context:
  [news_summary]

  Question: [poll_question]
  Your response (as this voter would respond):
  ```

### Simulation Features
- **Polling:** Query agents on ballot measures, candidate preferences
- **Interaction:** Agents influence nearby agents with shared demographics (small opinion shift)
- **News Consumption:** Agents update opinions based on news context embedding
- **Analysis:** Aggregate responses, compare to historical precinct results

---

## v2 (Future)

### Model Improvements
- **Fine-tune open-source model** (Qwen2.5-14B or LLaMA 3.1-8B) on:
  - Survey response data + demographics
  - Historical precinct results
  - Time-series calibration data
- **Cost estimate:** $10-30 per fine-tune run on cloud GPU, or host on VPS with GPU

### Dashboard
- React & TypeScript frontend
- Map visualization of precincts with agent distributions
- Real-time polling results
- Opinion shift charts over simulation iterations
- Network graph of agent interactions

### Advanced Features
- Multi-county expansion beyond SF and Miami-Dade
- Historical simulation (past elections with validation)
- What-if scenarios (policy changes, news events)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Prefect Orchestrator                       │
│                    (pipeline scheduling & monitoring)            │
└─────────────────────────────────────────────────────────────────┘
         │                │                │                │
         ▼                ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  ACS Data    │  │  Survey      │  │  News        │  │  Precinct    │
│  Ingestion   │  │  Parsing     │  │  Scraper     │  │  Mapping     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
         │                │                │                │
         ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                │
│           (demographics, personas, news, simulation logs)        │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│   /create-simulation  /poll-agents  /run-interaction  /results  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LLM Service (GLM-4 / Gemini)                     │
│                    (persona-based prompting)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Backend:** FastAPI (Python) with UV
- **Orchestration:** Prefect (pipeline workflows + built-in UI)
- **Database:** Supabase (hosted PostgreSQL + auth)
- **Containerization:** Docker Compose (v2)
- **Frontend:** CLI (v1), React + TypeScript (v2)
- **Web Server (v2):** Nginx
- **LLM:** GLM-4 Flash or Gemini Flash (v1), self-hosted fine-tuned model (v2)

### Concurrency (v1)
- **No Docker per agent/simulation** - too heavy
- Prefect built-in concurrency with async workers
- Batch processing (50 concurrent LLM calls)
- Agents are data in Supabase, not processes

### UI
- **v1:** CLI (Click-based) - `jefferson poll`, `jefferson simulate`, etc.
- **v2:** React dashboard with map visualization

---

## Goal
Simulate the upcoming primary elections in San Francisco and Miami-Dade county areas with sufficient accuracy to:
1. Predict precinct-level vote shares
2. Identify swing voter demographics
3. Test messaging effectiveness
4. Understand news/social media impact on voter opinion
