import json
import os
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = DATA_DIR / "papers_cache.json"

# In-memory cache - loaded once, refreshed by background scraper
_cache: dict | None = None
_cache_lock = Lock()


def get_cache() -> dict | None:
    """Return the current in-memory cache. None if not loaded."""
    return _cache


def load_cache_from_disk() -> bool:
    """Load cache from JSON file into memory. Returns True if successful."""
    global _cache
    if not CACHE_FILE.exists():
        return False
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with _cache_lock:
            _cache = data
        logger.info("Cache loaded from disk. Last updated: %s", data.get("last_updated"))
        return True
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load cache from disk: %s", e)
        return False


def save_cache_to_disk(data: dict) -> None:
    """Atomically write cache data to disk and update in-memory cache."""
    global _cache
    DATA_DIR.mkdir(exist_ok=True)

    # Write to temp file first, then rename (atomic on POSIX)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, CACHE_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    with _cache_lock:
        _cache = data
    logger.info("Cache saved to disk. Sessions: %d", len(data.get("sessions", [])))


def get_all_sessions() -> list[dict]:
    """Return all sessions from cache."""
    c = get_cache()
    return c["sessions"] if c else []


def get_sessions_for_year(year: str) -> list[dict]:
    """Return sessions filtered by year."""
    return [s for s in get_all_sessions() if s["year"] == year]


def get_papers_for_session(year: str, session: str) -> dict | None:
    """Return grouped papers for a year/session. None if not found."""
    c = get_cache()
    if not c:
        return None
    for k, v in c.get("papers", {}).items():
        parts = k.split("|", 1)
        if len(parts) == 2 and parts[0] == year and parts[1].lower() == session.lower():
            return v
    return None


def search_papers(query: str) -> list[dict]:
    """Search for subjects matching query across all years/sessions.
    Returns list of dicts with year, session, source_url, total_subjects, subjects."""
    c = get_cache()
    if not c:
        return []

    query_lower = query.lower()
    results = []

    # Build a lookup for session working_urls
    session_urls = {}
    for s in c.get("sessions", []):
        if s.get("year") and s.get("session"):
            session_urls[f"{s['year']}|{s['session']}"] = s.get("working_url", "")

    for key, subjects in c.get("papers", {}).items():
        parts = key.split("|", 1)
        if len(parts) != 2:
            continue
        year, session = parts

        matched = {k: v for k, v in subjects.items() if k and query_lower in k.lower()}
        if matched:
            results.append({
                "year": year,
                "session": session,
                "source_url": session_urls.get(key, ""),
                "total_subjects": len(matched),
                "subjects": matched,
            })

    # Sort by year descending, then session name
    results.sort(key=lambda r: (-int(r["year"]) if r["year"].isdigit() else 0, r["session"]))
    return results


def get_cache_age_seconds() -> float | None:
    """Return seconds since last cache update, or None."""
    c = get_cache()
    if not c or "last_updated" not in c:
        return None
    last = datetime.fromisoformat(c["last_updated"])
    return (datetime.now(timezone.utc) - last).total_seconds()
