from dotenv import load_dotenv
from graph import graph
from state import ChatState
from nodes import DatabaseManager

# Load environment variables
load_dotenv()

def initialize_database():
    """Initialize database with sample table and data"""
    db = DatabaseManager()
    print("Setting up database...")
    
    # Create sample table
    result = db.create_sample_table()
    if result.get("success"):
        print("✓ Sample table created successfully")
    else:
        print(f"✗ Error creating table: {result.get('error', 'Unknown error')}")
    
    # Insert sample data
    results = db.insert_sample_data()
    print("✓ Sample data inserted")
    
    return True

def run_cli():
    """Run the CLI version of the chatbot"""
    print("🤖 AI Database Assistant")
    print("Type 'quit' to exit\n")
    
    # Initialize conversation state
    conversation_state = {
        "messages": [],
        "user_input": "",
        "assistant_response": "",
        "conversation_history": [],
        "sql_query": None,
        "sql_result": None,
        "db_operation": None,
        "error_message": None
    }
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Update state with user input
        conversation_state["user_input"] = user_input
        conversation_state["error_message"] = None
        
        try:
            # Run the graph
            result = graph.invoke(conversation_state)
            print(f"\nAssistant: {result['assistant_response']}\n")
            
            # Update conversation state
            conversation_state = result
            
        except Exception as e:
            print(f"Error: {str(e)}\n")

def process_message(message: str, conversation_state: dict) -> dict:
    """Process a single message through the graph"""
    conversation_state["user_input"] = message
    conversation_state["error_message"] = None
    
    try:
        result = graph.invoke(conversation_state)
        return result
    except Exception as e:
        conversation_state["assistant_response"] = f"I encountered an error: {str(e)}"
        return conversation_state

if __name__ == "__main__":
    # Initialize database
    initialize_database()
    
    # Run CLI
    run_cli()