import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from notion_client import Client as NotionClient
from dotenv import load_dotenv
from mcp_server import mcp

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
VOCAB_DATABASE_ID = os.getenv("VOCAB_DATABASE_ID")
GRAMMAR_DATABASE_ID = os.getenv("GRAMMAR_DATABASE_ID")

# Cache for storing data
CACHE: Dict[str, Any] = {}

if not NOTION_TOKEN or not VOCAB_DATABASE_ID or not GRAMMAR_DATABASE_ID:
    print("Error: NOTION_TOKEN, VOCAB_DATABASE_ID, and GRAMMAR_DATABASE_ID environment variables must be set")

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
        elif prop_type == "number":
            return prop.get("number", 0)
        elif prop_type == "date":
            date_obj = prop.get("date")
            return date_obj.get("start") if date_obj else None
        else:
            return prop.get(prop_type)
    except Exception:
        return None

def _calculate_days_overdue(last_reviewed: str, mastery_level: str) -> int:
    """Calculate how many days a word is overdue for review."""
    if not last_reviewed:
        return 999  # Never reviewed
    
    try:
        last_date = datetime.fromisoformat(last_reviewed.replace('Z', '+00:00'))
        now = datetime.now()
        days_since = (now - last_date).days
        
        # Spaced repetition intervals based on mastery
        intervals = {
            "New": 1,
            "Learning": 3,
            "Familiar": 7,
            "Mastered": 30
        }
        
        interval = intervals.get(mastery_level, 1)
        return max(0, days_since - interval)
    except Exception:
        return 0

@mcp.tool()
async def add_vocabulary_word(
    word: str, 
    translation: str, 
    part_of_speech: str = "Noun",
    definition: str = None,
    example_sentence: str = None,
    example_translation: str = None,
    difficulty: str = "Medium",
    source_text: str = None
) -> str:
    """Add a new word to the vocabulary database."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        properties = {
            "Word/Phrase": {"title": [{"text": {"content": word}}]},
            "English Translation": {"rich_text": [{"text": {"content": translation}}]},
            "Part of Speech": {"select": {"name": part_of_speech}},
            "Difficulty": {"select": {"name": difficulty}},
            "Date Added": {"date": {"start": datetime.now().isoformat()}},
            "Mastery Level": {"select": {"name": "New"}},
            "Review Count": {"number": 0},
            "Success Rate": {"number": 0},
        }
        
        if definition:
            properties["Definition"] = {"rich_text": [{"text": {"content": definition}}]}
        if example_sentence:
            properties["Example Sentence"] = {"rich_text": [{"text": {"content": example_sentence}}]}
        if example_translation:
            properties["Example Translation"] = {"rich_text": [{"text": {"content": example_translation}}]}
        if source_text:
            properties["Source Text"] = {"rich_text": [{"text": {"content": source_text}}]}
        
        result = notion_client.pages.create(
            parent={"database_id": VOCAB_DATABASE_ID},
            properties=properties
        )
        
        return f"Successfully added '{word}' to vocabulary database. ID: {result['id']}"
    except Exception as e:
        return f"Error adding vocabulary word: {str(e)}"

@mcp.tool()
async def get_vocabulary_for_review(limit: int = 20) -> str:
    """Get vocabulary words due for review based on spaced repetition."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        # Get all vocabulary entries
        response = notion_client.databases.query(database_id=VOCAB_DATABASE_ID)
        
        words_for_review = []
        for page in response["results"]:
            word = _get_notion_property(page, "Word/Phrase", "title")
            translation = _get_notion_property(page, "English Translation")
            mastery_level = _get_notion_property(page, "Mastery Level", "select")
            difficulty = _get_notion_property(page, "Difficulty", "select")
            last_reviewed = _get_notion_property(page, "Last Reviewed", "date")
            example_sentence = _get_notion_property(page, "Example Sentence")
            
            days_overdue = _calculate_days_overdue(last_reviewed, mastery_level or "New")
            
            if days_overdue > 0:  # Due for review
                words_for_review.append({
                    "id": page["id"],
                    "word": word,
                    "translation": translation,
                    "mastery_level": mastery_level,
                    "difficulty": difficulty,
                    "days_overdue": days_overdue,
                    "example_sentence": example_sentence
                })
        
        # Sort by days overdue (most overdue first)
        words_for_review.sort(key=lambda x: x["days_overdue"], reverse=True)
        words_for_review = words_for_review[:limit]
        
        if not words_for_review:
            return "No vocabulary words are currently due for review."
        
        response_text = f"Found {len(words_for_review)} words due for review:\n\n"
        for word_data in words_for_review:
            response_text += f"- **{word_data['word']}** ({word_data['translation']})\n"
            response_text += f"  - Mastery: {word_data['mastery_level']}, "
            response_text += f"Difficulty: {word_data['difficulty']}, "
            response_text += f"Days overdue: {word_data['days_overdue']}\n"
            if word_data.get('example_sentence'):
                response_text += f"  - Example: {word_data['example_sentence']}\n"
            response_text += "\n"
        
        return response_text
    except Exception as e:
        return f"Error getting vocabulary for review: {str(e)}"

