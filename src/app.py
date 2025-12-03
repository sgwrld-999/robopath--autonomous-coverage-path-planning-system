"""
Main FastAPI application entrypoint.

Initializes:
- Database tables
- Routers
- CORS configuration
- Logging middleware

Author: Siddhant Gond
"""

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.database import Base, engine
from src.routers import router as trajectory_router  # Import the router you defined


# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------

# Automatically create all tables on startup (SQLite)
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------

app = FastAPI(
    title="Wall Coverage Robot System",
    description="Backend service for autonomous wall-finishing robot trajectory planning.",
    version="1.0.0",
)


# ---------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Logging Middleware
# ---------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log each API request with timing and status.
    """
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        "Path: %s | Method: %s | Status: %d | Time: %.4fs",
        request.url.path,
        request.method,
        response.status_code,
        duration,
    )

    return response


# ---------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------

app.include_router(trajectory_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------

@app.get("/", tags=["root"])
def read_root():
    """
    Serve the frontend application.
    """
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')
