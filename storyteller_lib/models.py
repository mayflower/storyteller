"""
StoryCraft Agent - Data models and state definitions.
"""

from typing import Annotated, Dict, List, Union, Any
from typing_extensions import TypedDict
from operator import add

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import add_messages

# Custom state reducers for merging complex story elements
# Define type aliases to avoid circular imports
SceneStateDict = Dict[str, Dict[str, Union[str, List[str]]]]
ChapterStateDict = Dict[str, Dict[str, Union[str, Dict]]]
CharacterProfileDict = Dict[str, Dict[str, Union[str, List[str], Dict]]]
WorldElementsDict = Dict[str, Dict[str, Union[str, List[str], Dict]]]

def merge_lists(existing: List[Any], new: List[Any]) -> List[Any]:
    """Merge two lists, appending new values to existing list."""
    if not existing:
        return new
    if not new:
        return existing
    return existing + new

def merge_dicts(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with values from new dict taking precedence."""
    result = existing.copy()
    for key, value in new.items():
        result[key] = value
    return result

def merge_characters(existing: CharacterProfileDict, new: CharacterProfileDict) -> CharacterProfileDict:
    """Deep merge character profiles to properly handle lists and nested content."""
    # Handle the case where existing or new is None
    if existing is None:
        return new if new is not None else {}
    if new is None:
        return existing
    
    result = existing.copy()
    for char_id, char_data in new.items():
        # Skip if char_data is None
        if char_data is None:
            continue
            
        if char_id in result:
            # If character exists, update fields intelligently
            result_char = result[char_id].copy()
            
            # Special handling for list fields that should be appended
            for list_field in ["evolution", "known_facts", "secret_facts", "revealed_facts"]:
                # Check if the field exists in char_data and is not None
                if list_field in char_data and char_data[list_field] is not None:
                    # Only process if the field has a value (not empty)
                    if char_data[list_field]:
                        if list_field in result_char and result_char[list_field] is not None:
                            result_char[list_field] = result_char[list_field] + char_data[list_field]
                        else:
                            result_char[list_field] = char_data[list_field]
            
            # Special handling for relationships dict
            if "relationships" in char_data and char_data["relationships"] is not None:
                if "relationships" in result_char and result_char["relationships"] is not None:
                    # Check if both are dictionaries before attempting to merge
                    if isinstance(result_char["relationships"], dict) and isinstance(char_data["relationships"], dict):
                        result_char["relationships"] = {**result_char["relationships"], **char_data["relationships"]}
                    elif isinstance(char_data["relationships"], dict):
                        # If only char_data has a dict, use it
                        result_char["relationships"] = char_data["relationships"]
                    elif isinstance(result_char["relationships"], dict):
                        # If only result_char has a dict, keep it
                        pass
                    else:
                        # If neither is a dict, convert to dict if possible or create empty dict
                        try:
                            # If it's a list of key-value pairs, convert to dict
                            if isinstance(char_data["relationships"], list) and all(isinstance(item, dict) for item in char_data["relationships"]):
                                result_char["relationships"] = {item.get("character", f"char_{i}"): item.get("relationship", "")
                                                              for i, item in enumerate(char_data["relationships"])}
                            else:
                                # Default to empty dict if conversion not possible
                                result_char["relationships"] = {}
                        except Exception:
                            # Fallback to empty dict
                            result_char["relationships"] = {}
                else:
                    # Ensure relationships is a dict before assigning
                    if isinstance(char_data["relationships"], dict):
                        result_char["relationships"] = char_data["relationships"]
                    elif isinstance(char_data["relationships"], list):
                        # Try to convert list to dict if possible
                        try:
                            if all(isinstance(item, dict) for item in char_data["relationships"]):
                                result_char["relationships"] = {item.get("character", f"char_{i}"): item.get("relationship", "")
                                                              for i, item in enumerate(char_data["relationships"])}
                            else:
                                result_char["relationships"] = {}
                        except Exception:
                            result_char["relationships"] = {}
                    else:
                        result_char["relationships"] = {}
            
            # Update other fields
            for field in ["name", "role", "backstory"]:
                if field in char_data and char_data[field]:
                    result_char[field] = char_data[field]
            
            result[char_id] = result_char
        else:
            # New character, just add it
            result[char_id] = char_data
            
    return result

def merge_scenes(existing: SceneStateDict, new: SceneStateDict) -> SceneStateDict:
    """Merge scene dictionaries, handling nested content properly."""
    result = existing.copy()
    for scene_id, scene_data in new.items():
        if scene_id in result:
            # Update existing scene
            result_scene = result[scene_id].copy()
            
            # Content should replace if provided
            if "content" in scene_data and scene_data["content"]:
                result_scene["content"] = scene_data["content"]
                
            # Structured reflection should always replace if provided
            if "structured_reflection" in scene_data and scene_data["structured_reflection"]:
                result_scene["structured_reflection"] = scene_data["structured_reflection"]
                
            # Reflection notes might need to append or replace depending on context
            if "reflection_notes" in scene_data:
                # If reflection notes indicate scene was revised, we want to completely replace
                if (len(scene_data["reflection_notes"]) == 1 and
                    scene_data["reflection_notes"][0] == "Scene has been revised"):
                    result_scene["reflection_notes"] = scene_data["reflection_notes"]
                # Otherwise append
                elif scene_data["reflection_notes"]:
                    if "reflection_notes" in result_scene:
                        result_scene["reflection_notes"] = result_scene["reflection_notes"] + scene_data["reflection_notes"]
                    else:
                        result_scene["reflection_notes"] = scene_data["reflection_notes"]
                        
            result[scene_id] = result_scene
        else:
            # New scene, just add it
            result[scene_id] = scene_data
            
    return result

def merge_chapters(existing: ChapterStateDict, new: ChapterStateDict) -> ChapterStateDict:
    """Merge chapter dictionaries with special handling for nested scenes."""
    result = existing.copy()
    for chapter_id, chapter_data in new.items():
        if chapter_id in result:
            # Update existing chapter
            result_chapter = result[chapter_id].copy()
            
            # Handle scenes separately with deep merge
            if "scenes" in chapter_data:
                scenes = result_chapter.get("scenes", {})
                result_chapter["scenes"] = merge_scenes(scenes, chapter_data["scenes"])
                
            # Handle reflection notes
            if "reflection_notes" in chapter_data and chapter_data["reflection_notes"]:
                if "reflection_notes" in result_chapter:
                    result_chapter["reflection_notes"] = result_chapter["reflection_notes"] + chapter_data["reflection_notes"]
                else:
                    result_chapter["reflection_notes"] = chapter_data["reflection_notes"]
                    
            # Update other fields
            for field in ["title", "outline"]:
                if field in chapter_data and chapter_data[field]:
                    result_chapter[field] = chapter_data[field]
                    
            result[chapter_id] = result_chapter
        else:
            # New chapter, just add it
            result[chapter_id] = chapter_data
            
    return result

def merge_revelations(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge revelation dictionaries, with special handling for continuity_issues."""
    result = existing.copy()
    
    # If there's no update or no continuity_issues in the update, just use standard merging
    if not new or "continuity_issues" not in new:
        for key, values in new.items():
            if key in result:
                # For normal lists, just append
                if isinstance(values, list) and isinstance(result[key], list):
                    result[key] = result[key] + values
                else:
                    # For other types, replace
                    result[key] = values
            else:
                result[key] = values
        return result
    
    # Special handling for continuity_issues
    old_issues = result.get("continuity_issues", [])
    new_issues = new.get("continuity_issues", [])
    
    # Create a dict to track the best issue for each chapter
    best_issues_by_chapter = {}
    
    # Process all old issues
    for issue in old_issues:
        chapter = issue.get("after_chapter")
        if not chapter:
            continue
            
        # Only add if we don't have this chapter yet, or if this one is resolved and the current one isn't
        if chapter not in best_issues_by_chapter:
            best_issues_by_chapter[chapter] = issue
        elif (issue.get("resolution_status") == "completed" and 
              best_issues_by_chapter[chapter].get("resolution_status") != "completed"):
            # Replace with resolved issue
            best_issues_by_chapter[chapter] = issue
    
    # Process all new issues (these take precedence over old ones)
    for issue in new_issues:
        chapter = issue.get("after_chapter")
        if not chapter:
            continue
            
        # New issues always replace old ones for the same chapter
        # Unless we have a resolved one and this new one isn't resolved
        if chapter not in best_issues_by_chapter:
            best_issues_by_chapter[chapter] = issue
        elif (issue.get("resolution_status") == "completed" or 
              best_issues_by_chapter[chapter].get("resolution_status") != "completed"):
            # Replace if the new issue is resolved OR if the current best isn't resolved
            best_issues_by_chapter[chapter] = issue
    
    # Create the final list of issues, one per chapter
    final_issues = list(best_issues_by_chapter.values())
    
    # Replace the continuity_issues list in the result
    result["continuity_issues"] = final_issues
    
    # Update any other fields from the new revelations update
    for key, value in new.items():
        if key != "continuity_issues":
            result[key] = value
            
    return result
def merge_creative_elements(existing: Dict[str, Dict], new: Dict[str, Dict]) -> Dict[str, Dict]:
    """Merge creative elements dictionaries."""
    result = existing.copy()
    for key, value in new.items():
        result[key] = value  # Simply replace since these are typically not incrementally updated
    return result

def merge_plot_threads(existing: Dict[str, Dict[str, Any]], new: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Merge plot thread dictionaries, preserving thread history and development.
    
    Args:
        existing: The existing plot threads dictionary
        new: The new plot threads dictionary to merge in
        
    Returns:
        The merged plot threads dictionary
    """
    result = existing.copy()
    
    for thread_name, thread_data in new.items():
        if thread_name in result:
            # Update existing thread
            existing_thread = result[thread_name]
            
            # Update status if it's changed
            if thread_data.get("status") != existing_thread.get("status"):
                existing_thread["status"] = thread_data["status"]
            
            # Update last chapter/scene if newer
            if thread_data.get("last_chapter") and thread_data.get("last_scene"):
                existing_thread["last_chapter"] = thread_data["last_chapter"]
                existing_thread["last_scene"] = thread_data["last_scene"]
            
            # Append new development history entries
            if "development_history" in thread_data and thread_data["development_history"]:
                existing_history = existing_thread.get("development_history", [])
                new_history = thread_data["development_history"]
                
                # Only add entries that don't already exist
                existing_entries = {
                    f"{entry.get('chapter')}_{entry.get('scene')}_{entry.get('development')}"
                    for entry in existing_history
                }
                
                for entry in new_history:
                    entry_key = f"{entry.get('chapter')}_{entry.get('scene')}_{entry.get('development')}"
                    if entry_key not in existing_entries:
                        existing_history.append(entry)
                
                existing_thread["development_history"] = existing_history
            
            # Update the thread in the result
            result[thread_name] = existing_thread
        else:
            # New thread, just add it
            result[thread_name] = thread_data
    
    return result

def merge_world_elements(existing: WorldElementsDict, new: WorldElementsDict) -> WorldElementsDict:
    """
    Merge worldbuilding elements dictionaries with intelligent handling of nested structures.
    
    This function allows for updating specific categories of world elements while preserving
    others, and handles both replacement and appending of elements depending on their type.
    
    Args:
        existing: The existing world elements dictionary
        new: The new world elements dictionary to merge in
        
    Returns:
        The merged world elements dictionary
    """
    result = existing.copy()
    
    for category, elements in new.items():
        if category in result:
            # If category exists, update it intelligently
            result_category = result[category].copy()
            
            for key, value in elements.items():
                if key in result_category:
                    # Handle lists by appending
                    if isinstance(value, list) and isinstance(result_category[key], list):
                        # For lists, append new items to avoid duplicates
                        existing_items = set(str(item) for item in result_category[key])
                        for item in value:
                            if str(item) not in existing_items:
                                result_category[key].append(item)
                    # Handle nested dictionaries recursively
                    elif isinstance(value, dict) and isinstance(result_category[key], dict):
                        result_category[key] = {**result_category[key], **value}
                    else:
                        # For other types, replace if the new value is not empty
                        if value:
                            result_category[key] = value
                else:
                    # If key doesn't exist in the category, add it
                    result_category[key] = value
            
            result[category] = result_category
        else:
            # If category doesn't exist, add it
            result[category] = elements
    
    return result

class CharacterProfile(TypedDict):
    """Character profile data structure."""
    name: str
    role: str
    backstory: str
    evolution: List[str]
    known_facts: List[str]
    secret_facts: List[str]
    revealed_facts: List[str]
    relationships: Dict[str, str]

class SceneState(TypedDict):
    """Scene state data structure."""
    content: str
    reflection_notes: List[str]

class ChapterState(TypedDict):
    """Chapter state data structure."""
    title: str
    outline: str
    scenes: Dict[str, SceneState]
    reflection_notes: List[str]

class StoryState(TypedDict):
    """Main state schema for the story generation graph, with reducer annotations."""
    # Use built-in add_messages for chat messages
    messages: Annotated[List[Union[HumanMessage, AIMessage]], add_messages]
    
    # Simple fields where standard replacement is fine
    genre: str
    tone: str
    author: str  # Author whose style to emulate
    author_style_guidance: str  # Specific notes on author's style
    language: str  # Target language for story generation
    initial_idea: str  # Initial story idea provided by the user
    initial_idea_elements: Dict[str, Any]  # Structured elements extracted from the initial idea
    global_story: str  # Overall storyline and hero's journey phases
    
    # Complex fields that need custom reducers
    chapters: Annotated[Dict[str, ChapterState], merge_chapters]  # Custom reducer for nested chapters
    characters: Annotated[Dict[str, CharacterProfile], merge_characters]  # Custom reducer for characters
    revelations: Annotated[Dict[str, Any], merge_revelations]  # Custom reducer for revelations with continuity_issues
    creative_elements: Annotated[Dict[str, Dict], merge_creative_elements]  # Custom reducer for creative elements
    world_elements: Annotated[Dict[str, Dict], merge_world_elements]  # Custom reducer for worldbuilding elements
    plot_threads: Annotated[Dict[str, Dict[str, Any]], merge_plot_threads]  # Custom reducer for plot threads
    
    # Tracking fields
    current_chapter: str  # Track which chapter is being written
    current_scene: str  # Track which scene is being written
    completed: bool  # Flag to indicate if the story is complete
    last_node: str  # Track which node was last executed for routing