from pydantic import BaseModel


class ExamSession(BaseModel):
    original_text: str
    year: str
    session: str | None
    working_url: str


class PaperLinks(BaseModel):
    paper: str | None = None
    memo: str | None = None


class SubjectPapers(BaseModel):
    subject: str
    papers: dict[str, PaperLinks]


class ExamSessionsResponse(BaseModel):
    source_url: str
    total: int
    sessions: list[ExamSession]


class PapersResponse(BaseModel):
    year: str
    session: str | None
    source_url: str
    total_subjects: int
    subjects: dict[str, dict[str, PaperLinks]]
