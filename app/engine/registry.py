"""
Tool registry for managing callable tools used by workflow nodes.
"""
from typing import Callable, Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class Tool:
    """Wrapper for a tool function with metadata."""
    
    def __init__(self, name: str, func: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
        self.name = name
        self.func = func
    
    def execute(self, state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool function with given state and parameters."""
        return self.func(state, params)


class ToolRegistry:
    """Registry for managing and retrieving tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, name: str, func: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
        """
        Register a new tool.
        
        Args:
            name: Unique tool name
            func: Function that takes (state, params) and returns updated state dict
        """
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")
        
        self.tools[name] = Tool(name, func)
        logger.info(f"Registered tool: {name}")
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Retrieve a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Return list of all registered tool names."""
        return list(self.tools.keys())
    
    def unregister(self, name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool was removed, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False


# Global singleton instance
tool_registry = ToolRegistry()
