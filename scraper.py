import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re

# DBE Main Site (Languages and Technical subjects)
DOMAIN = "https://www.education.gov.za"
BASE_URL = f"{DOMAIN}/Curriculum/NationalSeniorCertificate(NSC)Examinations/"
MAIN_PAGE_URL = BASE_URL + "NSCPastExaminationpapers.aspx"

# Eastern Cape Site (All subjects including Math, Science, etc.)
EC_DOMAIN = "http://www.ecexams.co.za"
EC_INDEX_URL = f"{EC_DOMAIN}/ExaminationPapers.htm"


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


def parse_paper_text(text: str) -> dict | None:
    """
    Parse paper link text to extract subject, paper number, and type.

    Examples:
    - "Afrikaans FAL P1" -> subject="Afrikaans FAL", paper="P1", is_memo=False
    - "Afrikaans FAL P1 memo" -> subject="Afrikaans FAL", paper="P1", is_memo=True
    - "Mathematics P2" -> subject="Mathematics", paper="P2", is_memo=False
    """
    text = text.strip()

    # Check if it's a memo
    is_memo = "memo" in text.lower()

    # Extract paper number (P1, P2, P3)
    paper_match = re.search(r"\b(P[1-3])\b", text, re.IGNORECASE)
    if not paper_match:
        return None

    paper = paper_match.group(1).upper()

    # Extract subject (everything before the paper number)
    subject_part = text[:paper_match.start()].strip()

    # Clean up subject name
    subject = subject_part.strip()
    if not subject:
        return None

    # Extract province if present (in parentheses at the end)
    province = None
    province_match = re.search(r"\(([^)]+)\)\s*$", text)
    if province_match:
        province = province_match.group(1)

    return {
        "subject": subject,
        "paper": paper,
        "is_memo": is_memo,
        "province": province,
        "original_text": text,
    }


def scrape_papers_from_url(url: str) -> list[dict]:
    """
    Scrape a specific exam papers page and extract all paper/memo links.
    Returns list of papers with download URLs.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    papers = []
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)

        # Filter: only links with fileticket (actual downloads)
        if "fileticket" not in href:
            continue

        parsed = parse_paper_text(text)
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
            "P1": {"paper": "url", "memo": "url"},
            "P2": {"paper": "url", "memo": "url"}
        }
    }
    """
    grouped = {}

    for p in papers:
        subject = p["subject"]
        paper_num = p["paper"]
        is_memo = p["is_memo"]
        url = p["download_url"]
        province = p.get("province")

        if subject not in grouped:
            grouped[subject] = {}

        # Handle provincial papers differently
        if province:
            key = f"{paper_num} ({province})"
        else:
            key = paper_num

        if key not in grouped[subject]:
            grouped[subject][key] = {"paper": None, "memo": None}

        if is_memo:
            grouped[subject][key]["memo"] = url
        else:
            grouped[subject][key]["paper"] = url

    return grouped


# =============================================================================
# Eastern Cape Site Scraper (ecexams.co.za) - All subjects
# =============================================================================

