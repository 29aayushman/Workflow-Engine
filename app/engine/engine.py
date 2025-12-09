"""
Core workflow execution engine.
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.engine.models import Graph, Run, Node, ExecutionStep
from app.engine.registry import tool_registry
from app.engine.storage import storage

logger = logging.getLogger(__name__)


def evaluate_condition(condition: str, state: Dict[str, Any]) -> bool:
    """
    Safely evaluate a condition expression against the state.
    
    Args:
        condition: Python expression as string (e.g., "state['count'] > 5")
        state: Current workflow state
        
    Returns:
        Boolean result of condition evaluation
    """
    try:
        # Create safe namespace with only state available
        namespace = {"state": state}
        result = eval(condition, {"__builtins__": {}}, namespace)
        return bool(result)
    except Exception as e:
        logger.error(f"Error evaluating condition '{condition}': {str(e)}")
        return False


def get_next_node_id(graph: Graph, state: Dict[str, Any], current_node_id: str) -> Optional[str]:
    """
    Determine the next node to execute based on edges and conditions.
    
    Args:
        graph: The workflow graph
        state: Current state
        current_node_id: ID of the node that just completed
        
    Returns:
        Next node ID or None if workflow is complete
    """
    # Find all edges from current node
    outgoing_edges = [e for e in graph.edges if e.source == current_node_id]
    
    if not outgoing_edges:
        logger.info(f"No outgoing edges from {current_node_id}, workflow complete")
        return None
    
    # Check conditional edges first
    for edge in outgoing_edges:
        if edge.condition:
            if evaluate_condition(edge.condition, state):
                logger.info(f"Condition '{edge.condition}' satisfied, routing to {edge.target}")
                return edge.target
        else:
            # Unconditional edge
            return edge.target
    
    # If no condition matched, return first edge's target as fallback
    return outgoing_edges[0].target


def execute_node(run: Run, graph: Graph) -> Run:
    """
    Execute the current node and update the run state.
    
    Args:
        run: Current run instance
        graph: The workflow graph
        
    Returns:
        Updated run instance
    """
    if not run.current_node_id:
        logger.warning(f"Run {run.run_id} has no current node")
        return run
    
    node = graph.nodes.get(run.current_node_id)
    if not node:
        logger.error(f"Node {run.current_node_id} not found in graph")
        run.status = "failed"
        return run
    
    logger.info(f"Executing node {node.id} (type: {node.type}) for run {run.run_id}")
    
    # Create execution step log
    step_log = {
        "node_id": node.id,
        "node_type": node.type,
        "started_at": datetime.now().isoformat(),
        "input_state": run.state.copy()
    }
    
    try:
        if node.type == "tool":
            # Execute tool
            if not node.tool_name:
                raise ValueError(f"Tool node {node.id} has no tool_name specified")
            
            tool = tool_registry.get(node.tool_name)
            if not tool:
                raise ValueError(f"Tool '{node.tool_name}' not found in registry")
            
            # Execute tool and merge result into state
            result = tool.execute(run.state, node.params)
            run.state.update(result)
            
            step_log["tool_name"] = node.tool_name
            step_log["tool_params"] = node.params
            
        elif node.type == "router":
            # Router just evaluates conditions in edges, no state change
            step_log["metadata"] = {"type": "router"}
            
        elif node.type == "loop":
            # Loop node can set loop metadata
            step_log["metadata"] = {"type": "loop"}
        
        # Mark step as completed
        step_log["finished_at"] = datetime.now().isoformat()
        step_log["output_state"] = run.state.copy()
        step_log["status"] = "completed"
        
    except Exception as e:
        logger.error(f"Error executing node {node.id}: {str(e)}")
        step_log["finished_at"] = datetime.now().isoformat()
        step_log["status"] = "failed"
        step_log["error"] = str(e)
        run.status = "failed"
    
    # Add step to log
    run.log.append(step_log)
    
    return run


def run_graph_sync(graph: Graph, run_id: str, initial_state: Dict[str, Any]) -> Run:
    """
    Execute a graph synchronously from start to finish.
    
    Args:
        graph: The workflow graph to execute
        run_id: Unique run identifier
        initial_state: Starting state
        
    Returns:
        Completed Run instance
    """
    # Create run
    run = Run(
        run_id=run_id,
        graph_id=graph.id,
        current_node_id=graph.start_node,
        state=initial_state.copy(),
        status="running",
        log=[]
    )
    
    storage.save_run(run)
    logger.info(f"Starting sync execution for run {run_id}, graph {graph.id}")
    
    max_iterations = 100  # Prevent infinite loops
    iteration = 0
    
    while run.current_node_id and run.status == "running" and iteration < max_iterations:
        iteration += 1
        
        # Execute current node
        run = execute_node(run, graph)
        
        if run.status == "failed":
            break
        
        # Get next node
        next_node_id = get_next_node_id(graph, run.state, run.current_node_id)
        run.current_node_id = next_node_id
        
        # Save progress
        storage.save_run(run)
    
    # Mark as completed if we finished successfully
    if run.status == "running":
        if iteration >= max_iterations:
            run.status = "failed"
            run.log.append({
                "error": "Max iterations reached",
                "timestamp": datetime.now().isoformat()
            })
        else:
            run.status = "completed"
    
    storage.save_run(run)
    logger.info(f"Finished sync execution for run {run_id}, status: {run.status}")
    
    return run


async def run_graph_async(graph: Graph, run_id: str, initial_state: Dict[str, Any]):
    """
    Execute a graph asynchronously (for background tasks).
    
    Args:
        graph: The workflow graph to execute
        run_id: Unique run identifier
        initial_state: Starting state
    """
    # For now, just call sync version
    # In production, you could add async tool support, streaming, etc.
    run = run_graph_sync(graph, run_id, initial_state)
    
    # Optionally broadcast to WebSocket clients here
    logger.info(f"Async execution completed for run {run_id}")
