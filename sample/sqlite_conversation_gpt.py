#!/usr/bin/env python3
"""
Enhanced conversation_gpt.py using SQLite database for persistent chat history
Drop-in upgrade from FileChatMessageHistory to SQLite with configurable limits
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import local_settings
from local_settings import get_api_key
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from sqlite_chat_history import SQLiteChatMessageHistory, ChatConfig
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    """Get LLM instance - same as your original code"""
    if local_settings.llm_source == "bridgeIT":
        api_key = get_api_key()
        llm_model = local_settings.llm_model
        api_version = local_settings.api_version
        llm_endpoint = local_settings.llm_endpoint
        app_key = local_settings.app_key
        llm = AzureChatOpenAI(
            model=llm_model,
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=llm_endpoint,
            temperature=0.7,
            model_kwargs=dict(user='{"appkey": "' + app_key + '", "user": "user1"}'),
        )
        return llm


def main():
    """Enhanced main function with SQLite persistence"""
    print("🤖 Enhanced Conversation GPT with SQLite History")
    print("=" * 50)
    
    # Load configuration
    config = ChatConfig().load_config()
    print("Configuration loaded:")
    print("   Max messages: {}".format(config['max_messages']))
    print("   Database: {}".format(config['db_path']))
    print("   Session: {}".format(config['default_session']))
    
    # Initialize LLM
    llm = get_llm()
    
    # Create SQLite chat history (replaces FileChatMessageHistory)
    sqlite_chat_history = SQLiteChatMessageHistory(
        session_id=config['default_session'],
        db_path=config['db_path'],
        max_messages=config['max_messages']
    )
    
    # Check if we have existing conversation
    existing_stats = sqlite_chat_history.get_session_stats()
    if existing_stats.get('total_messages', 0) > 0:
        print("\nResuming conversation:")
        print("   Previous messages: {}".format(existing_stats['total_messages']))
        print("   First message: {}".format(existing_stats.get('first_message', 'N/A')))
        print("   Last message: {}".format(existing_stats.get('last_message', 'N/A')))
        
        # Show recent context
        recent_messages = sqlite_chat_history.messages[-4:]  # Last 2 exchanges
        if recent_messages:
            print("\nRecent context:")
            for msg in recent_messages:
                role = "You" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                print("   {}: {}".format(role, content))
    else:
        print("\nStarting new conversation")
    
    # Create memory with SQLite backend (same interface as FileChatMessageHistory)
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        chat_memory=sqlite_chat_history  # This is the key change!
    )
    
    # Create prompt template (exactly same as your original)
    chatPromptTemplate = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. You have access to our previous conversation history."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{content}")
    ]) 
    
    # Create chain (exactly same as your original)
    chain = LLMChain(
        llm=llm,
        prompt=chatPromptTemplate,
        memory=memory,
        verbose=True
    )
    
    # Interactive chat loop with enhanced commands
    print("\nChat started! Type 'exit' to quit, 'stats' for session info, 'clear' to reset")
    print("=" * 50)
    
    while True:
        user_input = input("\n👤 You: ").strip()
        
        if not user_input:
            continue
            
        # Handle special commands
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        elif user_input.lower() == "stats":
            stats = sqlite_chat_history.get_session_stats()
            print("\nSession Statistics:")
            for key, value in stats.items():
                print("   {}: {}".format(key, value))
            continue
        elif user_input.lower() == "clear":
            sqlite_chat_history.clear()
            memory.clear()
            print("🗑️ Conversation history cleared!")
            continue
        elif user_input.lower() == "sessions":
            sessions = SQLiteChatMessageHistory.list_sessions(config['db_path'])
            print("\nAvailable sessions:")
            for session in sessions:
                print("   - {}".format(session))
            continue
        elif user_input.lower() == "help":
            print("""
Available Commands:
  • exit/quit - Exit the application
  • stats     - Show session statistics
  • clear     - Clear conversation history
  • sessions  - List all available sessions
  • help      - Show this help message
  
All your conversations are automatically saved to SQLite database!
   Database: {}
   Session: {}
   Max messages: {}
            """.format(config['db_path'], config['default_session'], config['max_messages']))
            continue
        
        try:
            # Get response from chain (same as original)
            response = chain.run(content=user_input)
            print("Assistant: {}".format(response))
            
        except Exception as e:
            print("Error: {}".format(str(e)))
    
    # Show final stats
    final_stats = sqlite_chat_history.get_session_stats()
    print("\nFinal session statistics:")
    for key, value in final_stats.items():
        print("   {}: {}".format(key, value))
    
    print("\nConversation saved to: {}".format(config['db_path']))
    print("Restart this app anytime to continue the conversation!")


if __name__ == "__main__":
    main()
