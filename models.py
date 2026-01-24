from enum import Enum
from pydantic import BaseModel, Field


class SessionType(str, Enum):
    """Available exam session types."""
    NOVEMBER = "November"
    MAYJUNE = "MayJune"
    FEBMARCH = "FebMarch"
    SUPPLEMENTARY = "Supplementary"


class Language(str, Enum):
    """Available paper languages."""
    ENGLISH = "English"
    AFRIKAANS = "Afrikaans"


class PaperNumber(str, Enum):
    """Paper numbers."""
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


# --- Response Models ---

class ExamSession(BaseModel):
    """Exam session information."""
    original_text: str = Field(..., description="Original link text from source")
    year: str = Field(..., description="Exam year", examples=["2024", "2025"])
    session: str | None = Field(..., description="Session type (November, MayJune, FebMarch, Supplementary)")
    working_url: str = Field(..., description="URL to scrape papers from")


class SessionsResponse(BaseModel):
    """Response for GET /sessions endpoint."""
    source_url: str = Field(..., description="Source page URL")
    total: int = Field(..., description="Total number of sessions")
    sessions: list[ExamSession]


class SessionsByYearResponse(BaseModel):
    """Response for GET /sessions/{year} endpoint."""
    year: str = Field(..., description="Requested year")
    total: int = Field(..., description="Number of sessions found")
    sessions: list[ExamSession]


class PaperLinks(BaseModel):
    """Download links for a paper, organized by language."""
    paper: dict[str, str] = Field(
        default_factory=dict,
        description="Question paper download URLs keyed by language (English, Afrikaans, or 'default' if no language specified)"
    )
    memo: dict[str, str] = Field(
        default_factory=dict,
        description="Memorandum download URLs keyed by language"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "paper": {"English": "https://education.gov.za/...", "Afrikaans": "https://education.gov.za/..."},
                "memo": {"English": "https://education.gov.za/..."}
            }]
        }
    }


class PapersResponse(BaseModel):
    """
    Response for GET /papers/{year}/{session} endpoint.

    Papers are grouped by subject, then by paper number (P1, P2, P3).
    Each paper has download links organized by language.
    """
    year: str = Field(..., description="Exam year")
    session: str = Field(..., description="Session type")
    source_url: str = Field(..., description="Source page URL that was scraped")
    total_subjects: int = Field(..., description="Number of subjects returned (may be filtered)")
    subjects: dict[str, dict[str, PaperLinks]] = Field(
        ...,
        description="Papers grouped by subject -> paper number -> language -> URL"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "year": "2025",
                "session": "MayJune",
                "source_url": "https://education.gov.za/...",
                "total_subjects": 2,
                "subjects": {
                    "Mathematics": {
                        "P1": {
                            "paper": {"English": "https://...", "Afrikaans": "https://..."},
                            "memo": {}
                        },
                        "P2": {
                            "paper": {"English": "https://..."},
                            "memo": {}
                        }
                    },
                    "Physical Sciences": {
                        "P1": {
                            "paper": {"English": "https://..."},
                            "memo": {}
                        }
                    }
                }
            }]
        }
    }


class SubjectsListResponse(BaseModel):
    """Response for GET /subjects/{year}/{session} endpoint."""
    year: str = Field(..., description="Exam year")
    session: str = Field(..., description="Session type")
    total: int = Field(..., description="Number of subjects")
    subjects: list[str] = Field(..., description="Alphabetically sorted list of subject names")


class AvailableValuesResponse(BaseModel):
    """
    Response for GET /values endpoint.

    Shows all acceptable parameter values for the API.
    """
    sessions: list[str] = Field(
        default=["November", "MayJune", "FebMarch", "Supplementary"],
        description="Valid session types to use in {session} path parameter"
    )
    years: list[str] = Field(
        ...,
        description="Available years in the database (sorted descending)"
    )
    sample_subjects: list[str] = Field(
        ...,
        description="Sample list of subjects (from latest session) - use /subjects/{year}/{session} for full list"
    )
    languages: list[str] = Field(
        default=["English", "Afrikaans"],
        description="Paper language variants in download links"
    )
    paper_numbers: list[str] = Field(
        default=["P1", "P2", "P3"],
        description="Valid paper numbers"
    )


class RootResponse(BaseModel):
    """Response for GET / endpoint."""
    message: str = Field(default="NSC Past Papers API")
    source: str = Field(default="Department of Basic Education (education.gov.za)")
    endpoints: dict[str, str] = Field(..., description="Available API endpoints")
