import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re

# DBE Main Site (All subjects)
DOMAIN = "https://www.education.gov.za"
BASE_URL = f"{DOMAIN}/Curriculum/NationalSeniorCertificate(NSC)Examinations/"
MAIN_PAGE_URL = BASE_URL + "NSCPastExaminationpapers.aspx"


def extract_year_month(text: str) -> tuple[str | None, str | None]:
    """
    Extract year and month/session from text.
    Returns (year, session) e.g., ("2025", "MayJune")
    """
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = year_match.group(1) if year_match else None

    session_patterns = [
        (r"May\s*/?\s*June", "MayJune"),
        (r"Feb\s*/?\s*March", "FebMarch"),
        (r"November", "November"),
        (r"Supplementary", "Supplementary"),
    ]

    session = None
    for pattern, name in session_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            session = name
            break

    return year, session


def extract_embedded_url(href: str) -> str | None:
    """Extract actual URL from LinkClick.aspx href if present."""
    if not href:
        return None

    if href.startswith("https://"):
        return href

    if "link=" in href:
        link_param = href.split("link=")[1].split("&")[0]
        decoded = unquote(link_param)
        if decoded.startswith("http"):
            return decoded.rstrip("+").strip()

    return None


def build_full_url(href: str) -> str:
    """Build full URL from href (handles relative paths)."""
    if not href:
        return ""
    if href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{DOMAIN}{href}"
    return href


def get_exam_sessions() -> list[dict]:
    """Scrape the main page and return all exam sessions."""
    response = requests.get(MAIN_PAGE_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find(id="dnn_ctr1741_Links_lstLinks")

    if not table:
        return []

    sessions = []
    for a_tag in table.find_all("a"):
        text = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")

        if not text:
            continue

        year, session = extract_year_month(text)
        if not year:
            continue

        embedded_url = extract_embedded_url(href)
        working_url = embedded_url if embedded_url else build_full_url(href)

        sessions.append({
            "original_text": text,
            "year": year,
            "session": session,
            "working_url": working_url,
        })

    return sessions


def get_sessions_by_year(year: str) -> list[dict]:
    """Get exam sessions filtered by year."""
    sessions = get_exam_sessions()
    return [s for s in sessions if s["year"] == year]


def parse_paper_link(text: str, current_subject: str) -> dict | None:
    """
    Parse paper link text to extract paper number and type.
    Subject is provided from the context (h2 header).

    Examples:
    - "Paper 1 (English)" with subject="Mathematics" -> paper="P1", is_memo=False
    - "Paper 2 memo" with subject="Accounting" -> paper="P2", is_memo=True
    - "Afrikaans FAL P1" -> subject="Afrikaans FAL", paper="P1" (subject from text)
    """
    text = text.strip()

    # Check if it's a memo
    is_memo = "memo" in text.lower()

    # Extract paper number - match both "P1/P2/P3" and "Paper 1/Paper 2/Paper 3"
    paper_match = re.search(r"\b(P[1-3])\b", text, re.IGNORECASE)
    if not paper_match:
        paper_match = re.search(r"\bPaper\s*([1-3])\b", text, re.IGNORECASE)
        if not paper_match:
            return None
        paper = f"P{paper_match.group(1)}"
    else:
        paper = paper_match.group(1).upper()

    # Try to extract subject from text (for language variants like "Afrikaans FAL P1")
    subject_part = text[:paper_match.start()].strip()

    # If we found a subject in the link text (e.g., "Afrikaans FAL P1"), use it
    # Otherwise use the current_subject from the h2 header
    if subject_part and not subject_part.lower().startswith("paper"):
        subject = subject_part
    else:
        subject = current_subject

    if not subject:
        return None

    # Extract language variant if present (in parentheses)
    # e.g., "Paper 1 (English)" or "Paper 1 (Afrikaans)"
    lang_match = re.search(r"\((English|Afrikaans|Afr|Eng)[^)]*\)", text, re.IGNORECASE)
    language = None
    if lang_match:
        lang = lang_match.group(1).lower()
        if lang in ("afrikaans", "afr"):
            language = "Afrikaans"
        elif lang in ("english", "eng"):
            language = "English"

    return {
        "subject": subject,
        "paper": paper,
        "is_memo": is_memo,
        "language": language,
        "original_text": text,
    }


def scrape_papers_from_url(url: str) -> list[dict]:
    """
    Scrape a specific exam papers page and extract all paper/memo links.
    Uses h2 headers to identify subjects, then finds paper links under each.
    Returns list of papers with download URLs.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    papers = []
    current_subject = None

    # Skip these h2 headers that are not subjects
    skip_headers = {"languages", "non languages", "non-languages"}

    # Iterate through all elements to maintain order
    for element in soup.find_all(["h2", "a"]):
        if element.name == "h2":
            # Update current subject from h2 header
            header_text = element.get_text(strip=True)
            if header_text.lower() not in skip_headers:
                current_subject = header_text
        elif element.name == "a" and current_subject:
            href = element.get("href", "")
            text = element.get_text(strip=True)

            # Filter: only links with fileticket (actual downloads)
            if "fileticket" not in href:
                continue

            parsed = parse_paper_link(text, current_subject)
            if not parsed:
                continue

            parsed["download_url"] = build_full_url(href)
            papers.append(parsed)

    return papers


def group_papers_by_subject(papers: list[dict]) -> dict:
    """
    Group papers by subject, organizing question papers and memos together.

    Returns structure like:
    {
        "Mathematics": {
            "P1": {"paper": {"English": "url", "Afrikaans": "url"}, "memo": {"English": "url"}},
            "P2": {"paper": {"English": "url"}, "memo": {"English": "url"}}
        }
    }
    """
    grouped = {}

    for p in papers:
        subject = p["subject"]
        paper_num = p["paper"]
        is_memo = p["is_memo"]
        url = p["download_url"]
        language = p.get("language", "default")

        if subject not in grouped:
            grouped[subject] = {}

        if paper_num not in grouped[subject]:
            grouped[subject][paper_num] = {"paper": {}, "memo": {}}

        if is_memo:
            grouped[subject][paper_num]["memo"][language] = url
        else:
            grouped[subject][paper_num]["paper"][language] = url

    return grouped
