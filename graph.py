from langgraph.graph import StateGraph, END
from state import ChatState
from nodes import (
    analyze_intent_node,
    database_operation_node,
    generate_response_node,
    should_continue
)

def create_graph() -> StateGraph:
    """Create and configure the LangGraph"""
    
    # Initialize the graph
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("analyze_intent", analyze_intent_node)
    workflow.add_node("database", database_operation_node)
    workflow.add_node("response", generate_response_node)
    
    # Set entry point
    workflow.set_entry_point("analyze_intent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "analyze_intent",
        should_continue,
        {
            "database": "database",
            "response": "response"
        }
    )
    
    # Add edge from database to response
    workflow.add_edge("database", "response")
    
    # Add edge from response to end
    workflow.add_edge("response", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app

# Create the graph instance
graph = create_graph()