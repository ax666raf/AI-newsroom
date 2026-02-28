from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import articles, briefings, status

app = FastAPI(title="AI Newsroom API", version="1.0.0")

# Allow React frontend (localhost:5173) to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router,  prefix="/api/articles")
app.include_router(briefings.router, prefix="/api/briefings")
app.include_router(status.router,    prefix="/api/status")

@app.get("/")
def root():
    return {"message": "AI Newsroom API is running"}