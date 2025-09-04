"""
Cisco Security Cloud Control (SCC) API tool for device inventory management
"""
import httpx
import json
import os
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class SCCTool:
    """Tool for interacting with Cisco Security Cloud Control API"""
    
    def __init__(self):
        # Base URL for Cisco SCC API
        self.base_url = "https://us.manage.security.cisco.com/api/rest/v1"
        self.bearer_token = os.getenv('SCC_BEARER_TOKEN', '')
        
        if not self.bearer_token:
            logger.warning("SCC_BEARER_TOKEN not found in environment variables")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication"""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _build_search_query(self, search_term: str) -> str:
        """Build Lucene query syntax for device search"""
        if not search_term:
            return ""
        
        # For SCC API, try different query approaches based on search term characteristics
        # 1. Simple name search (most common case)
        if search_term.replace(' ', '').isalnum():
            # For simple alphanumeric terms, try name field first
            return f'name:{search_term}'
        
        # 2. For more complex terms, escape and use multiple fields
        escaped_term = search_term.replace(' ', '\\ ').replace('"', '\\"')
        
        # Search across valid SCC API searchable fields
        # Start with most commonly used fields
        searchable_fields = ['name', 'deviceType', 'softwareVersion']
        
        # Build simpler query: name:term OR deviceType:term OR softwareVersion:term
        field_queries = [f'{field}:{escaped_term}' for field in searchable_fields]
        lucene_query = f"({' OR '.join(field_queries)})"
        
        return lucene_query
    
    async def list_devices(self, limit: int = 50, offset: int = 0, device_filter: str = None) -> Dict[str, Any]:
        """List firewall devices from SCC inventory"""
        try:
            if not self.bearer_token:
                return {'success': False, 'error': 'SCC_BEARER_TOKEN not configured in environment'}
            
            # Build URL with pagination parameters
            url = f"{self.base_url}/inventory/devices"
            params = {
                'limit': str(limit),  # API expects string according to documentation
                'offset': str(offset)  # API expects string according to documentation
            }
            
            # Add device filter using proper Lucene syntax if specified
            if device_filter:
                lucene_query = self._build_search_query(device_filter)
                if lucene_query:
                    params['q'] = lucene_query
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract relevant fields from each device
                filtered_devices = []
                for item in data.get('items', []):
                    filtered_device = {
                        'name': item.get('name'),
                        'uid': item.get('uid'),
                        'uidOnFmc': item.get('uidOnFmc'),
                        'deviceType': item.get('deviceType'),
                        'serial': item.get('serial'),
                        'softwareVersion': item.get('softwareVersion'),
                        'ftdLicenses': item.get('ftdLicenses', []),
                        'connectivityState': item.get('connectivityState'),
                        'configState': item.get('configState')
                    }
                    filtered_devices.append(filtered_device)
                
                return {
                    'success': True,
                    'count': data.get('count', 0),
                    'limit': data.get('limit', limit),
                    'offset': data.get('offset', offset),
                    'total_devices': data.get('count', 0),
                    'devices_returned': len(filtered_devices),
                    'items': filtered_devices,
                    'raw_response': data  # Keep full response for debugging
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling SCC API: {e.response.status_code} - {e.response.text}")
            return {
                'success': False, 
                'error': f'HTTP {e.response.status_code}: {e.response.text}',
                'status_code': e.response.status_code
            }
        except httpx.TimeoutException:
            logger.error("Timeout calling SCC API")
            return {'success': False, 'error': 'Request timeout'}
        except Exception as e:
            logger.error(f"Error calling SCC API: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def find_device(self, search_term: str, limit: int = 50) -> Dict[str, Any]:
        """Find specific device(s) by name, serial, or other criteria"""
        try:
            # First, try with API search using Lucene query
            result = await self.list_devices(limit=limit, device_filter=search_term)
            
            if not result['success']:
                return result
            
            devices = result.get('items', [])
            search_method = "API query"
            
            # If API search didn't return results, try local filtering as fallback
            if search_term and not devices:
                logger.info(f"API search for '{search_term}' returned no results, trying local filtering...")
                # Get all devices without filter and do local search
                full_result = await self.list_devices(limit=200)  # Get more devices for local search
                if full_result['success']:
                    devices = []
                    search_lower = search_term.lower()
                    for device in full_result.get('items', []):
                        # Search in name, deviceType, softwareVersion, and serial (local fallback can search serial)
                        device_matches = (
                            device.get('name', '').lower().find(search_lower) != -1 or
                            device.get('serial', '').lower().find(search_lower) != -1 or  # Serial search in local fallback
                            device.get('deviceType', '').lower().find(search_lower) != -1 or
                            device.get('softwareVersion', '').lower().find(search_lower) != -1 or
                            device.get('uid', '').lower().find(search_lower) != -1
                        )
                        if device_matches:
                            devices.append(device)
                    search_method = "local filtering"
            
            return {
                'success': True,
                'search_term': search_term,
                'search_method': search_method,
                'devices_found': len(devices),
                'items': devices,
                'lucene_query_used': self._build_search_query(search_term) if search_method == "API query" else None
            }
            
        except Exception as e:
            logger.error(f"Error finding device: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_all_devices(self, max_devices: int = 1000) -> Dict[str, Any]:
        """Get all devices with automatic pagination handling"""
        try:
            all_devices = []
            offset = 0
            limit = min(50, max_devices)  # API usually limits to 50 per request
            total_count = None
            
            while len(all_devices) < max_devices:
                result = await self.list_devices(limit=limit, offset=offset)
                
                if not result['success']:
                    return result
                
                devices = result.get('items', [])
                if not devices:
                    break  # No more devices
                
                all_devices.extend(devices)
                
                # Update total count from first response
                if total_count is None:
                    total_count = result.get('count', 0)
                
                # Check if we've got all devices
                if len(all_devices) >= total_count or len(devices) < limit:
                    break
                
                offset += limit
            
            return {
                'success': True,
                'total_count': total_count or len(all_devices),
                'devices_retrieved': len(all_devices),
                'items': all_devices[:max_devices]  # Ensure we don't exceed max_devices
            }
            
        except Exception as e:
            logger.error(f"Error getting all devices: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _raw_query(self, lucene_query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Execute raw Lucene query directly without modification"""
        try:
            if not self.bearer_token:
                return {'success': False, 'error': 'SCC_BEARER_TOKEN not configured in environment'}
            
            # Build URL with pagination parameters
            url = f"{self.base_url}/inventory/devices"
            params = {
                'limit': str(limit),
                'offset': str(offset),
                'q': lucene_query  # Use query directly
            }
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract relevant fields from each device
                filtered_devices = []
                for item in data.get('items', []):
                    filtered_device = {
                        'name': item.get('name'),
                        'uid': item.get('uid'),
                        'uidOnFmc': item.get('uidOnFmc'),
                        'deviceType': item.get('deviceType'),
                        'serial': item.get('serial'),
                        'softwareVersion': item.get('softwareVersion'),
                        'ftdLicenses': item.get('ftdLicenses', []),
                        'connectivityState': item.get('connectivityState'),
                        'configState': item.get('configState')
                    }
                    filtered_devices.append(filtered_device)
                
                return {
                    'success': True,
                    'count': data.get('count', 0),
                    'limit': data.get('limit', limit),
                    'offset': data.get('offset', offset),
                    'total_devices': data.get('count', 0),
                    'devices_returned': len(filtered_devices),
                    'items': filtered_devices,
                    'lucene_query': lucene_query,
                    'query_method': 'raw_lucene'
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling SCC API: {e.response.status_code} - {e.response.text}")
            return {
                'success': False, 
                'error': f'HTTP {e.response.status_code}: {e.response.text}',
                'status_code': e.response.status_code,
                'lucene_query': lucene_query
            }
        except httpx.TimeoutException:
            logger.error("Timeout calling SCC API")
            return {'success': False, 'error': 'Request timeout', 'lucene_query': lucene_query}
        except Exception as e:
            logger.error(f"Error calling SCC API: {str(e)}")
            return {'success': False, 'error': str(e), 'lucene_query': lucene_query}
    
    async def process_request(self, operation: str = 'list', **kwargs) -> Dict[str, Any]:
        """Main method to process SCC requests"""
        try:
            if operation == 'list':
                limit = kwargs.get('limit', 50)
                offset = kwargs.get('offset', 0)
                device_filter = kwargs.get('filter')
                return await self.list_devices(limit, offset, device_filter)
            
            elif operation == 'find':
                search_term = kwargs.get('search_term', '')
                limit = kwargs.get('limit', 50)
                if not search_term:
                    return {'success': False, 'error': 'search_term is required for find operation'}
                return await self.find_device(search_term, limit)
            
            elif operation == 'all':
                max_devices = kwargs.get('max_devices', 1000)
                return await self.get_all_devices(max_devices)
            
            elif operation == 'query':
                # Allow direct Lucene query for advanced users
                lucene_query = kwargs.get('lucene_query', '')
                limit = kwargs.get('limit', 50)
                offset = kwargs.get('offset', 0)
                if not lucene_query:
                    return {'success': False, 'error': 'lucene_query is required for query operation'}
                # Use raw query directly without processing
                return await self._raw_query(lucene_query, limit, offset)
            
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}. Available: list, find, all, query'}
                
        except Exception as e:
            logger.error(f"Error processing SCC request: {str(e)}")
            return {'success': False, 'error': str(e)}
