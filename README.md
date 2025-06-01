# Swedish Learning MCP

A Model Control Protocol (MCP) server for Swedish language learning with Notion integration.

## Features

### Vocabulary Management
- Add new Swedish words and phrases to your Notion database
- Get words due for review based on spaced repetition
- Update mastery levels and track success rates
- Search vocabulary by word, translation, or content
- Extract challenging words from Swedish text
- Get detailed information about specific words
- Mark words for immediate review

### Grammar Management  
- Add new grammar concepts with descriptions and examples
- Filter concepts by category, difficulty, or mastery status
- Update mastery status and add practice notes
- Search grammar concepts by name or content

### Study Sessions
- Generate mixed study sessions with vocabulary and grammar
- Update progress after completing study sessions
- Track learning statistics and mastery progression

## Installation

1. Clone this repository
2. Install dependencies: `pip install -e .`
3. Set up your environment variables (see setup guide)
4. Configure your Notion databases

## Environment Variables

Create a `.env` file with:

```
NOTION_TOKEN=your_notion_integration_token
VOCAB_DATABASE_ID=your_vocabulary_database_id  
GRAMMAR_DATABASE_ID=your_grammar_database_id
```

## Usage

Run the MCP server:

```bash
python main.py
```

Then connect it to Claude through MCP configuration.

## Available Tools

### Vocabulary Tools
- `add_vocabulary_word` - Add new vocabulary entries
- `get_vocabulary_for_review` - Get words due for review
- `update_word_mastery` - Update progress after studying
- `search_vocabulary` - Search existing vocabulary
- `extract_vocabulary_from_text` - Find challenging words in text
- `get_word_details` - Get full details for a word
- `mark_words_for_review` - Mark words for immediate review

### Grammar Tools
- `add_grammar_concept` - Add new grammar concepts
- `get_grammar_concepts` - Get concepts with filtering
- `update_grammar_mastery` - Update mastery status
- `search_grammar` - Search grammar concepts

### Study Tools
- `get_study_session_data` - Prepare study sessions
- `update_study_progress` - Update progress after studying

## Database Structure

See SETUP_GUIDE.md for detailed database schema and setup instructions.
