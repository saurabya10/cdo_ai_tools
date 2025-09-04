"""
MCP (Model Context Protocol) Server with integrated tools
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

from tools.file_reader import FileReaderTool
from tools.dynamodb_tool import DynamoDBTool
from tools.scc_tool import SCCTool
from tools.rest_api_tool import RestApiTool
from tools.sal_troubleshoot_tool import SALTroubleshootTool
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory, ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from settings import get_api_key, llm_model, llm_endpoint, api_version, app_key
from sqlite_chat_history import SQLiteChatMessageHistory, ChatConfig

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for handling tool orchestration and LLM interactions"""
    
    def get_llm(self):
        # Get fresh API key using Cisco OAuth2
        api_key = get_api_key()
        return AzureChatOpenAI(
            model=llm_model,
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=llm_endpoint,
            temperature=0.3,
            model_kwargs=dict(user='{"appkey": "' + app_key + '", "user": "user1"}'),
        )

    def __init__(self):
        # Initialize tools
        dynamodb_region = os.getenv('DYNAMODB_REGION', 'us-east-2')
        self.file_reader = FileReaderTool()
        self.dynamodb_tool = DynamoDBTool(region_name=dynamodb_region)
        self.scc_tool = SCCTool()
        self.rest_api_tool = RestApiTool()
        
        # Initialize SAL troubleshooting tool with dependencies
        self.sal_troubleshoot_tool = SALTroubleshootTool(
            scc_tool=self.scc_tool,
            dynamodb_tool=self.dynamodb_tool
        )
        
        # Initialize LLM client using AzureChatOpenAI
        self.llm_client = self.get_llm()
        
        # Load SQLite conversation configuration
        self.chat_config = ChatConfig().load_config()
        
        # Initialize SQLite-based conversation system
        self.default_session_id = self.chat_config.get('default_session', 'main_session')
        self.sqlite_history = SQLiteChatMessageHistory(
            session_id=self.default_session_id,
            db_path=self.chat_config.get('db_path', 'conversations.db'),
            max_messages=self.chat_config.get('max_messages', 100)
        )
        
        # Initialize LangChain memory with SQLite backend
        self.conversation_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            chat_memory=self.sqlite_history,
            input_key="input",
            output_key="output"
        )
        
        # Keep session management for multiple conversations
        self.active_sessions = {}  # {session_id: SQLiteChatMessageHistory instance}
        self.active_sessions[self.default_session_id] = self.sqlite_history
        
        # Initialize tools registry
        self._init_tools()
        
        # Alternative: Window-based memory (can be enabled if needed)
        # self.conversation_window_memory = ConversationBufferWindowMemory(
        #     k=10,  # Keep last 10 exchanges
        #     memory_key="chat_history", 
        #     return_messages=True,
        #     input_key="input",
        #     output_key="output"
        # )
        
    def get_conversation_history(self, session_id: str = None) -> List[Dict[str, str]]:
        """Get conversation history for a session from SQLite"""
        session_id = session_id or self.default_session_id
        
        # Get or create SQLite history for this session
        sqlite_history = self._get_session_history(session_id)
        messages = sqlite_history.messages
        
        # Convert LangChain messages to our expected format
        history = []
        for msg in messages:
            role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
            history.append({
                "role": role,
                "content": msg.content
            })
        
        return history
    
    def _get_session_history(self, session_id: str) -> SQLiteChatMessageHistory:
        """Get or create SQLite chat history for a session"""
        if session_id not in self.active_sessions:
            # Create new SQLite history for this session
            self.active_sessions[session_id] = SQLiteChatMessageHistory(
                session_id=session_id,
                db_path=self.chat_config.get('db_path', 'conversations.db'),
                max_messages=self.chat_config.get('max_messages', 100)
            )
        return self.active_sessions[session_id]
    
    def add_to_conversation(self, user_message: str, ai_response: str, session_id: str = None):
        """Add a message exchange to conversation history in SQLite"""
        session_id = session_id or self.default_session_id
        
        # Get or create SQLite history for this session
        sqlite_history = self._get_session_history(session_id)
        
        # Add messages to SQLite (automatic limiting handled by max_messages)
        sqlite_history.add_message(HumanMessage(content=user_message))
        sqlite_history.add_message(AIMessage(content=ai_response))
        
        # Update LangChain memory if this is the active session
        if session_id == self.default_session_id:
            self.conversation_memory.save_context(
                {"input": user_message},
                {"output": ai_response}
            )
    
    def clear_conversation(self, session_id: str = None):
        """Clear conversation history for a session in SQLite"""
        session_id = session_id or self.default_session_id
        
        # Clear SQLite history for this session
        sqlite_history = self._get_session_history(session_id)
        sqlite_history.clear()
        
        # Clear LangChain memory if this is the active session
        if session_id == self.default_session_id:
            self.conversation_memory.clear()
    
    def get_messages_for_llm(self, current_prompt: str, system_message: str = None, session_id: str = None) -> List:
        """Convert conversation history to LangChain message format"""
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        # Add conversation history
        history = self.get_conversation_history(session_id)
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current user message
        messages.append(HumanMessage(content=current_prompt))
        
        return messages
        
    # Initialize tools registry 
    def _init_tools(self):
        """Initialize the tools registry"""
        # Available tools registry
        self.tools = {
            'file_reader': {
                'name': 'file_reader',
                'description': 'Read and analyze CSV or text files with optional row limiting, column filtering, and specialized tenant processing analysis',
                'handler': self._handle_file_reader,
                'parameters': {
                    'file_path': {'type': 'string', 'required': True},
                    'operation': {'type': 'string', 'default': 'read', 'choices': ['read', 'search', 'tenant_analysis']},
                    'limit': {'type': 'integer', 'required': False, 'description': 'Number of rows to read (for CSV files)'},
                    'search_term': {'type': 'string', 'required': False},
                    'delimiter': {'type': 'string', 'default': ','},
                    'encoding': {'type': 'string', 'default': 'utf-8'},
                    'tenant_format': {'type': 'boolean', 'default': False, 'description': 'Process as tenant processing CSV with file anonymization'}
                }
            },
            'dynamodb_query': {
                'name': 'dynamodb_query',
                'description': 'Query DynamoDB tables',
                'handler': self._handle_dynamodb_query,
                'parameters': {
                    'table_name': {'type': 'string', 'required': True},
                    'operation': {'type': 'string', 'required': True, 'choices': ['list_tables', 'describe', 'query', 'scan', 'get_item']},
                    'partition_key': {'type': 'string', 'required': False},
                    'partition_value': {'type': 'string', 'required': False},
                    'sort_key': {'type': 'string', 'required': False},
                    'sort_value': {'type': 'string', 'required': False},
                    'attribute_name': {'type': 'string', 'required': False},
                    'attribute_value': {'type': 'string', 'required': False},
                    'comparison': {'type': 'string', 'default': 'eq', 'choices': ['eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'contains']},
                    'limit': {'type': 'integer', 'default': 100}
                }
            },
            'llm_chat': {
                'name': 'llm_chat',
                'description': 'Generate responses using LLM model with conversation history',
                'handler': self._handle_llm_chat,
                'parameters': {
                    'prompt': {'type': 'string', 'required': True},
                    'system_message': {'type': 'string', 'required': False},
                    'max_tokens': {'type': 'integer', 'default': 1000},
                    'temperature': {'type': 'float', 'default': 0.7},
                    'session_id': {'type': 'string', 'required': False, 'description': 'Session ID for conversation context'}
                }
            },
            'scc_tool': {
                'name': 'scc_tool',
                'description': 'Query Cisco Security Cloud Control API for firewall devices with Lucene query support',
                'handler': self._handle_scc_tool,
                'parameters': {
                    'operation': {'type': 'string', 'required': True, 'choices': ['list', 'find', 'all', 'query']},
                    'limit': {'type': 'integer', 'default': 50, 'description': 'Number of devices to return (max 200)'},
                    'offset': {'type': 'integer', 'default': 0, 'description': 'Pagination offset'},
                    'search_term': {'type': 'string', 'required': False, 'description': 'Search term for finding devices (searches name, deviceType, softwareVersion, notes, uid via API; serial via local fallback)'},
                    'filter': {'type': 'string', 'required': False, 'description': 'Simple device filter for list operation'},
                    'lucene_query': {'type': 'string', 'required': False, 'description': 'Advanced Lucene query syntax (for query operation)'},
                    'max_devices': {'type': 'integer', 'default': 1000, 'description': 'Maximum devices to retrieve (for all operation)'}
                }
            },
            'rest_api': {
                'name': 'rest_api',
                'description': 'Make REST API calls to any HTTP endpoint',
                'handler': self._handle_rest_api,
                'parameters': {
                    'url': {'type': 'string', 'required': True, 'description': 'The URL to call'},
                    'operation': {'type': 'string', 'default': 'get', 'choices': ['get', 'post', 'put', 'delete', 'patch']},
                    'method': {'type': 'string', 'required': False, 'description': 'HTTP method (alternative to operation)'},
                    'headers': {'type': 'object', 'required': False, 'description': 'HTTP headers as JSON object'},
                    'params': {'type': 'object', 'required': False, 'description': 'Query parameters as JSON object'},
                    'json_data': {'type': 'object', 'required': False, 'description': 'JSON body data'},
                    'auth_token': {'type': 'string', 'required': False, 'description': 'Authentication token'},
                    'auth_type': {'type': 'string', 'default': 'Bearer', 'description': 'Authentication type (Bearer, Basic, API-Key)'},
                    'timeout': {'type': 'float', 'default': 30.0, 'description': 'Request timeout in seconds'}
                }
            },
            'sal_troubleshoot': {
                'name': 'sal_troubleshoot',
                'description': 'Troubleshoot SAL (Secure Analytics and Logging) event streaming from firewall devices',
                'handler': self._handle_sal_troubleshoot,
                'parameters': {
                    'operation': {'type': 'string', 'required': True, 'choices': ['troubleshoot_device', 'check_all_devices', 'check_device_events']},
                    'device_criteria': {'type': 'string', 'required': False, 'description': 'Device name or search criteria for troubleshooting'},
                    'device_name': {'type': 'string', 'required': False, 'description': 'Specific device name to troubleshoot (alias for device_criteria)'},
                    'device_uuid': {'type': 'string', 'required': False, 'description': 'Device UUID (uidOnFmc) for direct event checking'},
                    'stream_id': {'type': 'string', 'required': False, 'description': 'SAL stream ID (uses default from SAL_STREAM_ID if not provided)'},
                    'limit': {'type': 'integer', 'default': 50, 'description': 'Maximum number of devices to check (for check_all_devices operation)'}
                }
            }
        }
    
    async def _handle_file_reader(self, **kwargs) -> Dict[str, Any]:
        """Handle file reading operations"""
        try:
            file_path = kwargs.get('file_path')
            operation = kwargs.get('operation', 'read')
            
            if not file_path:
                return {'success': False, 'error': 'file_path is required'}
            
            # Convert to absolute path if relative
            if not Path(file_path).is_absolute():
                file_path = str(Path.cwd() / file_path)
            
            # Remove file_path and operation from kwargs to avoid duplicate arguments
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('file_path', None)
            kwargs_copy.pop('operation', None)
            
            result = self.file_reader.process_file(file_path, operation, **kwargs_copy)
            return result
            
        except Exception as e:
            logger.error(f"Error in file reader handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_dynamodb_query(self, **kwargs) -> Dict[str, Any]:
        """Handle DynamoDB query operations"""
        try:
            table_name = kwargs.get('table_name', '')
            operation = kwargs.get('operation')
            
            if not operation:
                return {'success': False, 'error': 'operation is required'}
            
            # Remove table_name and operation from kwargs to avoid duplicate arguments
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('table_name', None)
            kwargs_copy.pop('operation', None)
            
            result = self.dynamodb_tool.process_query(table_name, operation, **kwargs_copy)
            return result
            
        except Exception as e:
            logger.error(f"Error in DynamoDB handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_llm_chat(self, **kwargs) -> Dict[str, Any]:
        """Handle LLM chat operations with conversation history"""
        try:
            prompt = kwargs.get('prompt')
            if not prompt:
                return {'success': False, 'error': 'prompt is required'}
            
            system_message = kwargs.get('system_message', '')
            max_tokens = kwargs.get('max_tokens', 1000)
            temperature = kwargs.get('temperature', 0.7)
            session_id = kwargs.get('session_id', self.default_session_id)
            
            # Create fresh LLM client with updated token
            llm = self.get_llm()
            llm.temperature = temperature
            llm.max_tokens = max_tokens
            
            # Get messages with conversation history
            messages = self.get_messages_for_llm(prompt, system_message, session_id)
            
            response = llm.invoke(messages)
            
            # Save conversation history
            self.add_to_conversation(prompt, response.content, session_id)
            
            return {
                'success': True,
                'response': response.content,
                'model': llm_model,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Error in LLM chat handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_scc_tool(self, **kwargs) -> Dict[str, Any]:
        """Handle Cisco Security Cloud Control API operations"""
        try:
            operation = kwargs.get('operation')
            if not operation:
                return {'success': False, 'error': 'operation parameter is required'}
            
            # Remove operation from kwargs to avoid duplicate arguments
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('operation', None)
            
            result = await self.scc_tool.process_request(operation, **kwargs_copy)
            return result
            
        except Exception as e:
            logger.error(f"Error in SCC tool handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_rest_api(self, **kwargs) -> Dict[str, Any]:
        """Handle generic REST API operations"""
        try:
            url = kwargs.get('url')
            if not url:
                return {'success': False, 'error': 'url parameter is required'}
            
            operation = kwargs.get('operation', 'get')
            
            # Remove operation from kwargs to avoid duplicate arguments
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('operation', None)
            
            # process_request expects url in kwargs
            result = await self.rest_api_tool.process_request(operation, **kwargs_copy)
            return result
            
        except Exception as e:
            logger.error(f"Error in REST API tool handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_sal_troubleshoot(self, **kwargs) -> Dict[str, Any]:
        """Handle SAL troubleshooting operations"""
        try:
            operation = kwargs.get('operation')
            if not operation:
                return {'success': False, 'error': 'operation parameter is required'}
            
            # Remove operation from kwargs to avoid duplicate arguments
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop('operation', None)
            
            result = await self.sal_troubleshoot_tool.process_request(operation, **kwargs_copy)
            return result
            
        except Exception as e:
            logger.error(f"Error in SAL troubleshoot handler: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """Analyze user intent to determine which tool to use"""
        system_message = """
        You are an intent classifier. Analyze the user's input and determine what action they want to perform.
        
        Available actions:
        1. "file_read" - User wants to read, analyze, or search in CSV/text files
        2. "dynamodb_query" - User wants to query or search DynamoDB tables
        3. "scc_query" - User wants to query Cisco Security Cloud Control for firewall devices
        4. "rest_api" - User wants to make REST API calls to external endpoints
        5. "sal_troubleshoot" - User wants to troubleshoot SAL (Secure Analytics and Logging) event streaming from firewall devices
        6. "general_chat" - General conversation or questions not requiring specific tools
        
        Respond with ONLY a JSON object in this format:
        {
            "action": "file_read|dynamodb_query|scc_query|rest_api|sal_troubleshoot|general_chat",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
        
        Examples:
        - "Read the sales data from report.csv" -> file_read
        - "Find user with ID 12345 in user table" -> dynamodb_query
        - "List all firewall devices" -> scc_query
        - "Find firewall device named Paradise" -> scc_query
        - "Call the API endpoint https://api.example.com" -> rest_api
        - "Find firewall device Paradise and check if it's sending events to SAL" -> sal_troubleshoot
        - "Check if all devices are sending events" -> sal_troubleshoot
        - "When was last event sent for device Paradise" -> sal_troubleshoot
        - "What's the weather like?" -> general_chat
        """
        
        try:
            # Create fresh LLM client with updated token
            llm = self.get_llm()
            llm.temperature = 0.1  # Low temperature for consistent classification
            llm.max_tokens = 200
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            # Try to parse JSON response
            try:
                import json
                intent_data = json.loads(response.content)
                return {
                    'success': True,
                    'action': intent_data.get('action', 'general_chat'),
                    'confidence': intent_data.get('confidence', 0.5),
                    'reasoning': intent_data.get('reasoning', '')
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                response_text = response.content.lower()
                if any(keyword in response_text for keyword in ['file', 'csv', 'text', 'read']):
                    return {
                        'success': True,
                        'action': 'file_read',
                        'confidence': 0.7,
                        'reasoning': 'Fallback classification based on keywords'
                    }
                elif any(keyword in response_text for keyword in ['dynamodb', 'table', 'query', 'database']):
                    return {
                        'success': True,
                        'action': 'dynamodb_query',
                        'confidence': 0.7,
                        'reasoning': 'Fallback classification based on keywords'
                    }
                else:
                    return {
                        'success': True,
                        'action': 'general_chat',
                        'confidence': 0.5,
                        'reasoning': 'Fallback to general chat'
                    }
                    
        except Exception as e:
            logger.error(f"Error analyzing intent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def analyze_and_route(self, user_input: str) -> Dict[str, Any]:
        """Analyze user input and route to appropriate tool"""
        try:
            # Use LLM to analyze intent
            intent_result = await self._analyze_intent(user_input)
            
            if not intent_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to analyze intent: {intent_result.get('error', 'Unknown error')}"
                }
            
            action = intent_result.get('action', 'general_chat')
            confidence = intent_result.get('confidence', 0.0)
            reasoning = intent_result.get('reasoning', '')
            
            logger.info(f"Intent analysis: action={action}, confidence={confidence}, reasoning={reasoning}")
            
            # Route based on action
            if action == 'file_read':
                return await self._handle_file_intent(user_input, reasoning)
            elif action == 'dynamodb_query':
                return await self._handle_dynamodb_intent(user_input, reasoning)
            elif action == 'scc_query':
                return await self._handle_scc_intent(user_input, reasoning)
            elif action == 'rest_api':
                return await self._handle_rest_api_intent(user_input, reasoning)
            elif action == 'sal_troubleshoot':
                return await self._handle_sal_troubleshoot_intent(user_input, reasoning)
            else:
                # General chat - use LLM with conversation history
                return await self._handle_llm_chat(prompt=user_input, session_id=self.default_session_id)
                
        except Exception as e:
            logger.error(f"Error in analyze_and_route: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_file_intent(self, user_input: str, reasoning: str) -> Dict[str, Any]:
        """Handle file-related intents by extracting parameters and calling file tool"""
        try:
            # Use LLM to extract file operation parameters
            system_message = f"""
            The user wants to perform a file operation. Based on their input, extract the parameters needed.
            
            Reasoning from intent analysis: {reasoning}
            
            Respond with ONLY a JSON object with these fields:
            {{
                "file_path": "path to file (required)",
                "operation": "read or search",
                "limit": "number of rows to read (for CSV files, extract from phrases like 'first N records', 'top N rows', etc.)",
                "search_term": "term to search for (only if operation is search)",
                "delimiter": "delimiter for CSV files (default: ,)",
                "encoding": "file encoding (default: utf-8)",
                "columns_requested": "list of specific column names mentioned or relevant to analysis (e.g., ['Time Interval'] for time analysis)",
                "analytical_focus": "true if user is asking analytical questions about patterns, trends, frequency, etc."
            }}
            
            Examples:
            - "read first 10 records" -> {{"limit": 10}}
            - "show me top 5 rows" -> {{"limit": 5}}  
            - "give me list of order_id" -> {{"columns_requested": ["order_id"]}}
            - "Time Interval field...do you think files are processed frequently" -> {{"columns_requested": ["Time Interval"], "analytical_focus": true}}
            - "analyze processing frequency" -> {{"analytical_focus": true}}
            
            If the file path is not specified, ask the user to provide it.
            """
            
            # Create fresh LLM client for parameter extraction
            llm = self.get_llm()
            llm.temperature = 0.1
            llm.max_tokens = 300
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            try:
                import json
                params = json.loads(response.content)
                
                if not params.get('file_path'):
                    return {
                        'success': True,
                        'response': "I'd be happy to help you with file operations! Please provide the path to the file you'd like me to read or search.",
                        'action': 'file_read',
                        'needs_input': True
                    }
                
                # Call file reader tool
                file_result = await self._handle_file_reader(**params)
                
                if file_result['success']:
                    # Handle specific column requests
                    columns_requested = params.get('columns_requested')
                    processed_result = file_result.copy()
                    
                    if columns_requested and isinstance(columns_requested, list) and file_result.get('data'):
                        # Filter data to show only requested columns
                        filtered_data = []
                        available_columns = file_result.get('columns', [])
                        
                        # Case-insensitive column matching
                        matched_columns = []
                        for requested_col in columns_requested:
                            for available_col in available_columns:
                                if requested_col.lower().replace('_', ' ') in available_col.lower().replace('_', ' ') or \
                                   available_col.lower().replace('_', ' ') in requested_col.lower().replace('_', ' '):
                                    matched_columns.append(available_col)
                                    break
                        
                        if matched_columns:
                            for record in file_result['data']:
                                filtered_record = {col: record.get(col) for col in matched_columns}
                                filtered_data.append(filtered_record)
                            
                            processed_result['data'] = filtered_data
                            processed_result['columns_shown'] = matched_columns
                            processed_result['filtered'] = True
                    
                    # Format response using LLM with analytical context
                    context_message = f"File operation completed. Here's the result: {json.dumps(processed_result, indent=2)}"
                    
                    format_llm = self.get_llm()
                    format_llm.temperature = 0.3
                    format_llm.max_tokens = 1000
                    
                    additional_context = ""
                    if columns_requested:
                        additional_context = f"\n\nUser specifically requested columns: {columns_requested}. Focus on presenting these columns clearly."
                    
                    # Enhanced analytical context
                    analytical_focus = params.get('analytical_focus', False)
                    if analytical_focus:
                        analytical_context = f"\n\nORIGINAL USER QUESTION: '{user_input}'\n\nIMPORTANT: This is an analytical question. The user wants data analysis, not just a data summary. Please:\n1. First show the relevant data\n2. Then provide detailed analysis answering their specific question\n3. Look for patterns, trends, frequencies, or insights\n4. Give specific conclusions based on the data"
                    else:
                        analytical_context = f"\n\nOriginal user question: '{user_input}'\n\nIf the user asked an analytical question (like trends, patterns, frequency analysis, etc.), provide detailed analysis based on the data."
                    
                    format_messages = [
                        SystemMessage(content=f"You are a data analyst assistant. Present file operation results clearly and answer any analytical questions based on the data.{additional_context}{analytical_context}"),
                        HumanMessage(content=f"Based on this file data, please provide a comprehensive response to the user's request: {context_message}")
                    ]
                    
                    format_response = format_llm.invoke(format_messages)
                    
                    # Save conversation history for file operations
                    self.add_to_conversation(user_input, format_response.content, self.default_session_id)
                    
                    return {
                        'success': True,
                        'response': format_response.content,
                        'raw_data': processed_result,
                        'action': 'file_read'
                    }
                else:
                    return file_result
                    
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse file operation parameters'
                }
                
        except Exception as e:
            logger.error(f"Error handling file intent: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_dynamodb_intent(self, user_input: str, reasoning: str) -> Dict[str, Any]:
        """Handle DynamoDB-related intents by extracting parameters and calling DDB tool"""
        try:
            # Use LLM to extract DynamoDB operation parameters
            system_message = f"""
            The user wants to perform a DynamoDB operation. Based on their input, extract the parameters needed.
            
            Reasoning from intent analysis: {reasoning}
            
            Respond with ONLY a JSON object with these fields:
            {{
                "table_name": "name of the table",
                "operation": "list_tables|describe|query|scan|get_item",
                "partition_key": "partition key name (for query/get_item)",
                "partition_value": "partition key value (for query/get_item)",
                "sort_key": "sort key name (optional for query)",
                "sort_value": "sort key value (optional for query)",
                "attribute_name": "attribute name (for scan)",
                "attribute_value": "attribute value (for scan)",
                "comparison": "eq|ne|lt|lte|gt|gte|contains (default: eq)",
                "limit": 100
            }}
            
            If the table name is not specified, suggest using "list_tables" operation first.
            """
            
            # Create fresh LLM client for parameter extraction
            llm = self.get_llm()
            llm.temperature = 0.1
            llm.max_tokens = 300
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            try:
                import json
                params = json.loads(response.content)
                
                # If no table name and not listing tables, suggest listing first
                if not params.get('table_name') and params.get('operation') != 'list_tables':
                    params['operation'] = 'list_tables'
                    params['table_name'] = ''
                
                # Call DynamoDB tool
                ddb_result = await self._handle_dynamodb_query(**params)
                
                if ddb_result['success']:
                    # Format response using LLM with analytical context
                    context_message = f"DynamoDB operation completed. Here's the result: {json.dumps(ddb_result, indent=2)}"
                    
                    format_llm = self.get_llm()
                    format_llm.temperature = 0.3
                    format_llm.max_tokens = 800
                    
                    # Preserve analytical context for DynamoDB queries too
                    analytical_context = f"\n\nOriginal user question: '{user_input}'\n\nIf the user asked an analytical question about the database data (like patterns, trends, counts, etc.), provide detailed analysis based on the query results."
                    
                    format_messages = [
                        SystemMessage(content=f"You are a data analyst assistant. Present DynamoDB operation results clearly and answer any analytical questions based on the data.{analytical_context}"),
                        HumanMessage(content=f"Based on this database query result, please provide a comprehensive response to the user's request: {context_message}")
                    ]
                    
                    format_response = format_llm.invoke(format_messages)
                    
                    # Save conversation history for DynamoDB operations
                    self.add_to_conversation(user_input, format_response.content, self.default_session_id)
                    
                    return {
                        'success': True,
                        'response': format_response.content,
                        'raw_data': ddb_result,
                        'action': 'dynamodb_query'
                    }
                else:
                    return ddb_result
                    
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse DynamoDB operation parameters'
                }
                
        except Exception as e:
            logger.error(f"Error handling DynamoDB intent: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_scc_intent(self, user_input: str, reasoning: str) -> Dict[str, Any]:
        """Handle SCC-related intents by extracting parameters and calling SCC tool"""
        try:
            # Use LLM to extract SCC operation parameters
            system_message = f"""
            The user wants to interact with Cisco Security Cloud Control API. Based on their input, extract the parameters needed.
            
            Reasoning from intent analysis: {reasoning}
            
            Respond with ONLY a JSON object with these fields:
            {{
                "operation": "list|find|all|query - list (paginated), find (search by name/serial/type), all (get all devices), query (advanced Lucene syntax)",
                "search_term": "term to search for device by name, deviceType, softwareVersion, notes, or uid (for find operation). Serial search uses local fallback.",
                "limit": "number of devices to return (default: 50, max: 200)",
                "offset": "pagination offset (default: 0)",
                "max_devices": "maximum devices to retrieve for all operation (default: 1000)",
                "lucene_query": "advanced Lucene query syntax like 'name:Paradise' or 'deviceType:CDFMC_MANAGED_FTD' (for query operation)"
            }}
            
            Examples:
            - "list all firewall devices" -> {{"operation": "list"}}
            - "find firewall device named Paradise" -> {{"operation": "find", "search_term": "Paradise"}}
            - "get all devices" -> {{"operation": "all"}}
            - "show me first 10 devices" -> {{"operation": "list", "limit": 10}}
            - "find devices with FTD type" -> {{"operation": "query", "lucene_query": "deviceType:CDFMC_MANAGED_FTD"}}
            - "devices in ONLINE state" -> {{"operation": "query", "lucene_query": "connectivityState:ONLINE"}}
            """
            
            # Create fresh LLM client for parameter extraction
            llm = self.get_llm()
            llm.temperature = 0.1
            llm.max_tokens = 300
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            try:
                import json
                params = json.loads(response.content)
                
                # Call SCC tool
                scc_result = await self._handle_scc_tool(**params)
                
                if scc_result['success']:
                    # Format response using LLM with analytical context
                    context_message = f"SCC API operation completed. Here's the result: {json.dumps(scc_result, indent=2)}"
                    
                    format_llm = self.get_llm()
                    format_llm.temperature = 0.3
                    format_llm.max_tokens = 1200  # Increased to accommodate detailed device info including uidOnFmc
                    
                    # Preserve analytical context for SCC queries
                    analytical_context = f"\n\nOriginal user question: '{user_input}'\n\nPresent the firewall device information clearly. If the user asked for specific devices or analysis, focus on that."
                    
                    format_messages = [
                        SystemMessage(content=f"You are a network security assistant. Present SCC firewall device information clearly and answer any questions about the devices. IMPORTANT: Always include these key device identifiers in your response: name, uid, uidOnFmc, deviceType, serial, softwareVersion, connectivityState, and configState. The uidOnFmc field is especially important for FMC integration and should always be displayed.{analytical_context}"),
                        HumanMessage(content=f"Based on this SCC API result, please provide a comprehensive response to the user's request: {context_message}")
                    ]
                    
                    format_response = format_llm.invoke(format_messages)
                    
                    # Save conversation history for SCC operations
                    self.add_to_conversation(user_input, format_response.content, self.default_session_id)
                    
                    return {
                        'success': True,
                        'response': format_response.content,
                        'raw_data': scc_result,
                        'action': 'scc_query'
                    }
                else:
                    return scc_result
                    
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse SCC operation parameters'
                }
                
        except Exception as e:
            logger.error(f"Error handling SCC intent: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_rest_api_intent(self, user_input: str, reasoning: str) -> Dict[str, Any]:
        """Handle REST API intents by extracting parameters and calling REST API tool"""
        try:
            # Use LLM to extract REST API parameters
            system_message = f"""
            The user wants to make a REST API call. Based on their input, extract the parameters needed.
            
            Reasoning from intent analysis: {reasoning}
            
            Respond with ONLY a JSON object with these fields:
            {{
                "url": "the complete URL to call (required)",
                "operation": "get|post|put|delete|patch (default: get)",
                "headers": "additional headers as JSON object (optional)",
                "params": "query parameters as JSON object (optional)",
                "json_data": "JSON body data for POST/PUT requests (optional)",
                "auth_type": "Bearer|Basic|API-Key (default: Bearer)",
                "timeout": "request timeout in seconds (default: 30)"
            }}
            
            Examples:
            - "Call https://api.example.com/users" -> {{"url": "https://api.example.com/users", "operation": "get"}}
            - "POST to https://api.example.com/data with JSON" -> {{"url": "https://api.example.com/data", "operation": "post"}}
            - "Get data from API with limit=10" -> needs URL but can include {{"params": {{"limit": 10}}}}
            
            If no URL is specified, ask the user to provide it.
            """
            
            # Create fresh LLM client for parameter extraction
            llm = self.get_llm()
            llm.temperature = 0.1
            llm.max_tokens = 300
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            try:
                import json
                params = json.loads(response.content)
                
                if not params.get('url'):
                    return {
                        'success': True,
                        'response': "I'd be happy to help you make a REST API call! Please provide the URL you'd like me to call.",
                        'action': 'rest_api',
                        'needs_input': True
                    }
                
                # Call REST API tool
                api_result = await self._handle_rest_api(**params)
                
                if api_result['success']:
                    # Format response using LLM with analytical context
                    context_message = f"REST API call completed. Here's the result: {json.dumps(api_result, indent=2)}"
                    
                    format_llm = self.get_llm()
                    format_llm.temperature = 0.3
                    format_llm.max_tokens = 800
                    
                    # Preserve analytical context for API responses
                    analytical_context = f"\n\nOriginal user question: '{user_input}'\n\nPresent the API response data clearly. If the user asked for specific analysis or information, focus on that."
                    
                    format_messages = [
                        SystemMessage(content=f"You are a helpful API assistant. Present REST API response data clearly and answer any questions about the results.{analytical_context}"),
                        HumanMessage(content=f"Based on this API response, please provide a comprehensive response to the user's request: {context_message}")
                    ]
                    
                    format_response = format_llm.invoke(format_messages)
                    
                    # Save conversation history for REST API operations
                    self.add_to_conversation(user_input, format_response.content, self.default_session_id)
                    
                    return {
                        'success': True,
                        'response': format_response.content,
                        'raw_data': api_result,
                        'action': 'rest_api'
                    }
                else:
                    return api_result
                    
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse REST API operation parameters'
                }
                
        except Exception as e:
            logger.error(f"Error handling REST API intent: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_sal_troubleshoot_intent(self, user_input: str, reasoning: str) -> Dict[str, Any]:
        """Handle SAL troubleshooting intents by extracting parameters and calling SAL troubleshoot tool"""
        try:
            # Use LLM to extract SAL troubleshooting parameters
            system_message = f"""
            The user wants to troubleshoot SAL (Secure Analytics and Logging) event streaming from firewall devices. Based on their input, extract the parameters needed.
            
            Reasoning from intent analysis: {reasoning}
            
            Respond with ONLY a JSON object with these fields:
            {{
                "operation": "troubleshoot_device|check_all_devices|check_device_events - troubleshoot_device (find device and check events), check_all_devices (check all devices), check_device_events (direct device UUID check)",
                "device_criteria": "device name or search criteria to find in SCC (for troubleshoot_device)",
                "device_uuid": "specific device UUID/uidOnFmc for direct checking (for check_device_events)",
                "stream_id": "SAL stream ID - leave empty to use default from environment",
                "limit": "maximum devices to check for check_all_devices operation (default: 50)"
            }}
            
            Examples:
            - "Find firewall device Paradise and check if it's sending events to SAL" -> {{"operation": "troubleshoot_device", "device_criteria": "Paradise"}}
            - "Check if all devices are sending events" -> {{"operation": "check_all_devices"}}
            - "When was last event sent for device Paradise" -> {{"operation": "troubleshoot_device", "device_criteria": "Paradise"}}
            - "Check events for device with UUID abc123" -> {{"operation": "check_device_events", "device_uuid": "abc123"}}
            - "Check SAL event status for all devices in stream xyz" -> {{"operation": "check_all_devices", "stream_id": "xyz"}}
            """
            
            # Create fresh LLM client for parameter extraction
            llm = self.get_llm()
            llm.temperature = 0.1
            llm.max_tokens = 300
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
            
            response = llm.invoke(messages)
            
            try:
                import json
                params = json.loads(response.content)
                
                # Call SAL troubleshoot tool
                sal_result = await self._handle_sal_troubleshoot(**params)
                
                if sal_result['success']:
                    # Format response using LLM with analytical context
                    context_message = f"SAL troubleshooting completed. Here's the result: {json.dumps(sal_result, indent=2)}"
                    
                    format_llm = self.get_llm()
                    format_llm.temperature = 0.3
                    format_llm.max_tokens = 1000  # More space for troubleshooting details
                    
                    # Preserve analytical context for SAL troubleshooting
                    analytical_context = f"\n\nOriginal user question: '{user_input}'\n\nPresent the SAL troubleshooting results clearly. Focus on device status, event streaming health, and provide actionable troubleshooting guidance. If devices are not sending recent events, explain what this means and suggest next steps."
                    
                    format_messages = [
                        SystemMessage(content=f"You are a network security troubleshooting assistant specializing in SAL (Secure Analytics and Logging) event streaming. Present troubleshooting results clearly with device status, event timing analysis, and actionable recommendations. Always explain what the timestamps and status mean in practical terms.{analytical_context}"),
                        HumanMessage(content=f"Based on this SAL troubleshooting result, please provide a comprehensive response to the user's request: {context_message}")
                    ]
                    
                    format_response = format_llm.invoke(format_messages)
                    
                    # Save conversation history for SAL troubleshooting
                    self.add_to_conversation(user_input, format_response.content, self.default_session_id)
                    
                    return {
                        'success': True,
                        'response': format_response.content,
                        'raw_data': sal_result,
                        'action': 'sal_troubleshoot'
                    }
                else:
                    return sal_result
                    
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse SAL troubleshooting parameters'
                }
                
        except Exception as e:
            logger.error(f"Error handling SAL troubleshoot intent: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools and their descriptions"""
        return {
            'success': True,
            'tools': [
                {
                    'name': tool_info['name'],
                    'description': tool_info['description'],
                    'parameters': tool_info['parameters']
                }
                for tool_info in self.tools.values()
            ]
        }
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a specific tool directly"""
        if tool_name not in self.tools:
            return {
                'success': False,
                'error': f'Tool {tool_name} not found. Available tools: {list(self.tools.keys())}'
            }
        
        try:
            handler = self.tools[tool_name]['handler']
            result = await handler(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_conversation_summary(self, session_id: str = None) -> Dict[str, Any]:
        """Get conversation summary statistics from SQLite"""
        session_id = session_id or self.default_session_id
        
        # Get SQLite statistics
        sqlite_history = self._get_session_history(session_id)
        stats = sqlite_history.get_session_stats()
        
        history = self.get_conversation_history(session_id)
        message_count = len(history)
        exchange_count = message_count // 2
        
        # Get last few messages for preview
        last_messages = history[-6:] if len(history) > 6 else history
        
        return {
            'session_id': session_id,
            'message_count': message_count,
            'exchange_count': exchange_count,
            'has_history': message_count > 0,
            'last_messages': last_messages,
            'database_stats': stats,
            'database_path': self.chat_config.get('db_path', 'conversations.db'),
            'max_messages': self.chat_config.get('max_messages', 100),
            'persistent_storage': True
        }
    
    def list_conversation_sessions(self) -> List[str]:
        """List all available conversation sessions"""
        return SQLiteChatMessageHistory.list_sessions(
            self.chat_config.get('db_path', 'conversations.db')
        )
    
    def switch_session(self, session_id: str):
        """Switch to a different conversation session"""
        self.default_session_id = session_id
        
        # Update the main conversation memory to use the new session
        sqlite_history = self._get_session_history(session_id)
        self.conversation_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            chat_memory=sqlite_history,
            input_key="input",
            output_key="output"
        )
        
        return f"Switched to session: {session_id}"
    
    def delete_session(self, session_id: str):
        """Delete a conversation session"""
        if session_id == self.default_session_id:
            raise ValueError("Cannot delete the currently active session")
        
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Delete from database
        SQLiteChatMessageHistory.delete_session(
            session_id, 
            self.chat_config.get('db_path', 'conversations.db')
        )
        
        return f"Deleted session: {session_id}"
    
    async def create_prompt_with_history(self, user_input: str, system_template: str = None) -> ChatPromptTemplate:
        """Create a ChatPromptTemplate with MessagesPlaceholder for conversation history"""
        
        # Default system template
        if not system_template:
            system_template = """You are a helpful AI assistant with access to various tools for file operations, database queries, and general conversation. 
            You maintain context from previous conversations to provide better assistance."""
        
        # Create prompt template with MessagesPlaceholder
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}")
        ])
        
        return prompt_template
    
    async def chat_with_memory_chain(self, user_input: str, system_template: str = None, session_id: str = None) -> Dict[str, Any]:
        """Example of using ChatPromptTemplate with MessagesPlaceholder for conversation memory"""
        try:
            session_id = session_id or self.default_session_id
            
            # Create prompt template with MessagesPlaceholder
            prompt_template = await self.create_prompt_with_history(user_input, system_template)
            
            # Get LLM
            llm = self.get_llm()
            
            # Get chat history in the format expected by MessagesPlaceholder
            memory_variables = self.conversation_memory.load_memory_variables({})
            chat_history = memory_variables.get('chat_history', [])
            
            # Create the chain
            chain = prompt_template | llm
            
            # Invoke the chain with history
            response = chain.invoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            # Save to memory
            self.conversation_memory.save_context(
                {"input": user_input},
                {"output": response.content}
            )
            
            # Also save to our custom storage
            self.add_to_conversation(user_input, response.content, session_id)
            
            return {
                'success': True,
                'response': response.content,
                'model': llm_model,
                'session_id': session_id,
                'method': 'MessagesPlaceholder'
            }
            
        except Exception as e:
            logger.error(f"Error in chat with memory chain: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Cleanup resources"""
        # No cleanup needed for AzureChatOpenAI - it handles its own session management
        logger.info("MCP Server closed successfully")
