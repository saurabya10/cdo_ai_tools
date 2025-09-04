#!/usr/bin/env python3
"""
Conversation Memory Examples - Demonstrating different approaches to maintain chat history
"""

import asyncio
import json
from typing import Dict, Any, List
from mcp_server import MCPServer
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory

# Example system templates
SPORTS_ANALYSIS_TEMPLATE = """
You are a sports data analyst assistant. Analyze sports performance data and provide insights about player consistency and performance patterns.

Based on the data provided, identify:
1. Players who perform consistently well at specific grounds
2. Performance patterns and trends
3. Statistical insights and recommendations

Use the conversation history to build upon previous analysis and maintain context.
"""

GENERAL_ASSISTANT_TEMPLATE = """
You are a helpful AI assistant with access to various tools for file operations, database queries, and general conversation.
You maintain context from previous conversations to provide better assistance.
"""

class ConversationMemoryDemo:
    """Demonstration class for different conversation memory approaches"""
    
    def __init__(self):
        self.mcp_server = MCPServer()
    
    async def demo_simple_memory_approach(self):
        """Demo 1: Simple conversation memory (current implementation)"""
        print("🔷 Demo 1: Simple Conversation Memory")
        print("=" * 50)
        
        # Start a conversation
        questions = [
            "What's the weather like today?",
            "What did I just ask you about?",
            "Can you remember our previous exchange?"
        ]
        
        session_id = "demo_session_1"
        
        for i, question in enumerate(questions, 1):
            print(f"\n👤 Question {i}: {question}")
            
            result = await self.mcp_server._handle_llm_chat(
                prompt=question,
                session_id=session_id
            )
            
            if result['success']:
                print(f"🤖 Response: {result['response']}")
            else:
                print(f"❌ Error: {result['error']}")
            
            # Show conversation summary
            if i == len(questions):
                summary = await self.mcp_server.get_conversation_summary(session_id)
                print(f"\n📊 Conversation Summary: {json.dumps(summary, indent=2)}")
    
    async def demo_messages_placeholder_approach(self):
        """Demo 2: MessagesPlaceholder with ChatPromptTemplate"""
        print("\n🔶 Demo 2: MessagesPlaceholder Approach")
        print("=" * 50)
        
        # Create a sports analysis scenario
        system_template = SPORTS_ANALYSIS_TEMPLATE
        
        # Sample data for sports analysis
        sample_data = """
        Player Performance Data:
        - John Smith: Ground A (85, 92, 88), Ground B (45, 52, 48), Ground C (91, 89, 93)
        - Mike Johnson: Ground A (76, 73, 79), Ground B (88, 91, 85), Ground C (82, 78, 80)
        - Sarah Wilson: Ground A (93, 95, 91), Ground B (94, 89, 92), Ground C (87, 85, 89)
        """
        
        questions = [
            f"Here is the player data: {sample_data}\nWhich player performs most consistently at Ground A?",
            "What about Ground B? Compare their consistency.",
            "Based on our previous analysis, which ground should we recommend for John Smith?"
        ]
        
        session_id = "sports_demo_session"
        
        for i, question in enumerate(questions, 1):
            print(f"\n👤 Question {i}: {question}")
            
            # Use MessagesPlaceholder approach
            result = await self.mcp_server.chat_with_memory_chain(
                user_input=question,
                system_template=system_template,
                session_id=session_id
            )
            
            if result['success']:
                print(f"🤖 Response: {result['response']}")
                print(f"📋 Method: {result['method']}")
            else:
                print(f"❌ Error: {result['error']}")
    
    async def demo_file_analysis_with_context(self):
        """Demo 3: File analysis maintaining context across operations"""
        print("\n🔸 Demo 3: File Analysis with Context")
        print("=" * 50)
        
        # This would demonstrate how file analysis maintains context
        questions = [
            "Read the tenant_reports/sample_tenant_processing.csv file",
            "Based on what we just analyzed, what patterns do you see in the time intervals?",
            "Given the previous analysis, which tenant seems most active?"
        ]
        
        session_id = "file_analysis_session"
        
        for i, question in enumerate(questions, 1):
            print(f"\n👤 Question {i}: {question}")
            
            # Route through the normal analyze_and_route which maintains context
            result = await self.mcp_server.analyze_and_route(question)
            
            if result['success']:
                print(f"🤖 Response: {result['response'][:200]}...")
            else:
                print(f"❌ Error: {result['error']}")
    
    async def demo_conversation_management(self):
        """Demo 4: Conversation management features"""
        print("\n🔹 Demo 4: Conversation Management")
        print("=" * 50)
        
        session_id = "management_demo"
        
        # Add some conversation history
        await self.mcp_server._handle_llm_chat(
            prompt="Hello, I'm testing conversation memory",
            session_id=session_id
        )
        
        await self.mcp_server._handle_llm_chat(
            prompt="Can you remember this conversation?",
            session_id=session_id
        )
        
        # Show conversation summary
        summary = await self.mcp_server.get_conversation_summary(session_id)
        print(f"📊 Before clearing - Summary: {json.dumps(summary, indent=2)}")
        
        # Clear conversation
        self.mcp_server.clear_conversation(session_id)
        
        # Show summary after clearing
        summary_after = await self.mcp_server.get_conversation_summary(session_id)
        print(f"📊 After clearing - Summary: {json.dumps(summary_after, indent=2)}")
    
    async def demo_multiple_sessions(self):
        """Demo 5: Multiple concurrent sessions"""
        print("\n🔺 Demo 5: Multiple Sessions")
        print("=" * 50)
        
        # Session 1: Tech discussion
        result1 = await self.mcp_server._handle_llm_chat(
            prompt="Let's discuss machine learning algorithms",
            session_id="tech_session"
        )
        
        # Session 2: Sports discussion
        result2 = await self.mcp_server._handle_llm_chat(
            prompt="Let's talk about football strategies",
            session_id="sports_session"
        )
        
        # Continue Session 1
        result1_continue = await self.mcp_server._handle_llm_chat(
            prompt="What did we just start discussing?",
            session_id="tech_session"
        )
        
        # Continue Session 2
        result2_continue = await self.mcp_server._handle_llm_chat(
            prompt="What was our previous topic?",
            session_id="sports_session"
        )
        
        print("🔧 Tech Session Context:")
        if result1_continue['success']:
            print(f"   {result1_continue['response'][:100]}...")
        
        print("⚽ Sports Session Context:")
        if result2_continue['success']:
            print(f"   {result2_continue['response'][:100]}...")
    
    async def show_messages_placeholder_structure(self):
        """Show the structure of MessagesPlaceholder"""
        print("\n📋 MessagesPlaceholder Structure Example")
        print("=" * 50)
        
        # Create a sample prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant analyzing {data_type} data."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Based on the data: {data}\n\nQuestion: {question}")
        ])
        
        print("🏗️ Prompt Template Structure:")
        print(f"   Messages: {len(prompt_template.messages)}")
        
        for i, message in enumerate(prompt_template.messages):
            if hasattr(message, 'variable_name'):
                print(f"   {i+1}. MessagesPlaceholder(variable_name='{message.variable_name}')")
            else:
                print(f"   {i+1}. {type(message).__name__}: {message.prompt.template[:50]}...")
        
        # Show how it would be used
        print("\n📝 Usage Example:")
        print("""
        # 1. Create the template (done above)
        
        # 2. Get conversation history from memory
        memory_variables = self.conversation_memory.load_memory_variables({})
        chat_history = memory_variables.get('chat_history', [])
        
        # 3. Create the chain
        chain = prompt_template | llm
        
        # 4. Invoke with all variables
        response = chain.invoke({
            "data_type": "sales",
            "data": "Q1 Sales: $100K, Q2 Sales: $150K",
            "question": "What's the growth trend?",
            "chat_history": chat_history  # This is where MessagesPlaceholder gets filled
        })
        """)
    
    async def run_all_demos(self):
        """Run all demonstration scenarios"""
        print("🚀 Conversation Memory Demonstration")
        print("=" * 70)
        
        try:
            await self.demo_simple_memory_approach()
            await self.demo_messages_placeholder_approach()
            await self.demo_file_analysis_with_context()
            await self.demo_conversation_management()
            await self.demo_multiple_sessions()
            await self.show_messages_placeholder_structure()
            
            print("\n✅ All demonstrations completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during demonstration: {str(e)}")
        
        finally:
            await self.mcp_server.close()