@mcp.tool()
async def update_word_mastery(word_id: str, correct_answers: int, total_answers: int) -> str:
    """Update mastery level and statistics after studying a word."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        # Get current word data
        page = notion_client.pages.retrieve(word_id)
        word = _get_notion_property(page, "Word/Phrase", "title")
        current_review_count = _get_notion_property(page, "Review Count", "number") or 0
        current_success_rate = _get_notion_property(page, "Success Rate", "number") or 0
        
        # Calculate new success rate
        session_success_rate = (correct_answers / total_answers) * 100 if total_answers > 0 else 0
        new_review_count = current_review_count + 1
        
        # Weighted average of success rates
        if current_review_count > 0:
            new_success_rate = ((current_success_rate * current_review_count) + session_success_rate) / new_review_count
        else:
            new_success_rate = session_success_rate
        
        # Determine new mastery level based on success rate and review count
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
            page_id=word_id,
            properties={
                "Mastery Level": {"select": {"name": new_mastery_level}},
                "Review Count": {"number": new_review_count},
                "Success Rate": {"number": round(new_success_rate, 1)},
                "Last Reviewed": {"date": {"start": datetime.now().isoformat()}}
            }
        )
        
        response = f"Updated mastery for '{word}':\n"
        response += f"- New mastery level: {new_mastery_level}\n"
        response += f"- Overall success rate: {round(new_success_rate, 1)}%\n"
        response += f"- Session success rate: {round(session_success_rate, 1)}%\n"
        response += f"- Total reviews: {new_review_count}"
        
        return response
    except Exception as e:
        return f"Error updating word mastery: {str(e)}"

@mcp.tool()
async def search_vocabulary(query: str) -> str:
    """Search vocabulary by word, translation, or content."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        response = notion_client.databases.query(database_id=VOCAB_DATABASE_ID)
        
        results = []
        query_lower = query.lower()
        
        for page in response["results"]:
            word = _get_notion_property(page, "Word/Phrase", "title") or ""
            translation = _get_notion_property(page, "English Translation") or ""
            definition = _get_notion_property(page, "Definition") or ""
            mastery_level = _get_notion_property(page, "Mastery Level", "select")
            success_rate = _get_notion_property(page, "Success Rate", "number") or 0
            
            # Search in word, translation, and definition
            if (query_lower in word.lower() or 
                query_lower in translation.lower() or 
                query_lower in definition.lower()):
                results.append({
                    "word": word,
                    "translation": translation,
                    "definition": definition,
                    "mastery_level": mastery_level,
                    "success_rate": success_rate
                })
        
        if not results:
            return f"No vocabulary entries found matching '{query}'"
        
        response_text = f"Found {len(results)} vocabulary entries:\n\n"
        for entry in results:
            response_text += f"- **{entry['word']}** - {entry['translation']}\n"
            if entry.get('definition'):
                response_text += f"  - Definition: {entry['definition']}\n"
            response_text += f"  - Mastery: {entry['mastery_level']}, "
            response_text += f"Success rate: {entry['success_rate']}%\n\n"
        
        return response_text
    except Exception as e:
        return f"Error searching vocabulary: {str(e)}"

