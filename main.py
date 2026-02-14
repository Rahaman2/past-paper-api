import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from scraper import MAIN_PAGE_URL
from cache import (
    load_cache_from_disk,
    get_all_sessions,
    get_sessions_for_year,
    get_papers_for_session,
    get_cache,
    get_cache_age_seconds,
    search_papers,
)
from scheduler import run_full_scrape, start_scheduler, stop_scheduler
from models import (
    RootResponse,
    SessionsResponse,
    SessionsByYearResponse,
    PapersResponse,
    SubjectsListResponse,
    AvailableValuesResponse,
    SearchResponse,
    SessionType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load cache or scrape. Shutdown: stop scheduler."""
    loaded = load_cache_from_disk()
    if not loaded:
        logger.info("No cache file found. Running initial scrape...")
        run_full_scrape()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="NSC Past Papers API",
    description="""
API to access South African NSC (National Senior Certificate) past examination papers and memos.

## Features
- Get download links for question papers and memorandums
- Filter by year, session, and subject
- Supports 60+ subjects including all languages and STEM subjects

## Data Source
Papers are scraped from the Department of Basic Education website (education.gov.za).
Data is cached and refreshed daily.
    """,
    version="2.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",  # Alternative localhost
        "https://matricmate.co.za",
        "https://www.matricmate.co.za",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=RootResponse)
def root():
    """
    API root - shows available endpoints.
    """
    return RootResponse(
        endpoints={
            "/sessions": "All available exam sessions",
            "/sessions/{year}": "Sessions for a specific year",
            "/papers/{year}/{session}": "Papers for a year/session (all subjects)",
            "/papers/{year}/{session}?subject=math": "Filter papers by subject name",
            "/subjects/{year}/{session}": "List all subjects for a session",
            "/values": "Show all acceptable parameter values",
            "/search?q=math": "Search papers across all years and sessions",
            "/health": "API health and cache status",
        }
    )


@app.get("/health")
def health():
    """API health check with cache status."""
    cache = get_cache()
    return {
        "status": "ok" if cache else "no_cache",
        "cache_age_seconds": int(get_cache_age_seconds() or 0),
        "last_updated": cache.get("last_updated") if cache else None,
        "total_sessions": len(cache.get("sessions", [])) if cache else 0,
        "scrape_errors": cache.get("scrape_errors", []) if cache else [],
    }


@app.get("/values", response_model=AvailableValuesResponse)
def get_available_values(response: Response):
    """
    Get all acceptable parameter values for the API.

    Use this endpoint to discover:
    - Valid session types (November, MayJune, etc.)
    - Available years
    - Sample list of subjects
    - Paper languages and numbers
    """
    sessions = get_all_sessions()
    if not sessions:
        raise HTTPException(status_code=503, detail="Cache not available. Try again shortly.")

    response.headers["Cache-Control"] = "public, max-age=3600"

    years = sorted(set(s["year"] for s in sessions if s["year"]), reverse=True)

    # Get sample subjects from the most recent session in cache
    sample_subjects: list[str] = []
    for session in sessions:
        year = session.get("year")
        session_name = session.get("session")
        if year and session_name:
            papers = get_papers_for_session(year, session_name)
            if papers:
                sample_subjects = sorted(papers.keys())
                break

    return AvailableValuesResponse(
        sessions=[s.value for s in SessionType],
        years=years,
        sample_subjects=sample_subjects,
        languages=["English", "Afrikaans"],
        paper_numbers=["P1", "P2", "P3"],
    )


@app.get("/sessions", response_model=SessionsResponse)
def get_sessions(response: Response):
    """
    Get all available exam sessions.

    Returns a list of all exam sessions available in the database,
    including year, session type, and the URL to fetch papers from.
    """
    sessions = get_all_sessions()
    if not sessions:
        raise HTTPException(status_code=503, detail="Cache not available. Try again shortly.")

    response.headers["Cache-Control"] = "public, max-age=3600"

    return SessionsResponse(
        source_url=MAIN_PAGE_URL,
        total=len(sessions),
        sessions=sessions,
    )


@app.get("/sessions/{year}", response_model=SessionsByYearResponse)
def get_sessions_by_year_endpoint(year: str, response: Response):
    """
    Get exam sessions filtered by year.

    **Path Parameters:**
    - **year**: The exam year (e.g., "2024", "2025")
    """
    sessions = get_sessions_for_year(year)

    if not sessions:
        raise HTTPException(status_code=404, detail=f"No sessions found for year {year}")

    response.headers["Cache-Control"] = "public, max-age=3600"

    return SessionsByYearResponse(
        year=year,
        total=len(sessions),
        sessions=sessions,
    )


@app.get("/papers/{year}/{session}", response_model=PapersResponse)
def get_papers(
    year: str,
    session: str,
    response: Response,
    subject: str | None = Query(
        None,
        description=(
            "Filter by subject name (case-insensitive partial match). "
            "Examples: 'english fal', 'english hl', 'afrikaans', 'isizulu hl', 'math', 'physics'"
        ),
        examples=["english fal", "english hl", "afrikaans", "isizulu hl", "math", "physics", "fal", "hl"],
    ),
):
    """
    Get papers for a specific year and session.

    **Path Parameters:**
    - **year**: Exam year (e.g., "2024", "2025")
    - **session**: Session type - one of: November, MayJune, FebMarch, Supplementary

    **Query Parameters:**
    - **subject**: Optional filter by subject name (case-insensitive partial match)

    **Subject Filter Examples:**
    | Query | Matches |
    |-------|---------|
    | `?subject=english fal` | English FAL |
    | `?subject=english hl` | English HL |
    | `?subject=english` | English FAL, English HL |
    | `?subject=afrikaans` | Afrikaans FAL, Afrikaans HL, Afrikaans SAL |
    | `?subject=isizulu hl` | IsiZulu HL |
    | `?subject=math` | Mathematics, Mathematical Literacy, Technical Mathematics |
    | `?subject=fal` | All FAL (First Additional Language) subjects |
    | `?subject=hl` | All HL (Home Language) subjects |

    **Response Structure:**
    Papers are grouped by: `subject -> paper_number (P1/P2/P3) -> language -> download_url`
    """
    year_sessions = get_sessions_for_year(year)

    target_session = None
    for s in year_sessions:
        if s["session"] and s["session"].lower() == session.lower():
            target_session = s
            break

    if not target_session:
        available = [s["session"] for s in year_sessions if s["session"]]
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session}' not found for year {year}. Available: {available}",
        )

    grouped = get_papers_for_session(year, session)
    if grouped is None:
        raise HTTPException(status_code=503, detail="Paper data not cached for this session")

    if subject:
        subject_lower = subject.lower()
        grouped = {k: v for k, v in grouped.items() if k and subject_lower in k.lower()}

    response.headers["Cache-Control"] = "public, max-age=3600"

    return PapersResponse(
        year=year,
        session=session,
        source_url=target_session["working_url"],
        total_subjects=len(grouped),
        subjects=grouped,
    )


@app.get("/search", response_model=SearchResponse)
def search(
    response: Response,
    q: str = Query(
        ...,
        min_length=2,
        description="Search query for subject name (case-insensitive partial match)",
        examples=["math", "english", "physics", "accounting"],
    ),
):
    """
    Search for papers across all years and sessions.

    **Query Parameters:**
    - **q**: Subject search query (min 2 characters, case-insensitive partial match)

    Returns matching subjects grouped by year/session, sorted by year descending.
    """
    results = search_papers(q)
    total = sum(r["total_subjects"] for r in results)

    response.headers["Cache-Control"] = "public, max-age=3600"

    return SearchResponse(
        query=q,
        total_results=total,
        results=results,
    )


@app.get("/subjects/{year}/{session}", response_model=SubjectsListResponse)
def list_subjects(year: str, session: str, response: Response):
    """
    List all available subjects for an exam session.

    **Path Parameters:**
    - **year**: Exam year (e.g., "2024", "2025")
    - **session**: Session type - one of: November, MayJune, FebMarch, Supplementary

    Returns an alphabetically sorted list of all subject names available for the specified session.
    """
    year_sessions = get_sessions_for_year(year)

    target_session = None
    for s in year_sessions:
        if s["session"] and s["session"].lower() == session.lower():
            target_session = s
            break

    if not target_session:
        raise HTTPException(status_code=404, detail=f"Session '{session}' not found for year {year}")

    grouped = get_papers_for_session(year, session)
    if grouped is None:
        raise HTTPException(status_code=503, detail="Paper data not cached for this session")

    subjects = sorted(grouped.keys())

    response.headers["Cache-Control"] = "public, max-age=3600"

    return SubjectsListResponse(
        year=year,
        session=session,
        total=len(subjects),
        subjects=subjects,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
