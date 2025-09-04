#!/usr/bin/env python3
"""
Main application entry point for the LLM Tool Orchestrator
"""
import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any
import click
from dotenv import load_dotenv

from mcp_server import MCPServer

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)


class LLMToolOrchestrator:
    """Main application class for orchestrating LLM and tools"""
    
    def __init__(self):
        self.mcp_server = MCPServer()
        self.running = True
    
    async def start_interactive_session(self):
        """Start an interactive session with the user"""
        print("\n🚀 Welcome to the LLM Tool Orchestrator!")
        print("This system can help you with:")
        print("  📁 Reading and analyzing CSV/text files")
        print("  🗃️  Querying DynamoDB tables")
        print("  💭 General conversation and assistance")
        print("\nType 'help' for commands, 'quit' to exit\n")
        
        while self.running:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    await self._show_help()
                    continue
                elif user_input.lower() == 'tools':
                    await self._list_tools()
                    continue
                elif user_input.lower() == 'history':
                    await self._show_conversation_history()
                    continue
                elif user_input.lower() == 'clear':
                    await self._clear_conversation()
                    continue
                elif user_input.lower() == 'sessions':
                    await self._list_sessions()
                    continue
                elif user_input.lower().startswith('switch '):
                    session_id = user_input.split(' ', 1)[1].strip()
                    await self._switch_session(session_id)
                    continue
                
                # Process user input through MCP server
                print("🤔 Processing your request...")
                result = await self.mcp_server.analyze_and_route(user_input)
                
                if result['success']:
                    print(f"\n🤖 Assistant: {result.get('response', 'Operation completed successfully')}")
                    
                    # Show raw data if available and requested
                    if result.get('raw_data') and '--verbose' in user_input:
                        print(f"\n📊 Raw Data:\n{json.dumps(result['raw_data'], indent=2)}")
                
                else:
                    print(f"\n❌ Error: {result.get('error', 'Unknown error occurred')}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive session: {str(e)}")
                print(f"\n❌ Unexpected error: {str(e)}")
    
    async def _show_help(self):
        """Show help information"""
        help_text = """
        📚 Available Commands:
        
        • help          - Show this help message
        • tools         - List available tools and their descriptions
        • history       - Show conversation history
        • clear         - Clear conversation history
        • sessions      - List all conversation sessions
        • switch <name> - Switch to a different session
        • quit/exit/q   - Exit the application
        
        🎯 Usage Examples:
        
        File Operations:
        • "Read the data from sales_report.csv"
        • "Search for 'error' in system_log.txt"
        • "Analyze the content of data/users.csv"
        
        DynamoDB Operations:
        • "Show me all tables"
        • "Find user with ID 12345 in users table"
        • "Query orders table for customer ABC123"
        • "Get all products with price greater than 100"
        
        General Chat:
        • "What is machine learning?"
        • "Explain how DynamoDB works"
        • "Help me understand this error message"
        
        💡 Tips:
        • Be specific about file paths and table names
        • Add '--verbose' to see raw data output
        • Use natural language - the system will understand your intent
        """
        print(help_text)
    
    async def _list_tools(self):
        """List available tools"""
        result = await self.mcp_server.list_tools()
        
        if result['success']:
            print("\n🛠️  Available Tools:")
            for tool in result['tools']:
                print(f"\n  📋 {tool['name']}")
                print(f"     {tool['description']}")
                
                if tool['parameters']:
                    print("     Parameters:")
                    for param, config in tool['parameters'].items():
                        required = "(required)" if config.get('required', False) else "(optional)"
                        print(f"       - {param}: {config['type']} {required}")
        else:
            print(f"❌ Error listing tools: {result.get('error')}")
    
    async def _show_conversation_history(self):
        """Show conversation history and statistics"""
        try:
            summary = await self.mcp_server.get_conversation_summary()
            
            print(f"\n💬 Conversation Summary:")
            print(f"   Session ID: {summary['session_id']}")
            print(f"   Total messages: {summary['message_count']}")
            print(f"   Exchanges: {summary['exchange_count']}")
            print(f"   Database: {summary.get('database_path', 'N/A')}")
            print(f"   Max messages: {summary.get('max_messages', 'N/A')}")
            print(f"   Persistent storage: {'✅ Yes' if summary.get('persistent_storage') else '❌ No'}")
            
            if summary.get('database_stats'):
                stats = summary['database_stats']
                if stats:
                    print(f"   First message: {stats.get('first_message', 'N/A')}")
                    print(f"   Last message: {stats.get('last_message', 'N/A')}")
            
            if summary['has_history']:
                print(f"\n📝 Recent Messages:")
                for i, msg in enumerate(summary['last_messages']):
                    role_emoji = "👤" if msg["role"] == "user" else "🤖"
                    role_name = "You" if msg["role"] == "user" else "Assistant"
                    content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    print(f"   {role_emoji} {role_name}: {content}")
            else:
                print("   No conversation history yet.")
                
        except Exception as e:
            print(f"❌ Error showing history: {str(e)}")
    
    async def _clear_conversation(self):
        """Clear conversation history"""
        try:
            self.mcp_server.clear_conversation()
            print("✅ Conversation history cleared!")
        except Exception as e:
            print(f"❌ Error clearing history: {str(e)}")
    
    async def _list_sessions(self):
        """List all conversation sessions"""
        try:
            sessions = self.mcp_server.list_conversation_sessions()
            current_session = self.mcp_server.default_session_id
            
            print(f"\n🗂️  Available Sessions:")
            if not sessions:
                print("   No sessions found.")
            else:
                for session in sessions:
                    indicator = "👉 " if session == current_session else "   "
                    status = "(current)" if session == current_session else ""
                    print(f"   {indicator}{session} {status}")
                
                print(f"\n💡 Use 'switch <session_name>' to switch sessions")
        except Exception as e:
            print(f"❌ Error listing sessions: {str(e)}")
    
    async def _switch_session(self, session_id: str):
        """Switch to a different conversation session"""
        try:
            result = self.mcp_server.switch_session(session_id)
            print(f"✅ {result}")
            
            # Show brief info about the new session
            summary = await self.mcp_server.get_conversation_summary()
            if summary['has_history']:
                print(f"   📊 This session has {summary['message_count']} messages")
            else:
                print(f"   ✨ Starting fresh conversation in this session")
                
        except Exception as e:
            print(f"❌ Error switching session: {str(e)}")
    
    async def process_single_request(self, request: str) -> Dict[str, Any]:
        """Process a single request (useful for API/batch mode)"""
        try:
            result = await self.mcp_server.analyze_and_route(request)
            return result
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def call_tool_directly(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a specific tool directly with parameters"""
        try:
            result = await self.mcp_server.call_tool(tool_name, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def shutdown(self):
        """Cleanup and shutdown"""
        self.running = False
        await self.mcp_server.close()
        logger.info("Application shutdown complete")


@click.group()
def cli():
    """LLM Tool Orchestrator - Intelligent routing between file reading, DynamoDB queries, and LLM chat"""
    pass


@cli.command()
def interactive():
    """Start interactive session"""
    async def main():
        orchestrator = LLMToolOrchestrator()
        try:
            await orchestrator.start_interactive_session()
        finally:
            await orchestrator.shutdown()
    
    asyncio.run(main())


@cli.command()
@click.argument('request')
@click.option('--verbose', is_flag=True, help='Show detailed output including raw data')
def process(request, verbose):
    """Process a single request"""
    async def main():
        orchestrator = LLMToolOrchestrator()
        try:
            result = await orchestrator.process_single_request(request)
            
            if result['success']:
                print(result.get('response', 'Operation completed successfully'))
                
                if verbose and result.get('raw_data'):
                    print(f"\nRaw Data:\n{json.dumps(result['raw_data'], indent=2)}")
            else:
                print(f"Error: {result.get('error', 'Unknown error occurred')}")
                sys.exit(1)
                
        finally:
            await orchestrator.shutdown()
    
    asyncio.run(main())


@cli.command()
@click.argument('tool_name')
@click.argument('params')
def call_tool(tool_name, params):
    """Call a specific tool with JSON parameters"""
    async def main():
        orchestrator = LLMToolOrchestrator()
        try:
            # Parse JSON parameters
            try:
                kwargs = json.loads(params)
            except json.JSONDecodeError:
                print("Error: Parameters must be valid JSON")
                sys.exit(1)
            
            result = await orchestrator.call_tool_directly(tool_name, **kwargs)
            
            if result['success']:
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {result.get('error', 'Unknown error occurred')}")
                sys.exit(1)
                
        finally:
            await orchestrator.shutdown()
    
    asyncio.run(main())


@cli.command()
def list_tools():
    """List available tools"""
    async def main():
        orchestrator = LLMToolOrchestrator()
        try:
            result = await orchestrator.mcp_server.list_tools()
            
            if result['success']:
                print("Available Tools:")
                for tool in result['tools']:
                    print(f"\n{tool['name']}: {tool['description']}")
                    if tool['parameters']:
                        print("  Parameters:")
                        for param, config in tool['parameters'].items():
                            required = "(required)" if config.get('required', False) else "(optional)"
                            print(f"    {param}: {config['type']} {required}")
            else:
                print(f"Error: {result.get('error')}")
                
        finally:
            await orchestrator.shutdown()
    
    asyncio.run(main())


if __name__ == '__main__':
    cli()
