import os
import psycopg2
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
from state import ChatState

load_dotenv()

# Initialize LLM - only used where needed
from langchain_openai import AzureChatOpenAI

def get_llm():
    """Get Azure LLM instance when needed"""
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_deployment=os.getenv("AZURE_GPT4_DEPLOYID"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        temperature=0.1
    )

# Database Manager integrated into nodes
class DatabaseManager:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.connection_string)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        if not self.connect():
            return {"error": "Failed to connect to database"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in results]
                return {"success": True, "data": data, "row_count": len(data)}
            else:
                # For INSERT, UPDATE, DELETE
                self.connection.commit()
                row_count = cursor.rowcount
                return {"success": True, "message": f"Operation completed successfully. {row_count} rows affected.", "row_count": row_count}
                
        except Exception as e:
            self.connection.rollback()
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
        """
        return self.execute_query(query, (table_name,))
    
    def get_all_tables(self) -> Dict[str, Any]:
        """Get all table names in the database"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        return self.execute_query(query)
    
    def create_sample_table(self):
        """Create a sample table for demonstration"""
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        return self.execute_query(query)
    
    def insert_sample_data(self):
        """Insert sample data"""
        users_data = [
            ("John Doe", "john@example.com", 30),
            ("Jane Smith", "jane@example.com", 25),
            ("Bob Johnson", "bob@example.com", 35)
        ]
        
        results = []
        for name, email, age in users_data:
            query = "INSERT INTO users (name, email, age) VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING;"
            result = self.execute_query(query, (name, email, age))
            results.append(result)
        
        return results

# Global database manager instance
db_manager = DatabaseManager()

def analyze_intent_node(state: ChatState) -> ChatState:
    """Analyze user intent to determine if database operation is needed - Uses LLM"""
    
    # Get LLM instance only when needed
    llm = get_llm()
    
    system_prompt = """You are an AI assistant that analyzes user queries to determine if they need database operations.

    Analyze the user's message and determine:
    1. If they want to perform a database operation (SELECT, INSERT, UPDATE, DELETE)
    2. What type of operation it is
    3. Generate appropriate SQL query if needed

    Database Schema:
    - Table: users (id, name, email, age, created_at)
    
    Response format:
    - If database operation needed: {"operation": "select/insert/update/delete", "sql": "SQL_QUERY_HERE"}
    - If just conversation: {"operation": "none", "response": "conversational_response"}
    
    Examples:
    - "Show me all users" -> {"operation": "select", "sql": "SELECT * FROM users;"}
    - "Add a new user John with email john@test.com" -> {"operation": "insert", "sql": "INSERT INTO users (name, email) VALUES ('John', 'john@test.com');"}
    - "Hello" -> {"operation": "none", "response": "Hello! How can I help you today?"}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_input"])
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Parse the response
        if "operation" in content and "select" in content.lower():
            state["db_operation"] = "select"
            # Extract SQL from response
            if "sql" in content:
                sql_start = content.find('"sql": "') + 8
                sql_end = content.find('"', sql_start)
                state["sql_query"] = content[sql_start:sql_end] if sql_end > sql_start else None
        elif "operation" in content and "insert" in content.lower():
            state["db_operation"] = "insert"
            if "sql" in content:
                sql_start = content.find('"sql": "') + 8
                sql_end = content.find('"', sql_start)
                state["sql_query"] = content[sql_start:sql_end] if sql_end > sql_start else None
        elif "operation" in content and "update" in content.lower():
            state["db_operation"] = "update"
            if "sql" in content:
                sql_start = content.find('"sql": "') + 8
                sql_end = content.find('"', sql_start)
                state["sql_query"] = content[sql_start:sql_end] if sql_end > sql_start else None
        elif "operation" in content and "delete" in content.lower():
            state["db_operation"] = "delete"
            if "sql" in content:
                sql_start = content.find('"sql": "') + 8
                sql_end = content.find('"', sql_start)
                state["sql_query"] = content[sql_start:sql_end] if sql_end > sql_start else None
        else:
            state["db_operation"] = "none"
            
    except Exception as e:
        state["error_message"] = f"Error analyzing intent: {str(e)}"
        state["db_operation"] = "none"
    
    return state

def database_operation_node(state: ChatState) -> ChatState:
    """Execute database operations - No LLM needed"""
    
    if state["db_operation"] == "none" or not state["sql_query"]:
        return state
    
    try:
        result = db_manager.execute_query(state["sql_query"])
        state["sql_result"] = result
    except Exception as e:
        state["error_message"] = f"Database error: {str(e)}"
        state["sql_result"] = None
    
    return state

def generate_response_node(state: ChatState) -> ChatState:
    """Generate final response based on operation results - Uses LLM"""
    
    # Get LLM instance only when needed
    llm = get_llm()
    
    conversation_context = ""
    if state["conversation_history"]:
        recent_history = state["conversation_history"][-4:]  # Last 4 exchanges
        for msg in recent_history:
            conversation_context += f"{msg['role']}: {msg['content']}\n"
    
    system_prompt = f"""You are a helpful AI assistant with database access. You help users interact with their database in a natural, conversational way.

    Conversation History:
    {conversation_context}

    Current user input: {state['user_input']}
    
    Database operation performed: {state['db_operation']}
    SQL query executed: {state['sql_query']}
    Database result: {state['sql_result']}
    Any errors: {state['error_message']}

    Instructions:
    1. If there was a database operation, explain what was done and present the results in a user-friendly way
    2. If it was just conversation, respond naturally
    3. If there was an error, explain it helpfully and suggest corrections
    4. Be conversational, helpful, and guide the user
    5. For data results, format them nicely (tables, lists, etc.)
    6. Always ask if they need help with anything else

    Respond in a natural, assistant-like manner."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Generate response based on the context provided.")
    ]
    
    try:
        response = llm.invoke(messages)
        state["assistant_response"] = response.content
    except Exception as e:
        state["assistant_response"] = f"I encountered an error generating a response: {str(e)}"
    
    # Update conversation history
    if not state["conversation_history"]:
        state["conversation_history"] = []
    
    state["conversation_history"].append({
        "role": "user",
        "content": state["user_input"]
    })
    state["conversation_history"].append({
        "role": "assistant", 
        "content": state["assistant_response"]
    })
    
    # Update messages for UI
    state["messages"] = [
        {"role": msg["role"], "content": msg["content"]} 
        for msg in state["conversation_history"]
    ]
    
    return state

def should_continue(state: ChatState) -> str:
    """Determine next node - No LLM needed"""
    if state["db_operation"] and state["db_operation"] != "none":
        return "database"
    else:
        return "response"