# Utility functions for team demonstration
def explain_memory_types():
    """Explain different memory types available"""
    explanations = {
        "ConversationBufferWindowMemory": {
            "description": "Keeps the last N message exchanges in memory",
            "use_case": "Good for recent context, memory efficient",
            "example": "Keeps last 10 exchanges (20 messages total)"
        },
        "ConversationSummaryBufferMemory": {
            "description": "Summarizes old conversations, keeps recent ones in full",
            "use_case": "Good for very long conversations",
            "example": "Summarizes messages beyond token limit"
        },
        "ConversationBufferMemory": {
            "description": "Keeps all conversation history",
            "use_case": "Simple but can grow very large",
            "example": "Stores every message exchange"
        }
    }
    
    print("🧠 Memory Types Comparison:")
    print("=" * 50)
    
    for memory_type, info in explanations.items():
        print(f"\n📝 {memory_type}:")
        print(f"   Description: {info['description']}")
        print(f"   Use case: {info['use_case']}")
        print(f"   Example: {info['example']}")

async def main():
    """Main demonstration function"""
    print("Starting Conversation Memory Demonstrations...")
    
    # Show memory types explanation
    explain_memory_types()
    
    # Run demonstrations
    demo = ConversationMemoryDemo()
    await demo.run_all_demos()

if __name__ == "__main__":
    asyncio.run(main())
