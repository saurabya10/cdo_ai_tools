# LLM Tool Orchestrator

An intelligent system that combines Large Language Models (LLM) with specialized tools for file processing and database queries using the Model Context Protocol (MCP). The system automatically routes user requests to the appropriate tool based on intent analysis.

## 🎯 Overview

This project provides a unified interface for:

1. **🤖 LLM Integration** - Interact with company-hosted Large Language Models
2. **📁 File Operations** - Read, analyze, and search CSV/text files
3. **🗃️ DynamoDB Queries** - Query AWS DynamoDB tables with natural language
4. **🧠 Intelligent Routing** - Automatic tool selection based on user intent

The system uses LangChain/LangGraph for orchestration and implements an MCP (Model Context Protocol) server for tool management.

## 🏗️ Architecture

```
User Input → Intent Analysis (AzureChatOpenAI) → Tool Router → Specific Tool → Formatted Response
                                                           ↓
                                                   [File Reader | DynamoDB | LLM Chat]
```

### Key Components

- **MCP Server** (`mcp_server.py`) - Central orchestrator with AzureChatOpenAI integration
- **Settings** (`settings.py`) - Cisco OAuth2 authentication for Azure OpenAI
- **File Reader Tool** (`tools/file_reader.py`) - CSV and text file processing
- **DynamoDB Tool** (`tools/dynamodb_tool.py`) - AWS DynamoDB operations
- **Main Application** (`main.py`) - CLI interface and application entry point

### LLM Integration

The system uses **AzureChatOpenAI** from LangChain with:
- ✅ **Cisco OAuth2 Authentication** - Automatic token management via `settings.py`
- ✅ **Azure OpenAI Endpoint** - Company-hosted LLM model support  
- ✅ **Intelligent Token Refresh** - Fresh tokens for each request
- ✅ **Production-Ready Client** - Battle-tested LangChain integration

### 🔌 API Integration Tools

- **🔥 SCCTool** (`tools/scc_tool.py`) - Cisco Security Cloud Control API for firewall devices
- **🌐 REST API Tool** (`tools/rest_api_tool.py`) - Generic REST API client for any HTTP endpoint

### 📊 Sample Data Included

The project includes `sales_report.csv` with 30 sample sales records for testing:
- **Order Information**: Date, Order ID, Customer details
- **Product Data**: Names, categories, prices, quantities  
- **Sales Metrics**: Revenue, regions, payment methods
- **Status Tracking**: Completed, Processing, Cancelled orders

Perfect for testing queries like:
- `"Read the data from sales_report.csv"`
- `"Show me all electronics orders"`
- `"Find orders over $500"`

### 🔥 SCC API Queries

Test Cisco Security Cloud Control queries:
- `"List all firewall devices"`
- `"Find firewall device named Paradise"`
- `"Show me devices with FTD licenses"`
- `"Get all firewall devices and their software versions"`

### 🌐 REST API Calls

Test generic API integrations:
- `"Call https://api.github.com to get GitHub API info"`
- `"Make a GET request to https://jsonplaceholder.typicode.com/posts with limit 5"`
- `"POST data to my API endpoint"`

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (Python 3.12+ recommended)
- AWS credentials configured (for DynamoDB access)  
- Company LLM credentials (APP_KEY, CLIENT_ID, CLIENT_SECRET)

### Installation

1. **Verify Python 3 installation:**
   ```bash
   python3 --version  # Should show Python 3.8+
   ```

2. **Install dependencies:**
   ```bash
   cd /path/to/your/project
   pip3 install -r requirements.txt
   ```
   
   **Note:** Use `pip3` and `python3` commands (not `pip` or `python`) to ensure Python 3 compatibility.

2. **Configure environment variables:**
   ```bash
   cp env.template .env
   # Edit .env file with your credentials
   ```

3. **Set AWS credentials** (one of the following methods):
   ```bash
   # Method 1: Export environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key  
   export AWS_REGION=us-east-1
   
   # Method 2: Use AWS CLI
   aws configure
   
   # Method 3: Use IAM roles (if running on EC2)
   ```

4. **Test the installation:**
   ```bash
   python3 test_installation.py
   ```
   This script will verify that all components are properly installed and configured.

5. **Run the application:**
   ```bash
   # Interactive mode
   python3 main.py interactive
   
   # Single request mode
   python3 main.py process "Read data from sales.csv"
   
   # List available tools
   python3 main.py list-tools
   ```

## 📖 Usage Examples

### Interactive Mode

Start an interactive session where you can chat naturally:

```bash
python3 main.py interactive
```

Example interactions:
- `"Read the sales data from reports/Q1_sales.csv"`
- `"Find user with ID 12345 in users table"`  
- `"Search for 'ERROR' in system.log"`
- `"What are all the available DynamoDB tables?"`
- `"Explain the difference between SQL and NoSQL"`

### Single Request Mode

Process one request and exit:

