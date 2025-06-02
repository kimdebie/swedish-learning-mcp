from datetime import datetime
from mcp_server import mcp
from utils import (
    notion_client,
    GRAMMAR_DATABASE_ID,
    _get_notion_property
)

@mcp.tool()
async def add_grammar_concept(
    concept_name: str,
    category: str,
    difficulty_level: str,
    description: str,
    examples: str,
    practice_notes: str = None
) -> str:
    """Add a new grammar concept to the database."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        properties = {
            "Concept Name": {"title": [{"text": {"content": concept_name}}]},
            "Category": {"select": {"name": category}},
            "Difficulty Level": {"select": {"name": difficulty_level}},
            "Description": {"rich_text": [{"text": {"content": description}}]},
            "Examples": {"rich_text": [{"text": {"content": examples}}]},
            "Date Added": {"date": {"start": datetime.now().isoformat()}},
            "Mastery Status": {"select": {"name": "Learning"}},
        }
        
        if practice_notes:
            properties["Practice Notes"] = {"rich_text": [{"text": {"content": practice_notes}}]}
        
        result = notion_client.pages.create(
            parent={"database_id": GRAMMAR_DATABASE_ID},
            properties=properties
        )
        
        return f"Successfully added grammar concept '{concept_name}'. ID: {result['id']}"
    except Exception as e:
        return f"Error adding grammar concept: {str(e)}"

@mcp.tool()
async def get_grammar_concepts(
    category: str = None,
    difficulty: str = None,
    mastery_status: str = None
) -> str:
    """Get grammar concepts with optional filtering."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        # Build filter if needed
        filter_conditions = []
        
        if category:
            filter_conditions.append({
                "property": "Category",
                "select": {"equals": category}
            })
        
        if difficulty:
            filter_conditions.append({
                "property": "Difficulty Level", 
                "select": {"equals": difficulty}
            })
        
        if mastery_status:
            filter_conditions.append({
                "property": "Mastery Status",
                "select": {"equals": mastery_status}
            })
        
        query_params = {"database_id": GRAMMAR_DATABASE_ID}
        
        if filter_conditions:
            if len(filter_conditions) == 1:
                query_params["filter"] = filter_conditions[0]
            else:
                query_params["filter"] = {
                    "and": filter_conditions
                }
        
        response = notion_client.databases.query(**query_params)
        
        concepts = []
        for page in response["results"]:
            concept_name = _get_notion_property(page, "Concept Name", "title")
            category_val = _get_notion_property(page, "Category", "select")
            difficulty_val = _get_notion_property(page, "Difficulty Level", "select")
            mastery_val = _get_notion_property(page, "Mastery Status", "select")
            
            concepts.append({
                "id": page["id"],
                "concept_name": concept_name,
                "category": category_val,
                "difficulty_level": difficulty_val,
                "mastery_status": mastery_val
            })
        
        if not concepts:
            return "No grammar concepts found matching the criteria."
        
        response_text = f"Found {len(concepts)} grammar concepts:\n\n"
        
        # Group by category
        by_category = {}
        for concept in concepts:
            cat = concept.get('category', 'Uncategorized')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(concept)
        
        for category_name, items in by_category.items():
            response_text += f"**{category_name}:**\n"
            for concept in items:
                response_text += f"- {concept['concept_name']} "
                response_text += f"({concept['difficulty_level']}, {concept['mastery_status']})\n"
            response_text += "\n"
        
        return response_text
    except Exception as e:
        return f"Error getting grammar concepts: {str(e)}"

@mcp.tool()
async def update_grammar_mastery(
    concept_id: str,
    mastery_status: str,
    practice_notes: str = None
) -> str:
    """Update mastery status and notes for a grammar concept."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        # Get current concept data
        page = notion_client.pages.retrieve(concept_id)
        concept_name = _get_notion_property(page, "Concept Name", "title")
        
        update_properties = {
            "Mastery Status": {"select": {"name": mastery_status}}
        }
        
        notes_updated = False
        if practice_notes:
            update_properties["Practice Notes"] = {"rich_text": [{"text": {"content": practice_notes}}]}
            notes_updated = True
        
        notion_client.pages.update(
            page_id=concept_id,
            properties=update_properties
        )
        
        response = f"Updated grammar concept '{concept_name}':\n"
        response += f"- New mastery status: {mastery_status}\n"
        if notes_updated:
            response += "- Practice notes updated\n"
        
        return response
    except Exception as e:
        return f"Error updating grammar mastery: {str(e)}"

@mcp.tool()
async def search_grammar(query: str) -> str:
    """Search grammar concepts by name, category, or content."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        response = notion_client.databases.query(database_id=GRAMMAR_DATABASE_ID)
        
        results = []
        query_lower = query.lower()
        
        for page in response["results"]:
            concept_name = _get_notion_property(page, "Concept Name", "title") or ""
            category = _get_notion_property(page, "Category", "select") or ""
            description = _get_notion_property(page, "Description") or ""
            examples = _get_notion_property(page, "Examples") or ""
            difficulty_level = _get_notion_property(page, "Difficulty Level", "select")
            mastery_status = _get_notion_property(page, "Mastery Status", "select")
            
            # Search in concept name, category, description, and examples
            if (query_lower in concept_name.lower() or 
                query_lower in category.lower() or 
                query_lower in description.lower() or
                query_lower in examples.lower()):
                results.append({
                    "concept_name": concept_name,
                    "category": category,
                    "description": description,
                    "difficulty_level": difficulty_level,
                    "mastery_status": mastery_status
                })
        
        if not results:
            return f"No grammar concepts found matching '{query}'"
        
        response_text = f"Found {len(results)} grammar concepts:\n\n"
        for concept in results:
            response_text += f"**{concept['concept_name']}**\n"
            response_text += f"- Category: {concept['category']}\n"
            response_text += f"- Difficulty: {concept['difficulty_level']}\n"
            response_text += f"- Mastery: {concept['mastery_status']}\n"
            description_preview = concept['description'][:100] + "..." if len(concept['description']) > 100 else concept['description']
            response_text += f"- Description: {description_preview}\n\n"
        
        return response_text
    except Exception as e:
        return f"Error searching grammar: {str(e)}"
