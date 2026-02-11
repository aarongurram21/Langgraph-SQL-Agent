from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict


class ChatState(TypedDict):
    """State schema for the chatbot"""
    messages: List[Dict[str, str]]
    user_input: str
    assistant_response: str
    conversation_history: List[Dict[str, str]]
    sql_query: Optional[str]
    sql_result: Optional[Any]
    db_operation: Optional[str]  # 'select', 'insert', 'update', 'delete', 'none'
    error_message: Optional[str]