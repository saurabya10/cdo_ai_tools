"""
SAL (Secure Analytics and Logging) Troubleshooting Tool
Orchestrates SCC device lookup with DynamoDB event tracking for troubleshooting
"""
import os
import time
import boto3
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SALTroubleshootTool:
    """Tool for troubleshooting SAL event streaming from firewall devices"""
    
    def __init__(self, scc_tool=None, dynamodb_tool=None):
        # Dependencies on other tools
        self.scc_tool = scc_tool
        self.dynamodb_tool = dynamodb_tool
        
        # SAL configuration from environment
        self.default_stream_id = os.getenv('SAL_STREAM_ID', '')
        self.last_event_table = os.getenv('LAST_EVENT_TRACKING_TABLE_PER_DEVICE', '')
        
        # Troubleshooting thresholds
        self.recent_event_threshold_minutes = 15  # Consider events older than 15 minutes as stale
        
        if not self.last_event_table:
            logger.warning("LAST_EVENT_TRACKING_TABLE_PER_DEVICE not configured in environment")
    
    def _get_current_epoch(self) -> int:
        """Get current time as epoch timestamp"""
        return int(time.time())
    
    def _epoch_to_readable(self, epoch_timestamp: int) -> str:
        """Convert epoch timestamp to readable format"""
        try:
            return datetime.fromtimestamp(epoch_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, OSError):
            return f"Invalid timestamp: {epoch_timestamp}"
    
    def _minutes_since_epoch(self, epoch_timestamp: int) -> int:
        """Calculate minutes elapsed since the given epoch timestamp"""
        current_epoch = self._get_current_epoch()
        return (current_epoch - epoch_timestamp) // 60
    
    async def find_devices_by_criteria(self, device_name: str = None, device_filter: str = None) -> Dict[str, Any]:
        """Find firewall devices using SCC tool based on search criteria"""
        try:
            if not self.scc_tool:
                return {'success': False, 'error': 'SCC tool not available'}
            
            # Determine search strategy
            if device_name:
                # Search for specific device by name
                result = await self.scc_tool.process_request('find', search_term=device_name)
            elif device_filter:
                # Use custom filter
                result = await self.scc_tool.process_request('query', lucene_query=device_filter)
            else:
                # List all devices
                result = await self.scc_tool.process_request('list', limit=100)
            
            if result['success']:
                devices = result.get('items', [])
                # Filter out devices without uidOnFmc (needed for SAL tracking)
                valid_devices = [d for d in devices if d.get('uidOnFmc')]
                
                return {
                    'success': True,
                    'devices_found': len(valid_devices),
                    'devices': valid_devices,
                    'search_criteria': device_name or device_filter or 'all devices'
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error finding devices: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def check_device_last_event(self, stream_id: str, device_uuid: str, device_name: str = None) -> Dict[str, Any]:
        """Check last event timestamp for a specific device from DynamoDB"""
        try:
            if not self.dynamodb_tool:
                return {'success': False, 'error': 'DynamoDB tool not available'}
            
            if not self.last_event_table:
                return {'success': False, 'error': 'LAST_EVENT_TRACKING_TABLE_PER_DEVICE not configured'}
            
            # Query DDB table using partition key (tenant_id/stream_id) and sort key (device_uuid)
            result = self.dynamodb_tool.process_query(
                table_name=self.last_event_table,
                operation='query',
                partition_key='tenant_id',
                partition_value=stream_id,
                sort_key='device_uuid', 
                sort_value=device_uuid
            )
            
            if not result['success']:
                return result
            
            records = result.get('items', [])
            current_epoch = self._get_current_epoch()
            
            if not records:
                # No record found - device never sent events
                return {
                    'success': True,
                    'device_name': device_name or 'Unknown',
                    'device_uuid': device_uuid,
                    'stream_id': stream_id,
                    'status': 'no_events_ever',
                    'message': 'No events have ever been recorded for this device in SAL',
                    'troubleshooting': 'Device may not be properly configured to send events to SAL or may have never been active',
                    'last_event_time': None,
                    'minutes_since_last_event': None,
                    'is_recent': False
                }
            
            # Get the most recent record (should be only one with this query)
            record = records[0]
            last_timestamp = record.get('last_timestamp')
            
            if not last_timestamp:
                return {
                    'success': True,
                    'device_name': device_name or 'Unknown',
                    'device_uuid': device_uuid,
                    'stream_id': stream_id,
                    'status': 'invalid_timestamp',
                    'message': 'Device record exists but has invalid timestamp',
                    'troubleshooting': 'Database record corruption or invalid data format',
                    'last_event_time': None,
                    'minutes_since_last_event': None,
                    'is_recent': False
                }
            
            # Convert to int if it's a string
            try:
                last_timestamp_epoch = int(last_timestamp)
            except (ValueError, TypeError):
                return {
                    'success': True,
                    'device_name': device_name or 'Unknown',
                    'device_uuid': device_uuid,
                    'stream_id': stream_id,
                    'status': 'invalid_timestamp',
                    'message': f'Invalid timestamp format: {last_timestamp}',
                    'troubleshooting': 'Database timestamp is not in valid epoch format',
                    'last_event_time': None,
                    'minutes_since_last_event': None,
                    'is_recent': False
                }
            
            # Calculate time difference
            minutes_since = self._minutes_since_epoch(last_timestamp_epoch)
            is_recent = minutes_since <= self.recent_event_threshold_minutes
            readable_time = self._epoch_to_readable(last_timestamp_epoch)
            
            # Determine status and message
            if is_recent:
                status = 'events_recent'
                message = f'Device is actively sending events to SAL. Last event: {readable_time} ({minutes_since} minutes ago)'
                troubleshooting = 'Device is working correctly - events are being received recently'
            else:
                status = 'events_stale'
                message = f'No recent events from device. Last event: {readable_time} ({minutes_since} minutes ago)'
                troubleshooting = f'Device may be offline, misconfigured, or experiencing connectivity issues. Events are older than {self.recent_event_threshold_minutes} minutes'
            
            return {
                'success': True,
                'device_name': device_name or 'Unknown',
                'device_uuid': device_uuid,
                'stream_id': stream_id,
                'status': status,
                'message': message,
                'troubleshooting': troubleshooting,
                'last_event_time': readable_time,
                'last_event_timestamp': last_timestamp_epoch,
                'minutes_since_last_event': minutes_since,
                'is_recent': is_recent,
                'threshold_minutes': self.recent_event_threshold_minutes
            }
            
        except Exception as e:
            logger.error(f"Error checking device last event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def troubleshoot_device(self, device_criteria: str, stream_id: str = None) -> Dict[str, Any]:
        """Main troubleshooting method - find device and check its SAL event status"""
        try:
            # Step 1: Find device using SCC
            device_result = await self.find_devices_by_criteria(device_name=device_criteria)
            
            if not device_result['success']:
                return device_result
            
            devices = device_result.get('devices', [])
            
            if not devices:
                return {
                    'success': True,
                    'status': 'device_not_found',
                    'message': f'No firewall devices found matching criteria: {device_criteria}',
                    'troubleshooting': 'Check device name spelling or try broader search criteria'
                }
            
            # Step 2: Determine stream ID
            if not stream_id:
                stream_id = self.default_stream_id
                if not stream_id:
                    return {
                        'success': False,
                        'error': 'Stream ID required but not provided and no default configured (SAL_STREAM_ID)',
                        'devices_found': devices,
                        'message': 'Please provide stream_id parameter or configure SAL_STREAM_ID in environment'
                    }
            
            # Step 3: Check each matching device
            device_results = []
            
            for device in devices:
                device_name = device.get('name', 'Unknown')
                device_uuid = device.get('uidOnFmc')
                
                if not device_uuid:
                    device_results.append({
                        'device_name': device_name,
                        'device_uuid': None,
                        'status': 'no_uuid',
                        'message': 'Device does not have uidOnFmc (not manageable by FMC)',
                        'troubleshooting': 'This device type may not support SAL event streaming'
                    })
                    continue
                
                # Check SAL event status for this device
                event_check = await self.check_device_last_event(stream_id, device_uuid, device_name)
                
                if event_check['success']:
                    device_results.append(event_check)
                else:
                    device_results.append({
                        'device_name': device_name,
                        'device_uuid': device_uuid,
                        'status': 'error',
                        'message': f'Error checking events: {event_check.get("error", "Unknown error")}',
                        'troubleshooting': 'Unable to query SAL event tracking table'
                    })
            
            # Step 4: Generate summary
            total_devices = len(device_results)
            recent_devices = sum(1 for d in device_results if d.get('is_recent', False))
            stale_devices = sum(1 for d in device_results if d.get('status') == 'events_stale')
            no_events_devices = sum(1 for d in device_results if d.get('status') == 'no_events_ever')
            
            return {
                'success': True,
                'search_criteria': device_criteria,
                'stream_id': stream_id,
                'devices_checked': total_devices,
                'summary': {
                    'total_devices': total_devices,
                    'devices_with_recent_events': recent_devices,
                    'devices_with_stale_events': stale_devices,
                    'devices_with_no_events': no_events_devices
                },
                'device_results': device_results,
                'overall_status': 'healthy' if recent_devices == total_devices else 'issues_detected'
            }
            
        except Exception as e:
            logger.error(f"Error in device troubleshooting: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def check_all_devices_status(self, stream_id: str = None, limit: int = 50) -> Dict[str, Any]:
        """Check SAL event status for all firewall devices"""
        try:
            # Use default stream ID if not provided
            if not stream_id:
                stream_id = self.default_stream_id
                if not stream_id:
                    return {
                        'success': False,
                        'error': 'Stream ID required but not provided and no default configured (SAL_STREAM_ID)'
                    }
            
            # Get all devices from SCC
            device_result = await self.find_devices_by_criteria()  # No criteria = get all
            
            if not device_result['success']:
                return device_result
            
            devices = device_result.get('devices', [])[:limit]  # Limit for performance
            
            if not devices:
                return {
                    'success': True,
                    'status': 'no_devices',
                    'message': 'No firewall devices found in SCC'
                }
            
            # Check each device
            device_results = []
            
            for device in devices:
                device_name = device.get('name', 'Unknown')
                device_uuid = device.get('uidOnFmc')
                
                if not device_uuid:
                    device_results.append({
                        'device_name': device_name,
                        'device_uuid': None,
                        'status': 'no_uuid',
                        'is_recent': False
                    })
                    continue
                
                # Check SAL event status
                event_check = await self.check_device_last_event(stream_id, device_uuid, device_name)
                
                if event_check['success']:
                    device_results.append(event_check)
                else:
                    device_results.append({
                        'device_name': device_name,
                        'device_uuid': device_uuid,
                        'status': 'error',
                        'is_recent': False
                    })
            
            # Generate comprehensive summary
            total_devices = len(device_results)
            recent_devices = sum(1 for d in device_results if d.get('is_recent', False))
            stale_devices = sum(1 for d in device_results if d.get('status') == 'events_stale')
            no_events_devices = sum(1 for d in device_results if d.get('status') == 'no_events_ever')
            error_devices = sum(1 for d in device_results if d.get('status') == 'error')
            
            healthy_percentage = (recent_devices / total_devices * 100) if total_devices > 0 else 0
            
            return {
                'success': True,
                'stream_id': stream_id,
                'devices_checked': total_devices,
                'summary': {
                    'total_devices': total_devices,
                    'devices_with_recent_events': recent_devices,
                    'devices_with_stale_events': stale_devices,
                    'devices_with_no_events': no_events_devices,
                    'devices_with_errors': error_devices,
                    'healthy_percentage': round(healthy_percentage, 2)
                },
                'device_results': device_results,
                'overall_status': 'healthy' if healthy_percentage > 80 else 'issues_detected',
                'recommendations': self._generate_recommendations(device_results)
            }
            
        except Exception as e:
            logger.error(f"Error checking all devices status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _generate_recommendations(self, device_results: List[Dict]) -> List[str]:
        """Generate troubleshooting recommendations based on device results"""
        recommendations = []
        
        no_events_count = sum(1 for d in device_results if d.get('status') == 'no_events_ever')
        stale_count = sum(1 for d in device_results if d.get('status') == 'events_stale')
        
        if no_events_count > 0:
            recommendations.append(f"{no_events_count} devices have never sent events - check SAL configuration and device connectivity")
        
        if stale_count > 0:
            recommendations.append(f"{stale_count} devices have stale events - verify devices are online and SAL forwarding is working")
        
        if no_events_count == 0 and stale_count == 0:
            recommendations.append("All devices are sending recent events to SAL - system is healthy")
        
        return recommendations
    
    async def process_request(self, operation: str = 'troubleshoot_device', **kwargs) -> Dict[str, Any]:
        """Main method to process SAL troubleshooting requests"""
        try:
            if operation == 'troubleshoot_device':
                device_criteria = kwargs.get('device_criteria') or kwargs.get('device_name', '')
                stream_id = kwargs.get('stream_id')
                
                if not device_criteria:
                    return {'success': False, 'error': 'device_criteria or device_name is required'}
                
                return await self.troubleshoot_device(device_criteria, stream_id)
            
            elif operation == 'check_all_devices':
                stream_id = kwargs.get('stream_id')
                limit = kwargs.get('limit', 50)
                return await self.check_all_devices_status(stream_id, limit)
            
            elif operation == 'check_device_events':
                stream_id = kwargs.get('stream_id') or self.default_stream_id
                device_uuid = kwargs.get('device_uuid')
                device_name = kwargs.get('device_name', 'Unknown')
                
                if not stream_id:
                    return {'success': False, 'error': 'stream_id is required'}
                if not device_uuid:
                    return {'success': False, 'error': 'device_uuid is required'}
                
                return await self.check_device_last_event(stream_id, device_uuid, device_name)
            
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}. Available: troubleshoot_device, check_all_devices, check_device_events'}
                
        except Exception as e:
            logger.error(f"Error processing SAL troubleshooting request: {str(e)}")
            return {'success': False, 'error': str(e)}
