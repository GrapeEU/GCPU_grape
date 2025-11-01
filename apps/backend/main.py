# -*- coding: utf-8 -*-
"""
Grape Backend - Main FastAPI Application Entry Point

This is the main entry point for the Grape backend API server.
It initializes FastAPI, configures middleware, and registers all route handlers.

Architecture Overview:
----------------------
- FastAPI REST API server
- MCP (Model Context Protocol) pipelines for KG operations
- Integration with gen2kgbot for NL2SPARQL conversion
- Google Cloud Platform deployment ready (Cloud Run)

Usage:
------
Development:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Production:
    uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4

With uv:
    uv run uvicorn main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from api.routes import health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    This is where you initialize connections, load models, etc.
    """
    # Startup
    logger.info("Starting Grape Backend API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Host: {settings.api_host}:{settings.api_port}")

    # gen2kgbot adapters and MCP tooling are initialised lazily when the first
    # request hits the relevant endpoint, which keeps startup lightweight.

    logger.info("Grape Backend API ready!")

    yield

    # Shutdown
    logger.info("Shutting down Grape Backend API...")
    logger.info("Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Grape Backend API",
    description="""
    **Grape Backend API** - Knowledge Graph querying with MCP pipelines and gen2kgbot integration.

    ## Features

    * **9 AI-powered scenarios** for KG exploration and reasoning
    * **9 MCP pipelines** as reusable tools
    * **gen2kgbot integration** for NL2SPARQL conversion
    * **GraphDB/SPARQL** backend support
    * **Google Cloud Platform** ready (Vertex AI, Cloud Run)

    ## Scenarios

    1. **Concept Exploration** - Explore information around a concept
    2. **Multi-hop Reasoning** - Find logical paths between concepts
    3. **NL2SPARQL Adaptive** - Complex question to SPARQL with context
    4. **Cross-KG Federation** - Link concepts across multiple knowledge graphs
    5. **Validation/Proof** - Prove or refute assertions
    6. **Explainable Reasoning** - Explain the reasoning path taken
    7. **Filtered Exploration** - Query with business constraints
    8. **Alignment Detection** - Detect agreements/divergences between KGs
    9. **Decision Synthesis** - Actionable synthesis with traceability
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again later.",
            "details": str(exc) if settings.environment == "development" else None,
        },
    )


# Register route handlers
app.include_router(health.router, prefix="/api")

# MCP Tools
from api import mcp
app.include_router(mcp.router, prefix="/api")

# Graph data
from api import graph
app.include_router(graph.router, prefix="/api")

# Agent
from api import agent
app.include_router(agent.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Grape Backend API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        reload_excludes=[
            ".venv/*",
            "venv/*",
            "*.pyc",
            "__pycache__/*",
            "gen2kgbot/*",
        ],
        reload_includes=["*.py"],
        log_level=settings.log_level.lower(),
    )
