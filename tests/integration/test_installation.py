#!/usr/bin/env python3
"""
Installation test script for LLM Tool Orchestrator
Run this script to verify that all components are properly installed
"""
import sys
import os

def test_python_version():
    """Test Python version compatibility"""
    print("🔍 Checking Python version...")
    if sys.version_info < (3, 8):
        print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} detected. Python 3.8+ required.")
        return False
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - Compatible!")
        return True

def test_imports():
    """Test that all required packages can be imported"""
    print("\n🔍 Testing package imports...")
    
    required_packages = [
        ("langchain", "LangChain framework"),
        ("langgraph", "LangGraph framework"),
        ("boto3", "AWS SDK"),
        ("pandas", "Data manipulation"),
        ("httpx", "HTTP client"),
        ("click", "CLI framework"),
        ("dotenv", "Environment variables")
    ]
    
    all_good = True
    for package, description in required_packages:
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print(f"✅ {package:12} - {description}")
        except ImportError as e:
            print(f"❌ {package:12} - Missing! Error: {e}")
            all_good = False
    
    return all_good

def test_project_structure():
    """Test that all project files exist"""
    print("\n🔍 Checking project structure...")
    
    required_files = [
        ("main.py", "Main application"),
        ("mcp_server.py", "MCP server"),
        ("env.template", "Environment template"),
        ("tools/file_reader.py", "File reader tool"),
        ("tools/dynamodb_tool.py", "DynamoDB tool"),
        ("llm/client.py", "LLM client")
    ]
    
    all_good = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path:20} - {description}")
        else:
            print(f"❌ {file_path:20} - Missing!")
            all_good = False
    
    return all_good

def test_tool_initialization():
    """Test that tools can be initialized"""
    print("\n🔍 Testing tool initialization...")
    
    try:
        from tools.file_reader import FileReaderTool
        file_tool = FileReaderTool()
        print("✅ File Reader Tool - Initialized successfully")
    except Exception as e:
        print(f"❌ File Reader Tool - Error: {e}")
        return False
    
    try:
        from tools.dynamodb_tool import DynamoDBTool
        ddb_tool = DynamoDBTool()
        print("✅ DynamoDB Tool - Initialized successfully")
    except Exception as e:
        print(f"❌ DynamoDB Tool - Error: {e}")
        return False
    
    try:
        from llm.client import LLMClient, LLMConfig
        config = LLMConfig(
            app_key="test",
            client_id="test", 
            client_secret="test",
            endpoint="https://test.com"
        )
        llm_client = LLMClient(config)
        print("✅ LLM Client - Initialized successfully")
    except Exception as e:
        print(f"❌ LLM Client - Error: {e}")
        return False
    
    return True

def test_environment_setup():
    """Test environment configuration"""
    print("\n🔍 Checking environment setup...")
    
    if os.path.exists(".env"):
        print("✅ .env file exists")
        
        # Check if key variables are set
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ["APP_KEY", "CLIENT_ID", "CLIENT_SECRET"]
        missing_vars = []
        set_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.strip() == "" or "your_" in value.lower():
                missing_vars.append(var)
            else:
                set_vars.append(var)
        
        if set_vars:
            print(f"✅ Configured variables: {', '.join(set_vars)}")
        
        if missing_vars:
            print(f"⚠️  Missing/unconfigured variables: {', '.join(missing_vars)}")
            print("   Please configure these in your .env file")
        else:
            print("✅ All required environment variables are properly configured")
            
    else:
        print("⚠️  .env file not found")
        print("   Copy env.template to .env and configure your credentials")

def main():
    """Run all installation tests"""
    print("🚀 LLM Tool Orchestrator - Installation Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", test_python_version),
        ("Package Imports", test_imports),
        ("Project Structure", test_project_structure),
        ("Tool Initialization", test_tool_initialization)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        if not test_func():
            all_passed = False
    
    # Environment setup (warning only)
    test_environment_setup()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your installation is ready.")
        print("\nNext steps:")
        print("1. Configure your .env file with credentials")
        print("2. Set up AWS credentials for DynamoDB access")
        print("3. Run: python3 main.py interactive")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
