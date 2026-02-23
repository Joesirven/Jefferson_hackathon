# Jefferson AI - Synthetic Voter Simulation

Agentic simulation for silicon polling - creating synthetic voter personas for election modeling and opinion polling.

## 🎯 Features

- **Synthetic Personas**: Generate realistic voter profiles based on demographic data and survey responses
- **Multi-LLM Support**: Powered by ZhipuAI, Google Gemini, and Anthropic (Claude)
- **Interactive Polling**: Ask open-ended, multiple choice, or scale questions to synthetic voters
- **News Context Integration**: Scrape and incorporate local news for context-aware responses
- **Batch Simulations**: Run large-scale simulations across multiple precincts
- **Fast & Scalable**: Built with Prefect for workflow orchestration and Supabase for data storage

## 🛠️ Technology Stack

- **Python 3.12+**: Core language
- **FastAPI & Uvicorn**: API server
- **Prefect**: Workflow orchestration
- **Supabase**: Database and backend services
- **Click**: CLI interface
- **Pydantic**: Data validation
- **ZhipuAI / Google / Anthropic**: LLM providers
- **BeautifulSoup4**: Web scraping
- **Pandas**: Data manipulation

## 📦 Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Supabase account (free tier works)
- At least one LLM API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Jefferson_hackathon
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## 🔑 Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# LLM API Keys (at least one required)
ZHIPUAI_API_KEY=your_zhipuai_api_key
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: Disable telemetry
PREFECT_SERVER_ANALYTICS_ENABLED=false
DO_NOT_TRACK=1
```

### Getting API Keys

- **Supabase**: Create a project at [supabase.com](https://supabase.com) → Project Settings → API
- **ZhipuAI**: Sign up at [open.bigmodel.cn](https://open.bigmodel.cn)
- **Google**: Create a project at [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials
- **Anthropic**: Get keys at [console.anthropic.com](https://console.anthropic.com)

## 🚀 Usage

### CLI Interface

The project includes a comprehensive CLI for data ingestion, polling, and simulation.

#### Count Personas

```bash
# Count all personas in database
uv run jefferson count

# Count personas in a specific precinct
uv run jefferson count --precinct precinct_id
```

#### Data Ingestion

```bash
# Ingest survey data
uv run jefferson ingest survey_data.csv --precincts precinct1 precinct2

# Scrape local news
uv run jefferson scrape-news "San Francisco" --hours 48
```

#### Polling

```bash
# Poll a precinct on a question
uv run jefferson poll precinct_id "What do you think about housing policy?"

# Multiple choice question
uv run jefferson poll precinct_id "Should we build more affordable housing?" \
  --type choice \
  --options "Yes" "No" "Unsure"

# Scale question
uv run jefferson poll precinct_id "Rate the mayor's performance (1-10)" \
  --type scale

# Interactive mode
uv run jefferson interactive-poll precinct_id
```

#### Simulation

```bash
# Run a full simulation
uv run jefferson simulate precinct1 precinct2 \
  --questions "How will you vote on Prop A?" "What's your top priority?" \
  --iterations 3 \
  --concurrent 50

# List recent simulations
uv run jefferson list-sims --limit 10
```

#### View Personas

```bash
# Show personas in a precinct
uv run jefferson show-personas precinct_id --limit 20
```

## 📁 Project Structure

```
Jefferson_hackathon/
├── src/
│   ├── __init__.py
│   ├── cli.py                 # Click CLI interface
│   ├── api/                   # FastAPI endpoints
│   │   ├── __init__.py
│   │   └── main.py
│   ├── flows/                 # Prefect workflows
│   │   ├── __init__.py
│   │   ├── ingestion.py       # Data ingestion pipelines
│   │   └── simulation.py      # Simulation workflows
│   ├── models/                # Pydantic models
│   │   ├── __init__.py
│   │   └── persona.py         # Persona data model
│   └── tasks/                 # Utility functions
│       ├── __init__.py
│       ├── database.py        # Supabase queries
│       ├── llm.py            # LLM client management
│       └── news.py           # News scraping
├── .env                       # Environment variables (not committed)
├── .python-version            # Python version pin
├── pyproject.toml            # Project configuration
├── uv.lock                   # Dependency lock file
├── CLAUDE.md                 # Claude Code instructions
├── LICENSE
├── README.md                 # This file
└── specs.md                  # Project specifications
```

## 🗄️ Database Setup

### Required Tables

Set up these tables in your Supabase project:

#### `personas`
Stores synthetic voter profiles.

```sql
create table personas (
  id text primary key,
  age integer,
  gender text,
  race text,
  education text,
  income_bracket text,
  employment_status text,
  marital_status text,
  precinct_id text,
  county text,
  party_id text,
  ideology text,
  top_issues text[],
  news_sources text[],
  socrates_prior boolean default false,
  created_at timestamp with time zone default now()
);
```

#### `survey_responses`
Stores raw survey data for persona building.

```sql
create table survey_responses (
  id text primary key,
  precinct_id text,
  county text,
  age integer,
  gender text,
  race text,
  education text,
  income text,
  responses jsonb,
  created_at timestamp with time zone default now()
);
```

#### `simulations`
Stores simulation results.

```sql
create table simulations (
  simulation_id text primary key,
  precinct_ids text[],
  questions jsonb,
  results jsonb,
  status text,
  created_at timestamp with time zone default now()
);
```

#### `news_articles`
Stores scraped news articles.

```sql
create table news_articles (
  id text primary key,
  title text,
  url text,
  summary text,
  content text,
  county text,
  published_at timestamp with time zone,
  scraped_at timestamp with time zone default now()
);
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

### Code Quality

```bash
# Lint code
uv run ruff check src/

# Format code
uv run ruff format src/

# Type checking
uv run mypy src/
```

### Database Migrations

Use Alembic for database migrations (if you add schema changes).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for all public functions
- Keep functions focused and modular
- Write tests for new features

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Jefferson Hackathon
- Powered by ZhipuAI, Google Gemini, and Anthropic
- Built with Supabase and Prefect
- Inspired by the need for better, faster, cheaper polling

## 📧 Contact

For questions or feedback, please open an issue in the repository.

---

**Note**: This is a hackathon project. While functional, it may require further development and hardening for production use.