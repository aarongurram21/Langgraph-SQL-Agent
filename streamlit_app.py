import streamlit as st
import os
from dotenv import load_dotenv
from main import process_message, initialize_database
from nodes import DatabaseManager

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Database Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "conversation_state" not in st.session_state:
    st.session_state.conversation_state = {
        "messages": [],
        "user_input": "",
        "assistant_response": "",
        "conversation_history": [],
        "sql_query": None,
        "sql_result": None,
        "db_operation": None,
        "error_message": None
    }

if "initialized" not in st.session_state:
    st.session_state.initialized = False

def initialize_app():
    """Initialize the application"""
    if not st.session_state.initialized:
        with st.spinner("Setting up database..."):
            try:
                initialize_database()
                st.session_state.initialized = True
                st.success("✅ Database initialized successfully!")
            except Exception as e:
                st.error(f"❌ Database initialization failed: {str(e)}")

def main():
    st.title("🤖 AI Database Assistant")
    st.markdown("---")
    
    # Initialize app
    initialize_app()
    
    # Sidebar with database info
    with st.sidebar:
        st.header("📊 Database Info")
        
        if st.button("🔄 Refresh Tables"):
            db = DatabaseManager()
            tables_result = db.get_all_tables()
            if tables_result.get("success"):
                st.write("**Available Tables:**")
                for table in tables_result["data"]:
                    st.write(f"- {table['table_name']}")
            else:
                st.error("Failed to fetch tables")
        
        st.markdown("---")
        st.header("💡 Example Queries")
        st.markdown("""
        **View Data:**
        - "Show me all users"
        - "List users older than 25"
        - "Find user with email john@example.com"
        
        **Add Data:**
        - "Add a new user Alice with email alice@test.com and age 28"
        - "Insert user Bob, bob@example.com, age 32"
        
        **Update Data:**
        - "Update John's age to 35"
        - "Change email of user with id 1 to newemail@test.com"
        
        **Delete Data:**
        - "Delete user with id 3"
        - "Remove users older than 40"
        
        **General Chat:**
        - "Hello!"
        - "What can you help me with?"
        - "Explain the database structure"
        """)
    
    # Main chat interface
    st.header("💬 Chat")
    
    # Display conversation history
    chat_container = st.container()
    
    with chat_container:
        if st.session_state.conversation_state["conversation_history"]:
            for message in st.session_state.conversation_state["conversation_history"]:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your database...")
    
    if user_input:
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Process message
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = process_message(user_input, st.session_state.conversation_state)
                st.session_state.conversation_state = result
                st.write(result["assistant_response"])
        
        # Display SQL query and results if applicable
        if result.get("sql_query"):
            with st.expander("🔍 SQL Query Executed"):
                st.code(result["sql_query"], language="sql")
            
            if result.get("sql_result"):
                with st.expander("📊 Database Results"):
                    if result["sql_result"].get("success"):
                        if result["sql_result"].get("data"):
                            st.dataframe(result["sql_result"]["data"])
                        st.success(result["sql_result"].get("message", "Operation completed successfully"))
                    else:
                        st.error(result["sql_result"].get("error", "Unknown error"))
    
    # Clear conversation button
    if st.button("🗑️ Clear Conversation"):
        st.session_state.conversation_state = {
            "messages": [],
            "user_input": "",
            "assistant_response": "",
            "conversation_history": [],
            "sql_query": None,
            "sql_result": None,
            "db_operation": None,
            "error_message": None
        }
        st.rerun()

if __name__ == "__main__":
    main()