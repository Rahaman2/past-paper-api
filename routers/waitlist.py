from fastapi import APIRouter, HTTPException
from models import WaitlistRequest, WaitlistSubmitResponse, AdminWaitlistResponse, WaitlistEntry
import database

router = APIRouter(prefix="/api")


@router.post("/waitlist", response_model=WaitlistSubmitResponse)
def submit_waitlist(body: WaitlistRequest):
    """Add a new entry to the waitlist."""
    new_id = database.insert_entry(
        name=body.name,
        whatsapp=body.whatsapp,
        grade=body.grade,
        subject=body.subject,
        preference=body.preference,
        email=body.email,
    )
    return WaitlistSubmitResponse(
        success=True,
        message="You're on the waitlist! We'll be in touch soon.",
        id=new_id,
    )


@router.get("/admin/waitlist", response_model=AdminWaitlistResponse)
def get_waitlist():
    """Return all waitlist entries (admin only — no auth for now)."""
    entries = database.get_all_entries()
    return AdminWaitlistResponse(
        total=len(entries),
        entries=[WaitlistEntry(**e) for e in entries],
    )
