"""
FastAPI application entry point for the Workflow Engine.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import routes_graph
from app.workflows.data_quality import register_data_quality_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Workflow Engine API",
    description="A minimal workflow engine for executing graph-based workflows with nodes, edges, and state management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
app.include_router(
    routes_graph.router,
    prefix="/graph",
    tags=["Graph Operations"]
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Workflow Engine API...")
    
    # Register workflow tools
    register_data_quality_tools()
    logger.info("Registered all workflow tools")
    
    logger.info("Workflow Engine API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Workflow Engine API...")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Workflow Engine API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "create_graph": "POST /graph/create",
            "run_graph": "POST /graph/run",
            "get_state": "GET /graph/state/{run_id}",
            "websocket_logs": "WS /graph/ws/logs/{run_id}"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "workflow-engine"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )