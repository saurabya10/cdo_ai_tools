"""
LLM Client for company hosted model integration
"""
import httpx
import json
import asyncio
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    app_key: str
    client_id: str
    client_secret: str
    endpoint: str
    timeout: int = 30
    max_retries: int = 3


class LLMClient:
    """Client for interacting with company hosted LLM model"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = None
        self._auth_token = None
    
    async def _get_auth_token(self) -> str:
        """Authenticate and get access token"""
        try:
            auth_url = f"{self.config.endpoint}/auth/token"
            
            auth_data = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'app_key': self.config.app_key,
                'grant_type': 'client_credentials'
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(auth_url, json=auth_data)
                response.raise_for_status()
                
                token_data = response.json()
                self._auth_token = token_data.get('access_token')
                
                if not self._auth_token:
                    raise ValueError("No access token received from auth endpoint")
                
                logger.info("Successfully authenticated with LLM service")
                return self._auth_token
                
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
    
    async def _make_request(self, prompt: str, system_message: str = None, 
                           max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """Make request to LLM endpoint"""
        try:
            if not self._auth_token:
                await self._get_auth_token()
            
            headers = {
                'Authorization': f'Bearer {self._auth_token}',
                'Content-Type': 'application/json'
            }
            
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'stream': False
            }
            
            completion_url = f"{self.config.endpoint}/chat/completions"
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(completion_url, json=payload, headers=headers)
                
                # Handle token expiration
                if response.status_code == 401:
                    logger.info("Token expired, re-authenticating...")
                    await self._get_auth_token()
                    headers['Authorization'] = f'Bearer {self._auth_token}'
                    response = await client.post(completion_url, json=payload, headers=headers)
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("Request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error making LLM request: {str(e)}")
            raise
    
    async def generate_response(self, prompt: str, system_message: str = None, 
                              max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate response from LLM model"""
        try:
            response = await self._make_request(prompt, system_message, max_tokens, temperature)
            
            # Extract content from response
            choices = response.get('choices', [])
            if not choices:
                return {
                    'success': False,
                    'error': 'No response choices returned from LLM'
                }
            
            message = choices[0].get('message', {})
            content = message.get('content', '').strip()
            
            if not content:
                return {
                    'success': False,
                    'error': 'Empty response content from LLM'
                }
            
            return {
                'success': True,
                'response': content,
                'usage': response.get('usage', {}),
                'model': response.get('model', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """Analyze user intent to determine which tool to use"""
        system_message = """
        You are an intent classifier. Analyze the user's input and determine what action they want to perform.
        
        Available actions:
        1. "file_read" - User wants to read, analyze, or search in CSV/text files
        2. "dynamodb_query" - User wants to query or search DynamoDB tables
        3. "general_chat" - General conversation or questions not requiring specific tools
        
        Respond with ONLY a JSON object in this format:
        {
            "action": "file_read|dynamodb_query|general_chat",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
        
        Examples:
        - "Read the sales data from report.csv" -> file_read
        - "Find user with ID 12345 in user table" -> dynamodb_query  
        - "What's the weather like?" -> general_chat
        """
        
        try:
            result = await self.generate_response(
                prompt=user_input,
                system_message=system_message,
                max_tokens=200,
                temperature=0.1
            )
            
            if result['success']:
                # Try to parse JSON response
                try:
                    intent_data = json.loads(result['response'])
                    return {
                        'success': True,
                        'action': intent_data.get('action', 'general_chat'),
                        'confidence': intent_data.get('confidence', 0.5),
                        'reasoning': intent_data.get('reasoning', '')
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    response_text = result['response'].lower()
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
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to analyze intent')
                }
                
        except Exception as e:
            logger.error(f"Error analyzing intent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def close(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