```bash
python3 main.py process "Show me all DynamoDB tables"
python3 main.py process "Analyze data/customer_feedback.csv" --verbose
```

### Direct Tool Calling

Call specific tools directly with JSON parameters:

```bash
# File operations
python3 main.py call-tool file_reader '{"file_path": "data.csv", "operation": "read"}'

# DynamoDB operations  
python3 main.py call-tool dynamodb_query '{"table_name": "users", "operation": "describe"}'

# LLM chat
python3 main.py call-tool llm_chat '{"prompt": "Explain machine learning"}'
```

## 🛠️ Available Tools

### 1. File Reader Tool

**Purpose:** Read and analyze CSV and text files

**Operations:**
- `read` - Read entire file content with analysis
- `search` - Search for specific terms within files

**Supported formats:** `.csv`, `.txt`, `.tsv`, `.json`

**Parameters:**
- `file_path` (required) - Path to the file
- `operation` (optional) - "read" or "search" 
- `search_term` (optional) - Term to search for
- `delimiter` (optional) - CSV delimiter (default: ",")
- `encoding` (optional) - File encoding (default: "utf-8")

### 2. DynamoDB Tool

**Purpose:** Query and interact with AWS DynamoDB tables

**Operations:**
- `list_tables` - Show all available tables
- `describe` - Get table schema and metadata
- `query` - Query by partition/sort keys
- `scan` - Scan with filter conditions
- `get_item` - Get single item by primary key

**Parameters:**
- `table_name` (required) - Name of the DynamoDB table
- `operation` (required) - Type of operation
- `partition_key` (optional) - Partition key name
- `partition_value` (optional) - Partition key value
- `sort_key` (optional) - Sort key name  
- `sort_value` (optional) - Sort key value
- `attribute_name` (optional) - Attribute for scan operations
- `attribute_value` (optional) - Value for scan operations
- `comparison` (optional) - Comparison operator (eq, ne, lt, etc.)
- `limit` (optional) - Maximum items to return

### 3. SCCTool (Cisco Security Cloud Control)

**Purpose:** Query Cisco Security Cloud Control API for firewall device inventory

**Operations:**
- `list` - Get paginated list of firewall devices
- `find` - Search for specific devices by name, serial, or type
- `all` - Retrieve all devices with automatic pagination

**Key Fields Extracted:**
- `name`, `uid`, `uidOnFmc`, `deviceType`, `serial`
- `softwareVersion`, `ftdLicenses`, `connectivityState`, `configState`

**Parameters:**
- `operation` (required) - "list", "find", or "all"
- `search_term` (optional) - Term to search for devices (for find operation)
- `limit` (optional) - Number of devices to return (default: 50)
- `offset` (optional) - Pagination offset (default: 0)
- `max_devices` (optional) - Maximum devices for "all" operation (default: 1000)

**Configuration:** Requires `SCC_BEARER_TOKEN` in `.env` file

### 4. REST API Tool

**Purpose:** Make HTTP requests to any REST API endpoint

**Supported Methods:** GET, POST, PUT, DELETE, PATCH

**Parameters:**
- `url` (required) - The endpoint URL to call
- `operation` (optional) - HTTP method (default: "get")
- `headers` (optional) - Additional HTTP headers as JSON object
- `params` (optional) - Query parameters as JSON object
- `json_data` (optional) - JSON body data for POST/PUT requests
- `auth_token` (optional) - Authentication token
- `auth_type` (optional) - Authentication type (Bearer, Basic, API-Key, default: Bearer)
- `timeout` (optional) - Request timeout in seconds (default: 30)

**Features:**
- Automatic JSON parsing
- Bearer/Basic/API-Key authentication
- Comprehensive error handling
- Request/response metadata

### 5. LLM Chat Tool

**Purpose:** Generate responses using the company-hosted LLM model

**Parameters:**
- `prompt` (required) - Input text for the LLM
- `system_message` (optional) - System context message
- `max_tokens` (optional) - Maximum response length (default: 1000)
- `temperature` (optional) - Response creativity (default: 0.7)

### 6. SAL Troubleshooting Tool 🆕

**Purpose:** Troubleshoot SAL (Secure Analytics and Logging) event streaming from firewall devices

**Multi-Step Workflow:**
1. **Device Discovery** - Find firewall devices using SCC tool
2. **Stream ID Resolution** - Use provided, prompted, or default stream ID  
3. **Event Tracking** - Query DynamoDB for last event timestamps
4. **Analysis & Recommendations** - Provide actionable troubleshooting insights

**Operations:**
- `troubleshoot_device` - Find specific device and check SAL event status
- `check_all_devices` - Health check for all firewall devices
- `check_device_events` - Direct device UUID event checking

**Parameters:**
- `operation` (required) - troubleshoot_device | check_all_devices | check_device_events
- `device_criteria` (optional) - Device name or search criteria  
- `device_uuid` (optional) - Specific device UUID (uidOnFmc)
- `stream_id` (optional) - SAL stream ID (uses SAL_STREAM_ID default)
- `limit` (optional) - Maximum devices to check (default: 50)

