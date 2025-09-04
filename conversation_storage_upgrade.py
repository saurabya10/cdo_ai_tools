#!/usr/bin/env python3
"""
Conversation Memory Storage Upgrade Options

This file shows different approaches to upgrade from in-memory to persistent storage
"""

import json
import sqlite3
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid

@dataclass
class ConversationMessage:
    """Single conversation message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ConversationSession:
    """Complete conversation session"""
    session_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None

# =============================================================================
# Option 1: SQLite Database (Simple, File-based)
# =============================================================================
class SQLiteConversationStore:
    """SQLite-based conversation storage"""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)')
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Save a single message"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Upsert session
            conn.execute('''
                INSERT OR REPLACE INTO sessions (session_id, created_at, updated_at, metadata)
                VALUES (?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?, ?)
            ''', (session_id, session_id, timestamp, timestamp, json.dumps(metadata or {})))
            
            # Insert message
            conn.execute('''
                INSERT INTO conversations (id, session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (message_id, session_id, role, content, timestamp, json.dumps(metadata or {})))
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT role, content, timestamp, metadata
                FROM conversations 
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (session_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
            conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))

# =============================================================================
# Option 2: Redis Cache (Fast, In-Memory with Persistence)
# =============================================================================
class RedisConversationStore:
    """Redis-based conversation storage"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 ttl: int = 3600):  # 1 hour TTL
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = ttl
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"conversation:{session_id}"
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Save a single message"""
        key = self._session_key(session_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Get existing conversation
        existing = self.redis_client.get(key)
        if existing:
            conversation = json.loads(existing)
        else:
            conversation = {"messages": [], "created_at": datetime.now().isoformat()}
        
        # Add new message
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()
        
        # Keep only last 20 messages (10 exchanges)
        if len(conversation["messages"]) > 20:
            conversation["messages"] = conversation["messages"][-20:]
        
        # Save back to Redis with TTL
        self.redis_client.setex(key, self.ttl, json.dumps(conversation))
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history"""
        key = self._session_key(session_id)
        data = self.redis_client.get(key)
        
        if data:
            conversation = json.loads(data)
            return conversation.get("messages", [])
        return []
    
    def clear_conversation(self, session_id: str):
        """Clear conversation"""
        key = self._session_key(session_id)
        self.redis_client.delete(key)

# =============================================================================
# Option 3: Hybrid Approach (Redis + Database)
# =============================================================================
class HybridConversationStore:
    """Hybrid storage: Redis for active sessions, Database for persistence"""
    
    def __init__(self, db_store: SQLiteConversationStore, redis_store: RedisConversationStore):
        self.db_store = db_store
        self.redis_store = redis_store
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Save to both Redis (fast access) and Database (persistence)"""
        # Save to Redis for fast access
        self.redis_store.save_message(session_id, role, content, metadata)
        
        # Save to Database for persistence
        self.db_store.save_message(session_id, role, content, metadata)
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get from Redis first (fast), fallback to Database"""
        # Try Redis first
        history = self.redis_store.get_conversation_history(session_id)
        
        if not history:
            # Fallback to database
            history = self.db_store.get_conversation_history(session_id)
            
            # Populate Redis cache if found in DB
            if history:
                for msg in history:
                    self.redis_store.save_message(
                        session_id, 
                        msg["role"], 
                        msg["content"], 
                        json.loads(msg.get("metadata", "{}"))
                    )
        
        return history
    
    def clear_conversation(self, session_id: str):
        """Clear from both stores"""
        self.redis_store.clear_conversation(session_id)
        self.db_store.clear_conversation(session_id)

# =============================================================================
# Integration Example: Enhanced MCPServer
# =============================================================================
class EnhancedMCPServer:
    """Example of how to integrate persistent storage into MCPServer"""
    
    def __init__(self, storage_type: str = "sqlite"):
        # Initialize storage backend
        if storage_type == "sqlite":
            self.conversation_store = SQLiteConversationStore("conversations.db")
        elif storage_type == "redis":
            self.conversation_store = RedisConversationStore()
        elif storage_type == "hybrid":
            db_store = SQLiteConversationStore("conversations.db")
            redis_store = RedisConversationStore()
            self.conversation_store = HybridConversationStore(db_store, redis_store)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    def add_to_conversation(self, user_message: str, ai_response: str, session_id: str = "default"):
        """Add conversation exchange using persistent storage"""
        # Save user message
        self.conversation_store.save_message(
            session_id=session_id,
            role="user", 
            content=user_message,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        
        # Save AI response
        self.conversation_store.save_message(
            session_id=session_id,
            role="assistant", 
            content=ai_response,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    def get_conversation_history(self, session_id: str = "default") -> List[Dict]:
        """Get conversation history from persistent storage"""
        return self.conversation_store.get_conversation_history(session_id)
    
    def clear_conversation(self, session_id: str = "default"):
        """Clear conversation from persistent storage"""
        self.conversation_store.clear_conversation(session_id)

# =============================================================================
# Usage Examples
# =============================================================================
if __name__ == "__main__":
    print("🗄️ Conversation Storage Options Demo")
    print("=" * 50)
    
    # Example 1: SQLite Storage
    print("\n1. SQLite Storage Example:")
    sqlite_store = SQLiteConversationStore("demo.db")
    sqlite_store.save_message("demo_session", "user", "Find device Paradise")
    sqlite_store.save_message("demo_session", "assistant", "Found Paradise device with uidOnFmc...")
    history = sqlite_store.get_conversation_history("demo_session")
    print(f"   Messages stored: {len(history)}")
    
    # Example 2: Enhanced MCP Server with persistent storage
    print("\n2. Enhanced MCP Server Example:")
    try:
        enhanced_server = EnhancedMCPServer("sqlite")
        enhanced_server.add_to_conversation(
            "Check SAL events for Paradise device", 
            "Paradise device last sent events 2 hours ago - STALE",
            "sal_session_001"
        )
        history = enhanced_server.get_conversation_history("sal_session_001")
        print(f"   Enhanced server conversation messages: {len(history)}")
    except Exception as e:
        print(f"   Enhanced server demo: {e}")
    
    print("\n✅ Storage upgrade examples completed!")