def get_ec_exam_sessions() -> list[dict]:
    """Get all exam sessions from Eastern Cape site."""
    response = requests.get(EC_INDEX_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    sessions = []
    for a_tag in soup.find_all("a"):
        text = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")

        # Filter for Grade 12 NSC/DBE exams
        if not href.endswith(".htm"):
            continue
        if "Gr_12" not in href and "Gr12" not in href and "NSC" not in href:
            continue

        year, session = extract_year_month(text)
        if not year:
            # Try extracting from href
            year_match = re.search(r"(20\d{2})", href)
            year = year_match.group(1) if year_match else None

        if not year:
            continue

        # Determine session from href or text
        if not session:
            if "November" in href or "November" in text:
                session = "November"
            elif "MayJune" in href or "May" in text or "June" in text:
                session = "MayJune"
            elif "September" in href or "Trial" in text:
                session = "September"
            elif "FebMarch" in href or "Supplementary" in text:
                session = "FebMarch"

        # Build full URL
        if href.startswith("http"):
            full_url = href
        else:
            full_url = f"{EC_DOMAIN}/{href}"

        sessions.append({
            "original_text": text.replace("\n", " ").replace("\t", " ").strip(),
            "year": year,
            "session": session,
            "working_url": full_url,
            "source": "ecexams",
        })

    return sessions


def get_ec_sessions_by_year(year: str) -> list[dict]:
    """Get Eastern Cape exam sessions filtered by year."""
    sessions = get_ec_exam_sessions()
    return [s for s in sessions if s["year"] == year]


def parse_ec_paper_url(url: str) -> list[dict]:
    """
    Parse paper info from Eastern Cape download URL.
    Returns a list because some files contain multiple papers (P1 P2 P3).

    Examples:
    - "Mathematics P1 Nov 2024.zip" -> [{"subject": "Mathematics", "paper": "P1", "is_memo": False}]
    - "Mathematics P1 Nov 2024 MG Afr & Eng.zip" -> [{"subject": "Mathematics", "paper": "P1", "is_memo": True}]
    - "Afrikaans HL P1 P2 P3.zip" -> [{"subject": "Afrikaans HL", "paper": "P1"}, ...]
    - "Afrikaans HL MG P1 P2 P3.zip" -> [{"subject": "Afrikaans HL", "paper": "P1", "is_memo": True}, ...]
    """
    # Decode URL
    decoded = unquote(url)
    filename = decoded.split("/")[-1]

    # Remove file extension
    name = re.sub(r"\.(zip|pdf)$", "", filename, flags=re.IGNORECASE)

    # Check if it's a memo (MG = Memorandum/Marking Guidelines)
    is_memo = " MG " in name or " MG" in name

    # Extract all paper numbers (P1, P2, P3)
    paper_matches = re.findall(r"\b(P[1-3])\b", name, re.IGNORECASE)
    if not paper_matches:
        return []

    # Extract subject: everything before the first P1/P2/P3 or MG
    # Use regex to find the position where subject ends
    subject_end = re.search(r"\s+(MG\s+)?P[1-3]\b", name, re.IGNORECASE)
    if not subject_end:
        return []

    subject = name[:subject_end.start()].strip()

    if not subject:
        return []

    # Create entry for each paper number found (deduplicate)
    results = []
    seen_papers = set()
    for paper in paper_matches:
        paper_upper = paper.upper()
        if paper_upper not in seen_papers:
            seen_papers.add(paper_upper)
            results.append({
                "subject": subject,
                "paper": paper_upper,
                "is_memo": is_memo,
                "filename": filename,
            })

    return results


def scrape_ec_papers_from_url(url: str) -> list[dict]:
    """
    Scrape papers from an Eastern Cape exam page.
    Returns list of papers with download URLs.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    # Get the base path for relative URLs
    base_path = "/".join(url.split("/")[:-1])

    papers = []
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")

        # Filter: only zip/pdf files
        if not (href.endswith(".zip") or href.endswith(".pdf")):
            continue

        # parse_ec_paper_url now returns a list
        parsed_list = parse_ec_paper_url(href)
        if not parsed_list:
            continue

        # Build full download URL
        if href.startswith("http"):
            download_url = href
        else:
            download_url = f"{base_path}/{href}"

        # Add download URL to each parsed entry
        for parsed in parsed_list:
            parsed["download_url"] = download_url
            papers.append(parsed)

    return papers


def group_ec_papers_by_subject(papers: list[dict]) -> dict:
    """
    Group Eastern Cape papers by subject.
    Similar structure to group_papers_by_subject but handles EC format.
    """
    grouped = {}

    for p in papers:
        subject = p["subject"]
        paper_num = p["paper"]
        is_memo = p["is_memo"]
        url = p["download_url"]

        if subject not in grouped:
            grouped[subject] = {}

        if paper_num not in grouped[subject]:
            grouped[subject][paper_num] = {"paper": None, "memo": None}

        if is_memo:
            grouped[subject][paper_num]["memo"] = url
        else:
            grouped[subject][paper_num]["paper"] = url

    return grouped
