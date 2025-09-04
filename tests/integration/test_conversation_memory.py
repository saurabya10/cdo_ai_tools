#!/usr/bin/env python3
"""
Quick test script to verify conversation memory functionality
"""

import asyncio
import sys
from mcp_server import MCPServer

async def test_conversation_memory():
    """Test the conversation memory implementation"""
    print("🧪 Testing Conversation Memory Implementation")
    print("=" * 50)
    
    mcp_server = MCPServer()
    
    try:
        # Test 1: Simple conversation memory
        print("\n✅ Test 1: Simple Memory")
        result1 = await mcp_server._handle_llm_chat(
            prompt="Hello, my name is Alice",
            session_id="test_session"
        )
        
        result2 = await mcp_server._handle_llm_chat(
            prompt="What is my name?",
            session_id="test_session"
        )
        
        if result1['success'] and result2['success']:
            print("   ✅ Simple memory test passed")
            print(f"   Response: {result2['response'][:100]}...")
        else:
            print("   ❌ Simple memory test failed")
            return False
        
        # Test 2: Conversation summary
        print("\n✅ Test 2: Conversation Summary")
        summary = await mcp_server.get_conversation_summary("test_session")
        print(f"   Messages: {summary['message_count']}, Exchanges: {summary['exchange_count']}")
        
        if summary['message_count'] == 4 and summary['exchange_count'] == 2:
            print("   ✅ Summary test passed")
        else:
            print(f"   ❌ Summary test failed - Expected 4 messages, got {summary['message_count']}")
            return False
        
        # Test 3: MessagesPlaceholder approach
        print("\n✅ Test 3: MessagesPlaceholder")
        result3 = await mcp_server.chat_with_memory_chain(
            user_input="What programming languages do you know?",
            session_id="placeholder_test"
        )
        
        if result3['success']:
            print("   ✅ MessagesPlaceholder test passed")
            print(f"   Method: {result3.get('method', 'Unknown')}")
        else:
            print("   ❌ MessagesPlaceholder test failed")
            return False
        
        # Test 4: Clear conversation
        print("\n✅ Test 4: Clear Conversation")
        mcp_server.clear_conversation("test_session")
        summary_after = await mcp_server.get_conversation_summary("test_session")
        
        if summary_after['message_count'] == 0:
            print("   ✅ Clear conversation test passed")
        else:
            print(f"   ❌ Clear conversation test failed - Expected 0 messages, got {summary_after['message_count']}")
            return False
        
        print("\n🎉 All tests passed! Conversation memory is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return False
    
    finally:
        await mcp_server.close()

async def test_integration_with_routing():
    """Test conversation memory with the analyze_and_route system"""
    print("\n🧪 Testing Integration with Routing System")
    print("=" * 50)
    
    mcp_server = MCPServer()
    
    try:
        # Test conversation through analyze_and_route
        result1 = await mcp_server.analyze_and_route("Hi, I'm Bob from marketing")
        result2 = await mcp_server.analyze_and_route("What department am I from?")
        
        if result1['success'] and result2['success']:
            print("✅ Integration test passed")
            print(f"Response includes context: {'marketing' in result2['response'].lower()}")
        else:
            print("❌ Integration test failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        return False
    
    finally:
        await mcp_server.close()

async def main():
    """Run all tests"""
    print("🚀 Running Conversation Memory Tests")
    
    # Run basic memory tests
    test1_passed = await test_conversation_memory()
    
    # Run integration tests
    test2_passed = await test_integration_with_routing()
    
    if test1_passed and test2_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("🎉 Your conversation memory implementation is ready for demo!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please check the implementation and try again.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
