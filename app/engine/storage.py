"""
In-memory storage for graphs and runs.
Can be replaced with database implementation later.
"""
from typing import Dict, Optional, List
from app.engine.models import Graph, Run
import logging

logger = logging.getLogger(__name__)


class InMemoryStorage:
    """Simple in-memory storage for graphs and runs."""
    
    def __init__(self):
        self.graphs: Dict[str, Graph] = {}
        self.runs: Dict[str, Run] = {}
    
    # Graph operations
    def save_graph(self, graph: Graph):
        """Save or update a graph."""
        self.graphs[graph.id] = graph
        logger.info(f"Saved graph: {graph.id}")
    
    def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Retrieve a graph by ID."""
        return self.graphs.get(graph_id)
    
    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph by ID."""
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            logger.info(f"Deleted graph: {graph_id}")
            return True
        return False
    
    def list_graphs(self) -> List[str]:
        """Return list of all graph IDs."""
        return list(self.graphs.keys())
    
    # Run operations
    def save_run(self, run: Run):
        """Save or update a run."""
        from datetime import datetime
        run.updated_at = datetime.now()
        self.runs[run.run_id] = run
        logger.debug(f"Saved run: {run.run_id}, status: {run.status}")
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Retrieve a run by ID."""
        return self.runs.get(run_id)
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run by ID."""
        if run_id in self.runs:
            del self.runs[run_id]
            logger.info(f"Deleted run: {run_id}")
            return True
        return False
    
    def list_runs(self, graph_id: Optional[str] = None) -> List[str]:
        """
        Return list of run IDs, optionally filtered by graph_id.
        
        Args:
            graph_id: If provided, only return runs for this graph
        """
        if graph_id:
            return [rid for rid, run in self.runs.items() if run.graph_id == graph_id]
        return list(self.runs.keys())
    
    def clear_all(self):
        """Clear all stored data (useful for testing)."""
        self.graphs.clear()
        self.runs.clear()
        logger.warning("Cleared all storage data")


# Global singleton instance
storage = InMemoryStorage()