**Key Features:**
- ⏰ **Time-based Analysis** - Identifies recent vs stale events (15-minute threshold)
- 🔍 **Root Cause Analysis** - Distinguishes between connectivity, configuration, and data issues
- 📊 **Health Metrics** - Overall system health percentage and device statistics
- 🛠️ **Actionable Recommendations** - Specific troubleshooting guidance based on device status
- ⚡ **Efficient Queries** - Uses DynamoDB partition+sort key for optimal performance

**Required Configuration:**
```bash
# .env file - SAL troubleshooting specific
SAL_STREAM_ID=your_default_sal_stream_id_here
LAST_EVENT_TRACKING_TABLE_PER_DEVICE=your_table_name_here
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `env.template`:

```bash
# LLM Model Configuration
APP_KEY=your_app_key_here
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
LLM_ENDPOINT=https://your-company-llm-endpoint.com/api/v1

# Cisco Security Cloud Control API
SCC_BEARER_TOKEN=your_scc_bearer_token_here

# SAL (Secure Analytics and Logging) Configuration
SAL_STREAM_ID=your_default_sal_stream_id_here
LAST_EVENT_TRACKING_TABLE_PER_DEVICE=your_last_event_tracking_table_name_here

# Generic REST API Token (optional)
REST_API_TOKEN=your_generic_api_token_here

# AWS Configuration (optional - can use AWS CLI/IAM roles)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
DYNAMODB_REGION=us-east-2

# Application Settings
MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
```

### Logging

The application logs to both console and `app.log` file. Log levels can be configured via the `LOG_LEVEL` environment variable.

## 🔄 How It Works

1. **Intent Analysis:** User input is analyzed by the LLM to determine intent (file operation, database query, or general chat)

2. **Parameter Extraction:** Based on the intent, the system extracts relevant parameters from the user's natural language input

3. **Tool Routing:** The appropriate tool is called with the extracted parameters

4. **Response Formatting:** Results are formatted into user-friendly responses using the LLM

5. **Output:** Final response is presented to the user with optional raw data

## 🏗️ Project Structure

```
cursor_ai/
├── main.py                 # Main application entry point
├── mcp_server.py          # MCP server with tool orchestration
├── requirements.txt       # Python dependencies
├── env.template          # Environment variables template
├── app.log               # Application logs
├── README.md             # This file
├── llm/
│   └── client.py         # LLM client implementation
└── tools/
    ├── file_reader.py    # File reading and analysis tool
    └── dynamodb_tool.py  # DynamoDB querying tool
```

## 🔧 Development

### Adding New Tools

1. Create a new tool file in the `tools/` directory
2. Implement the tool class with required methods
3. Register the tool in `mcp_server.py` tools registry
4. Add intent handling logic if needed

### Extending LLM Capabilities

The LLM client supports:
- Custom system messages
- Configurable temperature and token limits  
- Automatic token refresh
- Error handling and retries

### Testing

Test individual components:

```bash
# Test file operations
python3 -c "
import asyncio
from tools.file_reader import FileReaderTool
tool = FileReaderTool()
result = tool.process_file('test.csv', 'read')
print(result)
"

# Test DynamoDB operations  
python3 -c "
from tools.dynamodb_tool import DynamoDBTool
tool = DynamoDBTool()
result = tool.process_query('', 'list_tables')
print(result)
"
```

## 📋 Requirements

The project uses the following key dependencies:

- `langchain>=0.2.0` - LLM orchestration framework
- `langgraph>=0.2.0` - Graph-based LLM workflows  
- `langchain-openai>=0.2.0` - AzureChatOpenAI integration
- `boto3>=1.34.0` - AWS SDK for DynamoDB
- `pandas>=2.0.0` - Data manipulation for CSV files
- `httpx>=0.25.0` - HTTP client for async operations
- `click>=8.0.0` - CLI interface framework
- `python-dotenv>=1.0.0` - Environment variable management
- `requests>=2.25.0` - HTTP requests for OAuth2 authentication
- `certifi>=2021.0.0` - SSL certificate verification

## ⚠️ Important Notes

1. **Credentials Security:** Never commit `.env` files to version control
2. **AWS Costs:** DynamoDB operations may incur charges based on usage
3. **LLM Rate Limits:** Respect your company's LLM API rate limits
4. **File Paths:** Use absolute paths when possible for reliability
5. **Error Handling:** The system includes comprehensive error handling, but always validate inputs

## 🤝 Contributing

1. Follow the existing code style and commenting patterns
2. Add single-line comments for all methods and functionality
3. Update this README when adding new features
4. Test new functionality thoroughly before submitting

## 📄 License

This project is for internal company use. Please ensure compliance with company policies regarding LLM usage and data handling.

---

*Built with ❤️ using LangChain, MCP, and Python*
