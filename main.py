from fastapi import FastAPI, HTTPException, Query
from requests import RequestException

from scraper import (
    # DBE Main Site
    MAIN_PAGE_URL,
    get_exam_sessions,
    get_sessions_by_year,
    scrape_papers_from_url,
    group_papers_by_subject,
    # Eastern Cape Site (all subjects)
    EC_INDEX_URL,
    get_ec_exam_sessions,
    get_ec_sessions_by_year,
    scrape_ec_papers_from_url,
    group_ec_papers_by_subject,
)

app = FastAPI(
    title="NSC Past Papers API",
    description="API to access South African NSC past examination papers and memos",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "NSC Past Papers API",
        "sources": {
            "dbe": "Department of Basic Education (Languages & Technical)",
            "ec": "Eastern Cape (All subjects including Math, Science, etc.)",
        },
        "endpoints": {
            "/dbe/sessions": "DBE exam sessions",
            "/dbe/papers/{year}/{session}": "DBE papers (languages)",
            "/ec/sessions": "Eastern Cape exam sessions",
            "/ec/sessions/{year}": "EC sessions for a specific year",
            "/ec/papers/{year}/{session}": "EC papers (all subjects)",
            "/ec/subjects/{year}/{session}": "List subjects for EC session",
        },
    }


# =============================================================================
# DBE Main Site Endpoints (Languages and Technical subjects)
# =============================================================================

@app.get("/dbe/sessions")
def get_dbe_sessions():
    """Get all exam sessions from DBE main site."""
    try:
        sessions = get_exam_sessions()
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    return {
        "source": "dbe",
        "source_url": MAIN_PAGE_URL,
        "total": len(sessions),
        "sessions": sessions,
    }


@app.get("/dbe/sessions/{year}")
def get_dbe_sessions_for_year(year: str):
    """Get DBE exam sessions filtered by year."""
    try:
        sessions = get_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    if not sessions:
        raise HTTPException(status_code=404, detail=f"No sessions found for year {year}")

    return {
        "source": "dbe",
        "year": year,
        "total": len(sessions),
        "sessions": sessions,
    }


@app.get("/dbe/papers/{year}/{session}")
def get_dbe_papers(
    year: str,
    session: str,
    subject: str = Query(None, description="Filter by subject name"),
):
    """
    Get papers from DBE site (mainly languages and technical subjects).

    - **year**: e.g., "2024"
    - **session**: e.g., "MayJune" or "November"
    - **subject**: Optional filter by subject name
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
        grouped = {k: v for k, v in grouped.items() if subject_lower in k.lower()}

    return {
        "source": "dbe",
        "year": year,
        "session": session,
        "source_url": target_session["working_url"],
        "total_subjects": len(grouped),
        "subjects": grouped,
    }


# =============================================================================
# Eastern Cape Site Endpoints (All subjects including Math, Science, etc.)
# =============================================================================

@app.get("/ec/sessions")
def get_ec_sessions():
    """Get all exam sessions from Eastern Cape site (has all subjects)."""
    try:
        sessions = get_ec_exam_sessions()
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    return {
        "source": "ecexams",
        "source_url": EC_INDEX_URL,
        "total": len(sessions),
        "sessions": sessions,
    }


@app.get("/ec/sessions/{year}")
def get_ec_sessions_for_year(year: str):
    """Get Eastern Cape exam sessions filtered by year."""
    try:
        sessions = get_ec_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    if not sessions:
        raise HTTPException(status_code=404, detail=f"No sessions found for year {year}")

    return {
        "source": "ecexams",
        "year": year,
        "total": len(sessions),
        "sessions": sessions,
    }


@app.get("/ec/papers/{year}/{session}")
def get_ec_papers(
    year: str,
    session: str,
    subject: str = Query(None, description="Filter by subject name (e.g., 'math', 'physics')"),
):
    """
    Get papers from Eastern Cape site (ALL subjects including Math, Science, etc.).

    - **year**: e.g., "2024"
    - **session**: e.g., "November", "MayJune", "September"
    - **subject**: Optional filter by subject name (case-insensitive partial match)

    Returns papers grouped by subject with download links (zip files).
    """
    try:
        sessions = get_ec_sessions_by_year(year)
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch data: {str(e)}")

    target_session = None
    for s in sessions:
        if s["session"] and s["session"].lower() == session.lower():
            target_session = s
            break

    if not target_session:
        available = list(set(s["session"] for s in sessions if s["session"]))
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session}' not found for year {year}. Available: {available}",
        )

    try:
        papers = scrape_ec_papers_from_url(target_session["working_url"])
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch papers: {str(e)}")

    grouped = group_ec_papers_by_subject(papers)

    if subject:
        subject_lower = subject.lower()
        grouped = {k: v for k, v in grouped.items() if subject_lower in k.lower()}

    return {
        "source": "ecexams",
        "year": year,
        "session": session,
        "source_url": target_session["working_url"],
        "total_subjects": len(grouped),
        "subjects": grouped,
    }


@app.get("/ec/subjects/{year}/{session}")
def list_ec_subjects(year: str, session: str):
    """List all available subjects for an Eastern Cape exam session."""
    try:
        sessions = get_ec_sessions_by_year(year)
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
        papers = scrape_ec_papers_from_url(target_session["working_url"])
    except RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch papers: {str(e)}")

    grouped = group_ec_papers_by_subject(papers)
    subjects = sorted(grouped.keys())

    return {
        "source": "ecexams",
        "year": year,
        "session": session,
        "total": len(subjects),
        "subjects": subjects,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
