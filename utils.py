import os
from datetime import datetime
from typing import Any
from notion_client import Client as NotionClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
VOCAB_DATABASE_ID = os.getenv("VOCAB_DATABASE_ID")
GRAMMAR_DATABASE_ID = os.getenv("GRAMMAR_DATABASE_ID")

# Initialize Notion client
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

def calculate_days_overdue(last_reviewed: str, mastery_level: str) -> int:
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

def calculate_new_mastery_level(success_rate: float, review_count: int) -> str:
    """Determine new mastery level based on success rate and review count."""
    if success_rate >= 90 and review_count >= 5:
        return "Mastered"
    elif success_rate >= 75 and review_count >= 3:
        return "Familiar"
    elif review_count >= 1:
        return "Learning"
    else:
        return "New"

def calculate_weighted_success_rate(current_rate: float, current_count: int, session_rate: float) -> float:
    """Calculate weighted average of success rates."""
    if current_count > 0:
        return ((current_rate * current_count) + session_rate) / (current_count + 1)
    else:
        return session_rate 