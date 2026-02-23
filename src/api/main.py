# src/api/main.py
"""FastAPI backend for Jefferson AI."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

from src.models.persona import PollQuestion
from src.flows.simulation import run_simulation, poll_precinct
from src.flows.ingestion import ingest_all_data


app = FastAPI(
    title="Jefferson AI",
    description="Synthetic voter simulation for election modeling",
    version="0.1.0"
)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class SimulationRequest(BaseModel):
    """Request to start a simulation."""
    precinct_ids: List[str]
    questions: List[Dict[str, Any]]  # PollQuestion as dict
    num_iterations: int = 1
    max_concurrent: int = 50


class SimulationResponse(BaseModel):
    """Response after starting a simulation."""
    simulation_id: str
    status: str
    message: str


class PollRequest(BaseModel):
    """Request to poll a precinct."""
    precinct_id: str
    question: Dict[str, Any]
    max_concurrent: int = 50


class IngestionRequest(BaseModel):
    """Request to ingest data."""
    survey_files: List[str]
    precinct_ids: List[str]
    use_socrates: bool = True


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Jefferson AI"}


# ============================================================================
# Simulation Endpoints
# ============================================================================

@app.post("/v1/simulation/start", response_model=SimulationResponse)
async def start_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new simulation.

    The simulation runs in the background. Use GET /v1/simulation/{id} to check status.
    """
    simulation_id = str(uuid.uuid4())

    # Convert question dicts to PollQuestion objects
    questions = [PollQuestion(**q) for q in request.questions]

    # Start simulation in background
    background_tasks.add_task(
        run_simulation.serve,
        simulation_id,
        request.precinct_ids,
        questions,
        request.num_iterations,
        request.max_concurrent
    )

    return SimulationResponse(
        simulation_id=simulation_id,
        status="started",
        message=f"Simulation started for {len(request.precinct_ids)} precincts"
    )


@app.get("/v1/simulation/{simulation_id}")
async def get_simulation(simulation_id: str):
    """Get simulation results by ID."""
    from src.tasks.database import get_simulation_results

    results = await get_simulation_results(simulation_id)

    if not results:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return results


@app.get("/v1/simulations")
async def list_simulations(limit: int = 50):
    """List recent simulations."""
    from src.tasks.database import list_simulations

    simulations = await list_simulations(limit)
    return {"simulations": simulations}


# ============================================================================
# Polling Endpoints
# ============================================================================

@app.post("/v1/poll/precinct")
async def poll_precinct_endpoint(request: PollRequest):
    """
    Poll all agents in a precinct on a single question.

    Returns aggregated results.
    """
    from src.tasks.database import get_personas_by_precinct
    from src.tasks.llm import get_llm_client
    from src.tasks.news import get_combined_news_context

    # Get personas
    personas = await get_personas_by_precinct(request.precinct_id)

    if not personas:
        raise HTTPException(status_code=404, detail="No personas found for precinct")

    # Get news context
    # Would determine county from precinct
    news_context = await get_combined_news_context(["San Francisco"])

    # Convert question
    question = PollQuestion(**request.question)

    # Run poll
    llm_client = get_llm_client()
    responses = await poll_precinct.serve(
        personas=personas,
        question=question,
        news_context=news_context,
        llm_client=llm_client,
        max_concurrent=request.max_concurrent
    )

    return {
        "precinct_id": request.precinct_id,
        "question_id": question.id,
        "total_responded": len(responses),
        "results": aggregate_poll_results(responses, question)
    }


def aggregate_poll_results(responses: List, question: PollQuestion) -> Dict:
    """Aggregate poll results for API response."""
    if question.question_type == "choice":
        counts = {}
        for r in responses:
            choice = r.response.upper()
            counts[choice] = counts.get(choice, 0) + 1
        return {"type": "distribution", "counts": counts}
    elif question.question_type == "scale":
        values = []
        for r in responses:
            try:
                values.append(float(r.response))
            except:
                pass
        if values:
            return {
                "type": "stats",
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values)
            }
    return {"type": "raw", "responses": [r.response for r in responses]}


# ============================================================================
# Data Ingestion Endpoints
# ============================================================================

@app.post("/v1/ingest/surveys")
async def ingest_surveys(request: IngestionRequest, background_tasks: BackgroundTasks):
    """Ingest survey data and generate personas."""
    ingestion_id = str(uuid.uuid4())

    background_tasks.add_task(
        ingest_all_data.serve,
        request.survey_files,
        request.precinct_ids,
        request.use_socrates
    )

    return {
        "ingestion_id": ingestion_id,
        "status": "started",
        "message": f"Ingesting {len(request.survey_files)} survey files"
    }


# ============================================================================
# Persona Endpoints
# ============================================================================

@app.get("/v1/personas/count")
async def get_persona_count(precinct_id: Optional[str] = None):
    """Get count of personas, optionally filtered by precinct."""
    from src.tasks.database import get_persona_count

    count = await get_persona_count(precinct_id)
    return {"count": count}


@app.get("/v1/personas/{precinct_id}")
async def get_personas(precinct_id: str, limit: int = 100):
    """Get personas for a precinct."""
    from src.tasks.database import get_personas_by_precinct

    personas = await get_personas_by_precinct(precinct_id)
    return {
        "precinct_id": precinct_id,
        "count": len(personas),
        "personas": [p.dict() for p in personas[:limit]]
    }


# ============================================================================
# CLI Alternative
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
