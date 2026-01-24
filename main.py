from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from requests import RequestException

from scraper import (
    MAIN_PAGE_URL,
    get_exam_sessions,
    get_sessions_by_year,
    scrape_papers_from_url,
    group_papers_by_subject,
)
from models import (
    RootResponse,
    SessionsResponse,
    SessionsByYearResponse,
    PapersResponse,
    SubjectsListResponse,
    AvailableValuesResponse,
    SessionType,
)

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
    """,
    version="2.0.0",
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
        }
    )


@app.get("/values", response_model=AvailableValuesResponse)
def get_available_values():
    """
    Get all acceptable parameter values for the API.

    Use this endpoint to discover:
    - Valid session types (November, MayJune, etc.)
    - Available years
    - Sample list of subjects
    - Paper languages and numbers
    """
    try:
        sessions = get_exam_sessions()
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    # Extract unique years (sorted descending)
    years = sorted(set(s["year"] for s in sessions if s["year"]), reverse=True)

    # Get subjects from the most recent session
    sample_subjects: list[str] = []
    if sessions:
        # Find a session with papers to get subject list
        for session in sessions:
            if session.get("working_url"):
                try:
                    papers = scrape_papers_from_url(session["working_url"])
                    grouped = group_papers_by_subject(papers)
                    sample_subjects = sorted(grouped.keys())
                    break
                except Exception:
                    continue

    return AvailableValuesResponse(
        sessions=[s.value for s in SessionType],
        years=years,
        sample_subjects=sample_subjects,
        languages=["English", "Afrikaans"],
        paper_numbers=["P1", "P2", "P3"],
    )


@app.get("/sessions", response_model=SessionsResponse)
def get_sessions():
    """
    Get all available exam sessions.

    Returns a list of all exam sessions available in the database,
    including year, session type, and the URL to fetch papers from.
    """
    try:
        sessions = get_exam_sessions()
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    return SessionsResponse(
        source_url=MAIN_PAGE_URL,
        total=len(sessions),
        sessions=sessions,
    )


@app.get("/sessions/{year}", response_model=SessionsByYearResponse)
def get_sessions_for_year(year: str):
    """
    Get exam sessions filtered by year.

    **Path Parameters:**
    - **year**: The exam year (e.g., "2024", "2025")
    """
    try:
        sessions = get_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    if not sessions:
        raise HTTPException(status_code=404, detail=f"No sessions found for year {year}")

    return SessionsByYearResponse(
        year=year,
        total=len(sessions),
        sessions=sessions,
    )


@app.get("/papers/{year}/{session}", response_model=PapersResponse)
def get_papers(
    year: str,
    session: str,
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
    try:
        sessions = get_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    target_session = None
    for s in sessions:
        if s["session"] and s["session"].lower() == session.lower():
            target_session = s
            break

    if not target_session:
        available = [s["session"] for s in sessions if s["session"]]
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session}' not found for year {year}. Available: {available}",
        )

    try:
        papers = scrape_papers_from_url(target_session["working_url"])
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch papers: {str(e)}")

    grouped = group_papers_by_subject(papers)

    if subject:
        subject_lower = subject.lower()
        grouped = {k: v for k, v in grouped.items() if k and subject_lower in k.lower()}

    return PapersResponse(
        year=year,
        session=session,
        source_url=target_session["working_url"],
        total_subjects=len(grouped),
        subjects=grouped,
    )


@app.get("/subjects/{year}/{session}", response_model=SubjectsListResponse)
def list_subjects(year: str, session: str):
    """
    List all available subjects for an exam session.

    **Path Parameters:**
    - **year**: Exam year (e.g., "2024", "2025")
    - **session**: Session type - one of: November, MayJune, FebMarch, Supplementary

    Returns an alphabetically sorted list of all subject names available for the specified session.
    """
    try:
        sessions = get_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    target_session = None
    for s in sessions:
        if s["session"] and s["session"].lower() == session.lower():
            target_session = s
            break

    if not target_session:
        raise HTTPException(status_code=404, detail=f"Session '{session}' not found for year {year}")

    try:
        papers = scrape_papers_from_url(target_session["working_url"])
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch papers: {str(e)}")

    grouped = group_papers_by_subject(papers)
    subjects = sorted(grouped.keys())

    return SubjectsListResponse(
        year=year,
        session=session,
        total=len(subjects),
        subjects=subjects,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
