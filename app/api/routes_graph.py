"""
Graph API routes for creating, running, and monitoring workflows.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import uuid
import logging

from app.engine.models import GraphCreate, GraphResponse, RunRequest, RunResponse, StateResponse
from app.engine.engine import run_graph_sync, run_graph_async
from app.engine.storage import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket connections for streaming logs
active_connections: Dict[str, WebSocket] = {}


@router.post("/create", response_model=GraphResponse)
async def create_graph(graph_create: GraphCreate):
    """
    Create a new workflow graph.
    
    Args:
        graph_create: Graph definition with nodes, edges, and start_node
        
    Returns:
        GraphResponse with the created graph_id
    """
    try:
        # Generate unique graph ID
        graph_id = str(uuid.uuid4())
        
        # Validate graph structure
        if not graph_create.start_node:
            raise HTTPException(status_code=400, detail="start_node is required")
        
        if graph_create.start_node not in graph_create.nodes:
            raise HTTPException(
                status_code=400, 
                detail=f"start_node '{graph_create.start_node}' not found in nodes"
            )
        
        # Validate edges reference existing nodes
        node_ids = set(graph_create.nodes.keys())
        for edge in graph_create.edges:
            if edge.source not in node_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Edge source '{edge.source}' not found in nodes"
                )
            if edge.target not in node_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Edge target '{edge.target}' not found in nodes"
                )
        
        # Create graph object
        from app.engine.models import Graph
        graph = Graph(
            id=graph_id,
            nodes=graph_create.nodes,
            edges=graph_create.edges,
            start_node=graph_create.start_node
        )
        
        # Save to storage
        storage.save_graph(graph)
        
        logger.info(f"Created graph {graph_id} with {len(graph.nodes)} nodes")
        
        return GraphResponse(graph_id=graph_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating graph: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create graph: {str(e)}")


@router.post("/run", response_model=RunResponse)
async def run_graph(run_request: RunRequest, background_tasks: BackgroundTasks):
    """
    Run a workflow graph with the given initial state.
    
    Args:
        run_request: Contains graph_id, initial_state, and async flag
        background_tasks: FastAPI background tasks for async execution
        
    Returns:
        RunResponse with run_id, status, final_state, and execution log
    """
    try:
        # Retrieve graph
        graph = storage.get_graph(run_request.graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail=f"Graph {run_request.graph_id} not found")
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Check if async execution requested
        if run_request.async_execution:
            # Create pending run
            from app.engine.models import Run
            run = Run(
                run_id=run_id,
                graph_id=run_request.graph_id,
                current_node_id=graph.start_node,
                state=run_request.initial_state,
                status="pending",
                log=[]
            )
            storage.save_run(run)
            
            # Schedule background execution
            background_tasks.add_task(
                run_graph_async,
                graph,
                run_id,
                run_request.initial_state
            )
            
            logger.info(f"Scheduled async execution for run {run_id}")
            
            return RunResponse(
                run_id=run_id,
                status="pending",
                state=run_request.initial_state,
                log=[],
                message="Graph execution started in background"
            )
        else:
            # Synchronous execution
            run = run_graph_sync(graph, run_id, run_request.initial_state)
            
            logger.info(f"Completed sync execution for run {run_id}, status: {run.status}")
            
            return RunResponse(
                run_id=run.run_id,
                status=run.status,
                state=run.state,
                log=run.log
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running graph: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to run graph: {str(e)}")


@router.get("/state/{run_id}", response_model=StateResponse)
async def get_run_state(run_id: str):
    """
    Get the current state of a workflow run.
    
    Args:
        run_id: The unique identifier of the run
        
    Returns:
        StateResponse with run details, current state, and execution log
    """
    try:
        run = storage.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        return StateResponse(
            run_id=run.run_id,
            graph_id=run.graph_id,
            status=run.status,
            current_node_id=run.current_node_id,
            state=run.state,
            log=run.log
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving run state: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get run state: {str(e)}")


@router.websocket("/ws/logs/{run_id}")
async def websocket_logs(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for streaming real-time execution logs.
    
    Args:
        websocket: WebSocket connection
        run_id: The unique identifier of the run to stream logs for
    """
    await websocket.accept()
    active_connections[run_id] = websocket
    
    try:
        logger.info(f"WebSocket connection established for run {run_id}")
        
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "run_id": run_id,
            "message": "Connected to log stream"
        })
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back or handle client messages if needed
                await websocket.send_json({
                    "type": "ack",
                    "message": "Message received"
                })
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {str(e)}")
    finally:
        # Clean up connection
        if run_id in active_connections:
            del active_connections[run_id]
        logger.info(f"WebSocket connection closed for run {run_id}")


async def broadcast_log(run_id: str, log_entry: Dict[str, Any]):
    """
    Broadcast a log entry to connected WebSocket clients.
    
    Args:
        run_id: The run ID to broadcast to
        log_entry: The log entry to send
    """
    if run_id in active_connections:
        try:
            await active_connections[run_id].send_json({
                "type": "log",
                "run_id": run_id,
                "entry": log_entry
            })
        except Exception as e:
            logger.error(f"Failed to broadcast log to {run_id}: {str(e)}")
