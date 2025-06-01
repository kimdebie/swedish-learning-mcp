import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from notion_client import Client as NotionClient
from dotenv import load_dotenv
from mcp_server import mcp

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GRAMMAR_DATABASE_ID = os.getenv("GRAMMAR_DATABASE_ID")
VOCAB_DATABASE_ID = os.getenv("VOCAB_DATABASE_ID")

notion_client = NotionClient(auth=NOTION_TOKEN) if NOTION_TOKEN else None

def _extract_rich_text(rich_text: list) -> str:
    """Extract plain text from Notion's rich text objects."""
    return "".join(text_obj.get("plain_text", "") for text_obj in rich_text)

def _get_notion_property(page: dict, prop_name: str, prop_type: str = "rich_text") -> Any:
    """Extract property value from Notion page."""
    try:
        prop = page.get("properties", {}).get(prop_name, {})
        
        if prop_type == "rich_text":
            return _extract_rich_text(prop.get("rich_text", []))
        elif prop_type == "title":
            return _extract_rich_text(prop.get("title", []))
        elif prop_type == "select":
            select_obj = prop.get("select")
            return select_obj.get("name") if select_obj else None
        elif prop_type == "date":
            date_obj = prop.get("date")
            return date_obj.get("start") if date_obj else None
        else:
            return prop.get(prop_type)
    except Exception:
        return None

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

@mcp.tool()
async def get_study_session_data(vocab_count: int = 10, grammar_count: int = 5) -> str:
    """Prepare a mixed study session with vocabulary and grammar."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        # Get vocabulary for review
        vocab_response = notion_client.databases.query(database_id=VOCAB_DATABASE_ID)
        vocab_items = []
        
        for page in vocab_response["results"]:
            word = _get_notion_property(page, "Word/Phrase", "title")
            translation = _get_notion_property(page, "English Translation")
            mastery_level = _get_notion_property(page, "Mastery Level", "select")
            last_reviewed = _get_notion_property(page, "Last Reviewed", "date")
            
            # Simple check for words due for review (no last_reviewed or mastery not "Mastered")
            if not last_reviewed or mastery_level != "Mastered":
                vocab_items.append({
                    "id": page["id"],
                    "word": word,
                    "translation": translation
                })
        
        # Limit vocab items
        vocab_items = vocab_items[:vocab_count]
        
        # Get grammar concepts for review (focusing on "Learning" status)
        grammar_response = notion_client.databases.query(
            database_id=GRAMMAR_DATABASE_ID,
            filter={
                "property": "Mastery Status",
                "select": {"equals": "Learning"}
            }
        )
        
        grammar_items = []
        for page in grammar_response["results"]:
            concept_name = _get_notion_property(page, "Concept Name", "title")
            category = _get_notion_property(page, "Category", "select")
            
            grammar_items.append({
                "id": page["id"],
                "concept_name": concept_name,
                "category": category
            })
        
        # Limit grammar items
        grammar_items = grammar_items[:grammar_count]
        
        response_text = "**Study Session Prepared**\n\n"
        
        if vocab_items:
            response_text += f"**Vocabulary ({len(vocab_items)} words):**\n"
            for item in vocab_items:
                response_text += f"- {item['word']} - {item['translation']}\n"
            response_text += "\n"
        
        if grammar_items:
            response_text += f"**Grammar ({len(grammar_items)} concepts):**\n"
            for item in grammar_items:
                response_text += f"- {item['concept_name']} ({item['category']})\n"
            response_text += "\n"
        
        total_items = len(vocab_items) + len(grammar_items)
        response_text += f"Total items for review: {total_items}"
        
        return response_text
    except Exception as e:
        return f"Error preparing study session: {str(e)}"

@mcp.tool()
async def update_study_progress(results: List[Dict[str, Any]]) -> str:
    """Update progress after completing a study session."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        vocab_updates = []
        grammar_updates = []
        
        for result in results:
            result_type = result.get('type')
            result_id = result.get('id')
            
            if result_type == 'vocabulary':
                # Update vocabulary mastery
                correct = result.get('correct', 0)
                total = result.get('total', 1)
                
                # Get current word data
                page = notion_client.pages.retrieve(result_id)
                word = _get_notion_property(page, "Word/Phrase", "title")
                current_review_count = _get_notion_property(page, "Review Count", "number") or 0
                current_success_rate = _get_notion_property(page, "Success Rate", "number") or 0
                
                # Calculate new success rate
                session_success_rate = (correct / total) * 100 if total > 0 else 0
                new_review_count = current_review_count + 1
                
                # Weighted average of success rates
                if current_review_count > 0:
                    new_success_rate = ((current_success_rate * current_review_count) + session_success_rate) / new_review_count
                else:
                    new_success_rate = session_success_rate
                
                # Determine new mastery level
                if new_success_rate >= 90 and new_review_count >= 5:
                    new_mastery_level = "Mastered"
                elif new_success_rate >= 75 and new_review_count >= 3:
                    new_mastery_level = "Familiar"
                elif new_review_count >= 1:
                    new_mastery_level = "Learning"
                else:
                    new_mastery_level = "New"
                
                # Update the page
                notion_client.pages.update(
                    page_id=result_id,
                    properties={
                        "Mastery Level": {"select": {"name": new_mastery_level}},
                        "Review Count": {"number": new_review_count},
                        "Success Rate": {"number": round(new_success_rate, 1)},
                        "Last Reviewed": {"date": {"start": datetime.now().isoformat()}}
                    }
                )
                
                vocab_updates.append({
                    "word": word,
                    "new_mastery_level": new_mastery_level,
                    "new_success_rate": round(new_success_rate, 1)
                })
                
            elif result_type == 'grammar':
                # Update grammar mastery
                new_mastery = result.get('new_mastery', 'Learning')
                notes = result.get('notes')
                
                # Get current concept data
                page = notion_client.pages.retrieve(result_id)
                concept_name = _get_notion_property(page, "Concept Name", "title")
                
                update_properties = {
                    "Mastery Status": {"select": {"name": new_mastery}}
                }
                
                if notes:
                    update_properties["Practice Notes"] = {"rich_text": [{"text": {"content": notes}}]}
                
                notion_client.pages.update(
                    page_id=result_id,
                    properties=update_properties
                )
                
                grammar_updates.append({
                    "concept_name": concept_name,
                    "new_mastery_status": new_mastery
                })
        
        response_text = "**Study Session Progress Updated**\n\n"
        
        if vocab_updates:
            response_text += f"**Vocabulary ({len(vocab_updates)} words updated):**\n"
            for update in vocab_updates:
                response_text += f"- {update['word']}: {update['new_mastery_level']} "
                response_text += f"({update['new_success_rate']}%)\n"
            response_text += "\n"
        
        if grammar_updates:
            response_text += f"**Grammar ({len(grammar_updates)} concepts updated):**\n"
            for update in grammar_updates:
                response_text += f"- {update['concept_name']}: {update['new_mastery_status']}\n"
        
        return response_text
    except Exception as e:
        return f"Error updating study progress: {str(e)}"
