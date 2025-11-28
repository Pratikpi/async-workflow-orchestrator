"""Main application entry point."""
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from src.db import init_db
from src.api import workflow_router, task_router, execution_router, workflow_api_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("workflow_orchestrator.log"),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting Async Workflow Orchestrator")
    logger.info(f"Database URL: {settings.database_url}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Async Workflow Orchestrator")
    
    # Shutdown worker manager if it exists
    from src.api.execution import _worker_manager
    if _worker_manager:
        _worker_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Async Workflow Orchestrator",
    description="A lightweight workflow orchestrator using async I/O, threads, and state machines",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflow_api_router)  # New simplified /workflow/* endpoints
app.include_router(workflow_router)
app.include_router(task_router)
app.include_router(execution_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Async Workflow Orchestrator API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
