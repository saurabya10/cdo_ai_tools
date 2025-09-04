"""
Generic REST API tool for calling any HTTP endpoint
"""
import httpx
import json
import os
from typing import Dict, Any, Optional, Union
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class RestApiTool:
    """Generic tool for making REST API calls"""
    
    def __init__(self):
        self.timeout = 30.0
        self.max_redirects = 5
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None, 
                        auth_token: Optional[str] = None, 
                        auth_type: str = 'Bearer') -> Dict[str, str]:
        """Prepare HTTP headers with optional authentication"""
        default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'LLM-Tool-Orchestrator/1.0'
        }
        
        if headers:
            default_headers.update(headers)
        
        # Add authentication if provided
        if auth_token:
            if auth_type.lower() == 'bearer':
                default_headers['Authorization'] = f'Bearer {auth_token}'
            elif auth_type.lower() == 'basic':
                default_headers['Authorization'] = f'Basic {auth_token}'
            elif auth_type.lower() == 'api-key':
                default_headers['X-API-Key'] = auth_token
            else:
                default_headers['Authorization'] = f'{auth_type} {auth_token}'
        
        return default_headers
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    async def make_request(self, 
                          url: str,
                          method: str = 'GET',
                          headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None,
                          data: Optional[Union[Dict, str]] = None,
                          json_data: Optional[Dict[str, Any]] = None,
                          auth_token: Optional[str] = None,
                          auth_type: str = 'Bearer',
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """Make HTTP request to any REST endpoint"""
        try:
            # Validate URL
            if not self._validate_url(url):
                return {'success': False, 'error': f'Invalid URL format: {url}'}
            
            # Prepare headers
            request_headers = self._prepare_headers(headers, auth_token, auth_type)
            
            # Use provided timeout or default
            request_timeout = timeout or self.timeout
            
            # Prepare request data
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'headers': request_headers,
                'timeout': request_timeout,
                'follow_redirects': True
            }
            
            if params:
                request_kwargs['params'] = params
            
            if json_data:
                request_kwargs['json'] = json_data
            elif data:
                if isinstance(data, dict):
                    request_kwargs['json'] = data
                else:
                    request_kwargs['content'] = data
                    request_headers['Content-Type'] = 'text/plain'
            
            # Make the request
            async with httpx.AsyncClient() as client:
                response = await client.request(**request_kwargs)
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except (json.JSONDecodeError, ValueError):
                    response_data = response.text
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'url': str(response.url),
                    'method': method.upper(),
                    'is_json': isinstance(response_data, (dict, list)),
                    'response_size': len(response.content),
                    'encoding': response.encoding
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            try:
                error_data = e.response.json()
            except:
                error_data = e.response.text
                
            return {
                'success': False,
                'error': f'HTTP {e.response.status_code}',
                'status_code': e.response.status_code,
                'error_details': error_data,
                'url': str(e.response.url)
            }
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {url}")
            return {'success': False, 'error': f'Request timeout after {request_timeout}s'}
        except httpx.ConnectError:
            logger.error(f"Connection error to {url}")
            return {'success': False, 'error': f'Connection error to {url}'}
        except Exception as e:
            logger.error(f"Error making REST request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return await self.make_request(url, method='GET', **kwargs)
    
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        return await self.make_request(url, method='POST', **kwargs)
    
    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        return await self.make_request(url, method='PUT', **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self.make_request(url, method='DELETE', **kwargs)
    
    async def patch(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make PATCH request"""
        return await self.make_request(url, method='PATCH', **kwargs)
    
    async def process_request(self, operation: str = 'get', **kwargs) -> Dict[str, Any]:
        """Main method to process REST API requests"""
        try:
            url = kwargs.get('url')
            if not url:
                return {'success': False, 'error': 'url parameter is required'}
            
            # Get auth token from environment if not provided
            auth_token = kwargs.get('auth_token') or os.getenv('REST_API_TOKEN') or os.getenv('SCC_BEARER_TOKEN')
            if auth_token:
                kwargs['auth_token'] = auth_token
            
            # Remove url from kwargs to avoid duplicate parameter
            kwargs_clean = kwargs.copy()
            kwargs_clean.pop('url', None)
            
            if operation.lower() == 'get':
                return await self.get(url, **kwargs_clean)
            elif operation.lower() == 'post':
                return await self.post(url, **kwargs_clean)
            elif operation.lower() == 'put':
                return await self.put(url, **kwargs_clean)
            elif operation.lower() == 'delete':
                return await self.delete(url, **kwargs_clean)
            elif operation.lower() == 'patch':
                return await self.patch(url, **kwargs_clean)
            else:
                # Default to generic request with specified method
                method = kwargs.get('method', 'GET')
                kwargs_clean.pop('method', None)
                return await self.make_request(url, method=method, **kwargs_clean)
                
        except Exception as e:
            logger.error(f"Error processing REST API request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def paginated_get(self, 
                           url: str,
                           limit_param: str = 'limit',
                           offset_param: str = 'offset', 
                           page_size: int = 50,
                           max_pages: int = 10,
                           **kwargs) -> Dict[str, Any]:
        """Make paginated GET requests"""
        try:
            all_data = []
            page = 0
            offset = 0
            total_records = None
            
            while page < max_pages:
                # Add pagination parameters
                params = kwargs.get('params', {}).copy()
                params[limit_param] = page_size
                params[offset_param] = offset
                
                request_kwargs = kwargs.copy()
                request_kwargs['params'] = params
                
                response = await self.get(url, **request_kwargs)
                
                if not response['success']:
                    return response
                
                data = response['data']
                
                # Handle different pagination response formats
                if isinstance(data, dict):
                    # Format: {"items": [...], "total": 100}
                    items = data.get('items', data.get('data', data.get('results', [])))
                    if not items:
                        break
                    
                    all_data.extend(items)
                    
                    # Get total count if available
                    if total_records is None:
                        total_records = data.get('total', data.get('count', data.get('totalCount')))
                    
                elif isinstance(data, list):
                    # Format: [item1, item2, ...]
                    if not data:
                        break
                    all_data.extend(data)
                else:
                    # Single item or unknown format
                    all_data.append(data)
                    break
                
                # Check if we've got all data
                if len(data.get('items', data if isinstance(data, list) else [])) < page_size:
                    break
                
                page += 1
                offset += page_size
            
            return {
                'success': True,
                'total_pages': page,
                'total_records': total_records or len(all_data),
                'records_retrieved': len(all_data),
                'data': all_data,
                'paginated': True
            }
            
        except Exception as e:
            logger.error(f"Error in paginated GET: {str(e)}")
            return {'success': False, 'error': str(e)}
