from dotenv import load_dotenv

# Import tool modules to register their tools
from mcp_server import mcp
import vocabulary_tools
import grammar_tools
import study_tools

if __name__ == "__main__":
    load_dotenv()
    # Run the server
    mcp.run(transport='stdio')
