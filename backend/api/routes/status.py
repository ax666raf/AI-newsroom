from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.database.models import CollectionLog

router = APIRouter()


@router.get("")
@router.get("/")
def get_status(db: Session = Depends(get_db)):
    """Return information about the most recent pipeline run."""
    latest = db.query(CollectionLog).order_by(CollectionLog.run_at.desc()).first()
    if latest is None:
        return {
            "last_run_at": None,
            "articles_collected": 0,
            "stories_processed": 0,
            "groups_created": 0,
            "status": "unknown",
            "success": False,
            "notes": "No pipeline runs recorded yet",
        }

    status_text = (latest.status or "unknown").lower()
    return {
        "last_run_at": latest.run_at.isoformat() if latest.run_at else None,
        "articles_collected": int(latest.articles_found or 0),
        "stories_processed": int(latest.new_stories or 0),
        "groups_created": int(latest.groups_created or 0),
        "status": status_text,
        "success": status_text in {"success", "partial"},
        "notes": latest.notes,
    }
