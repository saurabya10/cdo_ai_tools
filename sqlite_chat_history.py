#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite-based Chat Message History for LangChain
Drop-in replacement for FileChatMessageHistory with persistent storage and configurable limits
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path

try:
    from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain.memory.chat_message_histories.base import BaseChatMessageHistory
except ImportError:
    try:
        from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
        from langchain_core.chat_history import BaseChatMessageHistory
    except ImportError:
        # Fallback for testing without langchain
        class BaseMessage:
            def __init__(self, content="", additional_kwargs=None):
                self.content = content
                self.additional_kwargs = additional_kwargs or {}
        
        class HumanMessage(BaseMessage):
            pass
        
        class AIMessage(BaseMessage):  
            pass
        
        class SystemMessage(BaseMessage):
            pass
        
        class BaseChatMessageHistory:
            pass


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """
    SQLite-based chat message history with configurable message limits.
    
    Drop-in replacement for FileChatMessageHistory that:
    - Stores conversations in SQLite database
    - Supports configurable message limits
    - Persists across application restarts
    - Works with LangChain memory and MessagesPlaceholder
    """
    
    def __init__(self, session_id="default", db_path="chat_history.db", max_messages=50):
        """
        Initialize SQLite chat history.
        
        Args:
            session_id: Unique identifier for this conversation session
            db_path: Path to SQLite database file
            max_messages: Maximum number of messages to keep (0 = unlimited)
        """
        self.session_id = session_id
        self.db_path = db_path
        self.max_messages = max_messages
        
        # Ensure database exists and is initialized
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    additional_kwargs TEXT,
                    timestamp TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_timestamp 
                ON chat_messages(session_id, timestamp)
            """)
    
    def _message_to_dict(self, message):
        """Convert LangChain message to dictionary for storage"""
        return {
            "type": message.__class__.__name__,
            "content": message.content,
            "additional_kwargs": json.dumps(message.additional_kwargs),
            "timestamp": datetime.now().isoformat()
        }
    
    def _dict_to_message(self, msg_dict):
        """Convert dictionary back to LangChain message"""
        message_type = msg_dict["type"]
        content = msg_dict["content"]
        additional_kwargs = json.loads(msg_dict["additional_kwargs"]) if msg_dict["additional_kwargs"] else {}
        
        if message_type == "HumanMessage":
            return HumanMessage(content=content, additional_kwargs=additional_kwargs)
        elif message_type == "AIMessage":
            return AIMessage(content=content, additional_kwargs=additional_kwargs)
        elif message_type == "SystemMessage":
            return SystemMessage(content=content, additional_kwargs=additional_kwargs)
        else:
            # Fallback for unknown message types
            return HumanMessage(content=content, additional_kwargs=additional_kwargs)
    
    def add_message(self, message):
        """Add a message to the chat history"""
        msg_dict = self._message_to_dict(message)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO chat_messages (session_id, message_type, content, additional_kwargs, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.session_id,
                msg_dict["type"],
                msg_dict["content"],
                msg_dict["additional_kwargs"],
                msg_dict["timestamp"]
            ))
        
        # Enforce message limit if configured
        if self.max_messages > 0:
            self._enforce_message_limit()
    
    def _enforce_message_limit(self):
        """Remove oldest messages if we exceed the limit"""
        with sqlite3.connect(self.db_path) as conn:
            # Count current messages for this session
            cursor = conn.execute("""
                SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
            """, (self.session_id,))
            
            current_count = cursor.fetchone()[0]
            
            if current_count > self.max_messages:
                # Delete oldest messages beyond the limit
                messages_to_delete = current_count - self.max_messages
                conn.execute("""
                    DELETE FROM chat_messages 
                    WHERE id IN (
                        SELECT id FROM chat_messages 
                        WHERE session_id = ? 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                """, (self.session_id, messages_to_delete))
    
    @property
    def messages(self):
        """Retrieve all messages for this session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT message_type, content, additional_kwargs, timestamp
                FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC
            """, (self.session_id,))
            
            messages = []
            for row in cursor.fetchall():
                msg_dict = {
                    "type": row["message_type"],
                    "content": row["content"],
                    "additional_kwargs": row["additional_kwargs"],
                    "timestamp": row["timestamp"]
                }
                messages.append(self._dict_to_message(msg_dict))
            
            return messages
    
    def clear(self):
        """Clear all messages for this session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM chat_messages WHERE session_id = ?
            """, (self.session_id,))
    
    def get_session_stats(self):
        """Get statistics about this session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message,
                    COUNT(CASE WHEN message_type = 'HumanMessage' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN message_type = 'AIMessage' THEN 1 END) as ai_messages
                FROM chat_messages 
                WHERE session_id = ?
            """, (self.session_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}
    
    @classmethod
    def list_sessions(cls, db_path="chat_history.db"):
        """List all available session IDs in the database"""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT session_id FROM chat_messages ORDER BY session_id
            """)
            return [row[0] for row in cursor.fetchall()]
    
    @classmethod
    def delete_session(cls, session_id, db_path="chat_history.db"):
        """Delete all messages for a specific session"""
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                DELETE FROM chat_messages WHERE session_id = ?
            """, (session_id,))


# Configuration helper
class ChatConfig:
    """Configuration for chat history settings"""
    
    def __init__(self, config_file="chat_config.json"):
        self.config_file = config_file
        self.default_config = {
            "max_messages": 50,
            "db_path": "chat_history.db",
            "default_session": "main_session"
        }
    
    def load_config(self):
        """Load configuration from file or create with defaults"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults for missing keys
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
        except FileNotFoundError:
            # Create default config file
            self.save_config(self.default_config)
            return self.default_config
    
    def save_config(self, config):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)


if __name__ == "__main__":
    # Demo and testing
    print("SQLite Chat History Demo")
    print("=" * 40)
    
    # Test basic functionality
    chat_history = SQLiteChatMessageHistory(
        session_id="demo_session",
        db_path="demo_chat.db", 
        max_messages=10
    )
    
    # Add some test messages
    chat_history.add_message(HumanMessage(content="Hello, this is a test message"))
    chat_history.add_message(AIMessage(content="Hi! I'm responding to your test message"))
    chat_history.add_message(HumanMessage(content="Can you remember this conversation after restart?"))
    chat_history.add_message(AIMessage(content="Yes! This conversation is stored in SQLite database"))
    
    # Show messages
    print("\nMessages in database:")
    for i, msg in enumerate(chat_history.messages, 1):
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        print("   {}. {}: {}".format(i, role, msg.content))
    
    # Show session stats
    print("\nSession Statistics:")
    stats = chat_history.get_session_stats()
    for key, value in stats.items():
        print("   {}: {}".format(key, value))
    
    # Show all sessions
    print("\nAll Sessions:")
    sessions = SQLiteChatMessageHistory.list_sessions("demo_chat.db")
    for session in sessions:
        print("   - {}".format(session))
    
    print("\nDemo completed! Database saved as 'demo_chat.db'")
