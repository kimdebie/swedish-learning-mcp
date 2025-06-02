from datetime import datetime
from typing import List, Dict, Any
from mcp_server import mcp
from utils import (
    notion_client,
    GRAMMAR_DATABASE_ID,
    VOCAB_DATABASE_ID,
    _get_notion_property,
    calculate_new_mastery_level,
    calculate_weighted_success_rate
)

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
                new_success_rate = calculate_weighted_success_rate(current_success_rate, current_review_count, session_success_rate)
                
                # Determine new mastery level
                new_mastery_level = calculate_new_mastery_level(new_success_rate, new_review_count)
                
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
