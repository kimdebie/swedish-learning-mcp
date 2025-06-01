# Swedish Learning MCP Setup Guide

## Prerequisites

1. Python 3.8 or higher
2. A Notion account with an integration token
3. Two Notion databases set up with the correct structure

## Setting Up Notion

### 1. Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Give it a name (e.g., "Swedish Learning MCP")
4. Select the workspace where your databases will be
5. Copy the "Internal Integration Token" - you'll need this for the `.env` file

### 2. Create the Vocabulary Database

Create a new database in Notion with these properties:

| Property Name | Type | Options/Notes |
|--------------|------|---------------|
| Word/Phrase | Title | The main property |
| English Translation | Text | |
| Part of Speech | Select | Options: Noun, Verb, Adjective, Adverb, Phrase, Preposition, Conjunction, Pronoun, Other |
| Definition | Text | |
| Example Sentence | Text | |
| Example Translation | Text | |
| Date Added | Date | |
| Mastery Level | Select | Options: New, Learning, Familiar, Mastered |
| Difficulty | Select | Options: Easy, Medium, Hard |
| Last Reviewed | Date | |
| Review Count | Number | |
| Success Rate | Number | |
| Source Text | Text | |

### 3. Create the Grammar Database

Create another database with these properties:

| Property Name | Type | Options/Notes |
|--------------|------|---------------|
| Concept Name | Title | The main property |
| Category | Select | Options: Verbs, Nouns, Adjectives, Pronouns, Syntax, Word Order, Cases, Other |
| Difficulty Level | Select | Options: Beginner, Intermediate, Advanced |
| Description | Text | |
| Examples | Text | |
| Practice Notes | Text | |
| Date Added | Date | |
| Mastery Status | Select | Options: Learning, Practicing, Comfortable, Mastered |

### 4. Share Databases with Integration

1. Open each database in Notion
2. Click "Share" in the top right
3. Click "Invite"
4. Select your integration from the list
5. Click "Invite"

### 5. Get Database IDs

1. Open each database in Notion
2. Look at the URL in your browser
3. The database ID is the 32-character string after the workspace name and before the question mark
4. Example: `https://www.notion.so/workspace/abc123def456ghi789jkl012mno345pq?v=...`
   - Database ID: `abc123def456ghi789jkl012mno345pq`

## Installing the MCP

### 1. Clone or Download the Project

```bash
cd /Users/kimdebie/Documents/
# If you're setting this up fresh, the files are already in swedish_learning_mcp/
```

### 2. Set Up Python Environment

```bash
cd swedish_learning_mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your values:
   ```
   NOTION_TOKEN=your_actual_integration_token
   VOCAB_DATABASE_ID=your_vocabulary_database_id
   GRAMMAR_DATABASE_ID=your_grammar_database_id
   ```

### 5. Test the Installation

```bash
python -m swedish_learning_mcp.server
```

You should see: "Swedish Learning MCP initialized successfully"

## Configuring Claude Desktop

Add this to your Claude Desktop configuration file:

**On macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**On Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swedish-learning": {
      "command": "python",
      "args": [
        "-m",
        "swedish_learning_mcp.server"
      ],
      "cwd": "/Users/kimdebie/Documents/swedish_learning_mcp",
      "env": {
        "PYTHONPATH": "/Users/kimdebie/Documents/swedish_learning_mcp"
      }
    }
  }
}
```

## Using the MCP

Once configured, you can use these commands in Claude:

### Vocabulary Management
- Add new words: "Add the Swedish word 'hej' which means 'hello'"
- Get words for review: "Show me vocabulary words I need to review"
- Update progress: "I got 8 out of 10 correct for word ID xyz"
- Search vocabulary: "Search for words related to 'food'"
- Extract from text: "Extract challenging words from this Swedish text: ..."

### Grammar Management
- Add concepts: "Add a grammar concept about Swedish verb conjugation"
- View concepts: "Show me all beginner-level grammar concepts"
- Update mastery: "Mark grammar concept ID abc as 'Comfortable'"
- Search grammar: "Search for grammar rules about pronouns"

### Study Sessions
- Get mixed session: "Prepare a study session with 10 vocabulary words and 5 grammar concepts"
- Update progress: "Update my progress for this study session"

## Troubleshooting

### "Notion token not provided"
- Make sure your `.env` file exists and contains the correct token
- Verify the token starts with `secret_`

### "Database IDs not provided"
- Check that both database IDs are in your `.env` file
- Verify they are 32 characters long (no spaces or special characters)

### "Failed to create page"
- Ensure your integration has access to both databases
- Check that all required properties exist in your Notion databases
- Verify property names match exactly (case-sensitive)

### MCP not appearing in Claude
- Restart Claude Desktop after updating the config
- Check the config file path is correct for your OS
- Ensure Python is in your system PATH

## Tips for Success

1. **Start Small**: Add a few words and grammar concepts first to test the system
2. **Regular Reviews**: Use the spaced repetition system daily for best results
3. **Add Context**: Include example sentences when adding new vocabulary
4. **Track Progress**: Use the mastery levels to see your improvement
5. **Customize**: Adjust the review intervals in `utils.py` if needed

## Support

If you encounter issues:
1. Check the logs in the terminal where you ran the server
2. Verify all environment variables are set correctly
3. Ensure your Notion databases have the exact property names listed above
4. Make sure your integration has the necessary permissions

Happy learning! 🇸🇪
