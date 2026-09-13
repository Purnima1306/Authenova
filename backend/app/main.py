"""
Authenova Main FastAPI Application
AI-powered identity and document verification platform.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import init_db
from app.api.routes import health, upload, extraction, validation, tampering, face, risk, report, screening


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize persistent storage / tables on startup
    init_db()
    yield


app = FastAPI(
    title="Authenova API",
    description="AI-powered identity and document verification platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware to allow React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(extraction.router, prefix="/api/v1", tags=["extraction"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
app.include_router(tampering.router, prefix="/api/v1", tags=["tampering"])
app.include_router(face.router, prefix="/api/v1", tags=["face"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(report.router, prefix="/api/v1", tags=["report"])
app.include_router(screening.router, prefix="/api/v1", tags=["screening"])


@app.get("/")
def root():
    return {
        "message": "Authenova API is running",
        "version": "1.0.0",
        "status": "operational"
    }