@mcp.tool()
async def extract_vocabulary_from_text(text: str, add_to_database: bool = False) -> str:
    """Analyze Swedish text and identify potentially challenging words."""
    # Simple heuristic: words longer than 6 characters or containing specific Swedish characters
    import re
    
    # Common Swedish words to exclude from extraction
    common_words = {
        "att", "och", "det", "är", "som", "för", "på", "med", "av", "till", "från", "har", "den", "de", "om", "var", "eller", "när", "efter", "över", "andra", "mycket", "bara", "skulle", "första", "utan", "mellan", "under", "ser", "honom", "kommer", "man", "också", "nu", "kan", "göra", "får", "ska", "här", "något", "alla", "igen", "mer", "varje", "sedan", "våra", "vara", "samt", "vid", "sådan", "dock", "men", "så", "både", "denna", "dessa", "vilka", "vilket"
    }
    
    # Find words (excluding punctuation)
    words = re.findall(r'\b[a-zA-ZåäöÅÄÖ]+\b', text.lower())
    
    challenging_words = []
    for word in set(words):  # Remove duplicates
        if (len(word) > 6 or  # Long words
            any(char in word for char in 'åäöÅÄÖ') or  # Contains Swedish characters
            word.endswith(('tion', 'ning', 'het', 'dom', 'skap', 'else'))  # Common Swedish suffixes
           ) and word not in common_words:
            challenging_words.append(word)
    
    if not challenging_words:
        return "No challenging words identified in the text."
    
    results = []
    already_in_db = []
    
    if add_to_database and notion_client:
        # Check which words are already in database
        try:
            db_response = notion_client.databases.query(database_id=VOCAB_DATABASE_ID)
            existing_words = {_get_notion_property(page, "Word/Phrase", "title").lower() 
                            for page in db_response["results"]}
            
            for word in challenging_words:
                if word in existing_words:
                    already_in_db.append(word)
                else:
                    # Add to database with placeholder translation
                    await add_vocabulary_word(
                        word=word,
                        translation="[Translation needed]",
                        source_text=text[:100] + "..." if len(text) > 100 else text
                    )
                    results.append(word)
        except Exception as e:
            return f"Error processing words: {str(e)}"
    else:
        results = challenging_words
    
    response = f"Identified {len(challenging_words)} potentially challenging words:\n\n"
    
    if results and not add_to_database:
        response += f"**Words identified:** {', '.join(results)}\n\n"
    if already_in_db:
        response += f"**Already in database:** {', '.join(already_in_db)}\n\n"
    if results and add_to_database:
        response += f"**Added to database:** {', '.join(results)}\n"
    
    return response

@mcp.tool()
async def get_word_details(word_id: str) -> str:
    """Get full details for a specific vocabulary entry."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    try:
        page = notion_client.pages.retrieve(word_id)
        
        word = _get_notion_property(page, "Word/Phrase", "title")
        translation = _get_notion_property(page, "English Translation")
        part_of_speech = _get_notion_property(page, "Part of Speech", "select")
        definition = _get_notion_property(page, "Definition")
        difficulty = _get_notion_property(page, "Difficulty", "select")
        mastery_level = _get_notion_property(page, "Mastery Level", "select")
        example_sentence = _get_notion_property(page, "Example Sentence")
        example_translation = _get_notion_property(page, "Example Translation")
        review_count = _get_notion_property(page, "Review Count", "number")
        success_rate = _get_notion_property(page, "Success Rate", "number")
        last_reviewed = _get_notion_property(page, "Last Reviewed", "date")
        source_text = _get_notion_property(page, "Source Text")
        
        response = f"**{word}**\n\n"
        response += f"- **Translation:** {translation}\n"
        response += f"- **Part of Speech:** {part_of_speech}\n"
        
        if definition:
            response += f"- **Definition:** {definition}\n"
        
        response += f"- **Difficulty:** {difficulty}\n"
        response += f"- **Mastery Level:** {mastery_level}\n"
        
        if example_sentence:
            response += f"\n**Example:**\n"
            response += f"- Swedish: {example_sentence}\n"
            if example_translation:
                response += f"- English: {example_translation}\n"
        
        response += f"\n**Statistics:**\n"
        response += f"- Review Count: {review_count or 0}\n"
        response += f"- Success Rate: {success_rate or 0}%\n"
        
        if last_reviewed:
            response += f"- Last Reviewed: {last_reviewed}\n"
        
        if source_text:
            response += f"\n**Source:** {source_text}\n"
        
        return response
    except Exception as e:
        return f"Error getting word details: {str(e)}"

@mcp.tool()
async def mark_words_for_review(word_ids: List[str]) -> str:
    """Mark multiple words for immediate review by resetting their last reviewed date."""
    if not notion_client:
        return "Error: Notion client not initialized"
    
    updated = []
    failed = []
    
    for word_id in word_ids:
        try:
            page = notion_client.pages.retrieve(word_id)
            word = _get_notion_property(page, "Word/Phrase", "title")
            
            # Reset last reviewed to force review
            notion_client.pages.update(
                page_id=word_id,
                properties={
                    "Last Reviewed": {"date": None}
                }
            )
            
            updated.append(word)
        except Exception as e:
            failed.append({"id": word_id, "error": str(e)})
    
    response = f"Marked {len(updated)} words for review.\n"
    
    if updated:
        response += "\n**Successfully updated:**\n"
        for word in updated:
            response += f"- {word}\n"
    
    if failed:
        response += "\n**Failed to update:**\n"
        for failure in failed:
            response += f"- ID: {failure['id']} - {failure['error']}\n"
    
    return response
