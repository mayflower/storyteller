"""
StoryCraft Agent Package - A multi-component story generation system using LangGraph.
"""

import functools
import time
import inspect
from typing import Dict, Any, Callable, Optional

# Global progress tracking
_progress_callback = None
_start_time = None
_node_counts = {}

def track_progress(node_func: Callable) -> Callable:
    """
    Decorator for tracking progress in node functions.
    
    Args:
        node_func: The node function to track
        
    Returns:
        Wrapped function that reports progress
    """
    @functools.wraps(node_func)
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        global _progress_callback, _start_time, _node_counts
        
        # Initialize tracking if needed
        if _start_time is None:
            _start_time = time.time()
            
        # Get node name
        node_name = node_func.__name__
        
        # Update node counts
        if node_name not in _node_counts:
            _node_counts[node_name] = 0
        _node_counts[node_name] += 1
        
        # Execute the node function
        result = node_func(state)
        
        # Report progress if callback is set
        if _progress_callback:
            # Calculate elapsed time
            elapsed = time.time() - _start_time
            
            # Call the progress callback with node name and state
            _progress_callback(node_name, result)
            
        return result
    
    return wrapper

def set_progress_callback(callback: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
    """
    Set the global progress tracking callback.
    
    Args:
        callback: Function to call for progress updates or None to disable
    """
    global _progress_callback, _start_time, _node_counts
    _progress_callback = callback
    _start_time = None
    _node_counts = {}

def reset_progress_tracking() -> None:
    """Reset all progress tracking variables."""
    global _progress_callback, _start_time, _node_counts
    _start_time = None
    _node_counts = {}

# Export public API
from storyteller_lib.storyteller import generate_story

__all__ = ["generate_story", "track_progress", "set_progress_callback", "reset_progress_tracking"]