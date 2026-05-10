from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import articles, briefings, qa, status
from backend.database.db import init_db
from backend.pipeline.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="AI Newsroom API", version="1.0.0")

# Allow React frontend (localhost:5173, etc) to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router,  prefix="/api/articles")
app.include_router(briefings.router, prefix="/api/briefings")
app.include_router(qa.router,        prefix="/api/qa")
app.include_router(status.router,    prefix="/api/status")


@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB schema exists (including newly added briefing table)."""
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Stop background scheduler cleanly on API shutdown."""
    stop_scheduler()

@app.get("/")
def root():
    return {"message": "AI Newsroom API is running"}