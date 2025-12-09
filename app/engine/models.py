"""
Pydantic models for the workflow engine.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime


class Node(BaseModel):
    """Represents a single node in the workflow graph."""
    id: str
    type: Literal["tool", "router", "loop"]
    tool_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    """Represents a directed edge between nodes."""
    source: str
    target: str
    condition: Optional[str] = None


class Graph(BaseModel):
    """Complete workflow graph definition."""
    id: str
    nodes: Dict[str, Node]
    edges: List[Edge]
    start_node: str


class GraphCreate(BaseModel):
    """Request model for creating a new graph."""
    nodes: Dict[str, Node]
    edges: List[Edge]
    start_node: str


class GraphResponse(BaseModel):
    """Response model after creating a graph."""
    graph_id: str


class ExecutionStep(BaseModel):
    """Log entry for a single node execution."""
    node_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_state: Dict[str, Any]
    output_state: Dict[str, Any]
    status: Literal["running", "completed", "failed"] = "running"
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    """Represents a single workflow execution run."""
    run_id: str
    graph_id: str
    current_node_id: Optional[str]
    state: Dict[str, Any]
    status: Literal["pending", "running", "completed", "failed"]
    log: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RunRequest(BaseModel):
    """Request model for running a graph."""
    graph_id: str
    initial_state: Dict[str, Any]
    async_execution: bool = False


class RunResponse(BaseModel):
    """Response model after starting or completing a run."""
    run_id: str
    status: str
    state: Dict[str, Any]
    log: List[Dict[str, Any]]
    message: Optional[str] = None


class StateResponse(BaseModel):
    """Response model for querying run state."""
    run_id: str
    graph_id: str
    status: str
    current_node_id: Optional[str]
    state: Dict[str, Any]
    log: List[Dict[str, Any]]
