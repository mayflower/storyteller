"""
StoryCraft Agent - Initialization nodes.
"""

from typing import Dict

from storyteller_lib.config import llm, manage_memory_tool, MEMORY_NAMESPACE, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from storyteller_lib.models import StoryState
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.modifier import RemoveMessage
from storyteller_lib import track_progress

@track_progress
def initialize_state(state: StoryState) -> Dict:
    """Initialize the story state with user input."""
    messages = state["messages"]
    
    # Use the genre, tone, author, language, and initial idea values already passed in the state
    # If not provided, use defaults
    genre = state.get("genre") or "fantasy"
    tone = state.get("tone") or "epic"
    author = state.get("author") or ""
    initial_idea = state.get("initial_idea") or ""
    author_style_guidance = state.get("author_style_guidance", "")
    language = state.get("language") or DEFAULT_LANGUAGE
    
    # Validate language and default to English if not supported
    if language.lower() not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    # If author guidance wasn't provided in the initial state, but we have an author, get it now
    if author and not author_style_guidance:
        # See if we have cached guidance
        try:
            author_style_object = manage_memory_tool.invoke({
                "action": "get",
                "key": f"author_style_{author.lower().replace(' ', '_')}",
                "namespace": MEMORY_NAMESPACE
            })
            
            if author_style_object and "value" in author_style_object:
                author_style_guidance = author_style_object["value"]
        except Exception:
            # If error, we'll generate it later
            pass
    
    # Prepare response message
    author_mention = f" in the style of {author}" if author else ""
    idea_mention = f" based on your idea: '{initial_idea}'" if initial_idea else ""
    language_mention = f" in {SUPPORTED_LANGUAGES[language.lower()]}" if language.lower() != DEFAULT_LANGUAGE else ""
    response_message = f"I'll create a {tone} {genre} story{author_mention}{language_mention}{idea_mention} for you. Let me start planning the narrative..."
    
    # Get existing message IDs to delete
    message_ids = [msg.id for msg in state.get("messages", [])]
    
    # Initialize the state
    return {
        "genre": genre,
        "tone": tone,
        "author": author,
        "initial_idea": initial_idea,
        "author_style_guidance": author_style_guidance,
        "language": language,
        "global_story": "",
        "chapters": {},
        "characters": {},
        "revelations": {"reader": [], "characters": []},
        "current_chapter": "",
        "current_scene": "",
        "completed": False,
        "messages": [
            *[RemoveMessage(id=msg_id) for msg_id in message_ids],
            AIMessage(content=response_message)
        ]
    }

@track_progress
def brainstorm_story_concepts(state: StoryState) -> Dict:
    """Brainstorm creative story concepts before generating the outline."""
    from storyteller_lib.creative_tools import creative_brainstorm
    
    genre = state["genre"]
    tone = state["tone"]
    author = state["author"]
    initial_idea = state.get("initial_idea", "")
    author_style_guidance = state["author_style_guidance"]
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Generate initial context based on genre, tone, language, and initial idea
    idea_context = f"\nThe story should be based on this initial idea: '{initial_idea}'" if initial_idea else ""
    language_context = ""
    if language.lower() != DEFAULT_LANGUAGE:
        language_context = f"\nThe story should be written in {SUPPORTED_LANGUAGES[language.lower()]} with character names, places, and cultural references appropriate for {SUPPORTED_LANGUAGES[language.lower()]}-speaking audiences."
    
    context = f"""
    We're creating a {tone} {genre} story that follows the hero's journey structure.
    The story should be engaging, surprising, and emotionally resonant with readers.{idea_context}{language_context}
    """
    
    # Brainstorm different high-level story concepts
    brainstorm_results = creative_brainstorm(
        topic="Story Concept",
        genre=genre,
        tone=tone,
        context=context,
        author=author,
        author_style_guidance=author_style_guidance,
        language=language,
        num_ideas=5
    )
    
    # Brainstorm unique world-building elements
    world_building_results = creative_brainstorm(
        topic="World Building Elements",
        genre=genre,
        tone=tone,
        context=context,
        author=author,
        author_style_guidance=author_style_guidance,
        language=language,
        num_ideas=4
    )
    
    # Brainstorm central conflicts
    conflict_results = creative_brainstorm(
        topic="Central Conflict",
        genre=genre,
        tone=tone,
        context=context,
        author=author,
        author_style_guidance=author_style_guidance,
        language=language,
        num_ideas=3
    )
    
    # Store all creative elements
    creative_elements = {
        "story_concepts": brainstorm_results,
        "world_building": world_building_results,
        "central_conflicts": conflict_results
    }
    
    # Create messages to add and remove
    idea_mention = f" based on your idea" if initial_idea else ""
    new_msg = AIMessage(content=f"I've brainstormed several creative concepts for your {tone} {genre} story{idea_mention}. Now I'll develop a cohesive outline based on the most promising ideas.")
    
    # Get existing message IDs to delete
    message_ids = [msg.id for msg in state.get("messages", [])]
    
    # Update state with brainstormed ideas
    return {
        "creative_elements": creative_elements,
        "messages": [
            *[RemoveMessage(id=msg_id) for msg_id in message_ids],
            new_msg
        ]
    }