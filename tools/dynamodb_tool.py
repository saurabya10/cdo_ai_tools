"""
DynamoDB querying tool using AWS boto3 client
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, Any, List, Optional, Union
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class DynamoDBTool:
    """Tool for querying DynamoDB tables"""
    
    def __init__(self, region_name: str = 'us-east-2'):
        # Initialize DynamoDB client and resource (AWS credentials from environment)
        self.region_name = region_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.client = boto3.client('dynamodb', region_name=region_name)
    
    def list_tables(self) -> Dict[str, Any]:
        """List all available DynamoDB tables"""
        try:
            response = self.client.list_tables()
            return {
                'success': True,
                'tables': response.get('TableNames', []),
                'count': len(response.get('TableNames', []))
            }
        except Exception as e:
            logger.error(f"Error listing DynamoDB tables: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get table schema and metadata"""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            
            return {
                'success': True,
                'table_name': table_name,
                'item_count': table.item_count,
                'table_size_bytes': table.table_size_bytes,
                'key_schema': table.key_schema,
                'attribute_definitions': table.attribute_definitions,
                'provisioned_throughput': table.provisioned_throughput,
                'table_status': table.table_status
            }
        except Exception as e:
            logger.error(f"Error describing table {table_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def query_by_partition_key(self, table_name: str, partition_key: str, partition_value: Union[str, int, float]) -> Dict[str, Any]:
        """Query table by partition key"""
        try:
            table = self.dynamodb.Table(table_name)
            
            response = table.query(
                KeyConditionExpression=Key(partition_key).eq(partition_value)
            )
            
            items = response.get('Items', [])
            return {
                'success': True,
                'items': json.loads(json.dumps(items, cls=DecimalEncoder)),
                'count': len(items),
                'scanned_count': response.get('ScannedCount', 0)
            }
        except Exception as e:
            logger.error(f"Error querying table {table_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def query_with_sort_key(self, table_name: str, partition_key: str, partition_value: Union[str, int, float],
                           sort_key: str, sort_value: Union[str, int, float], 
                           comparison: str = 'eq') -> Dict[str, Any]:
        """Query table with both partition and sort key"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Build key condition expression
            key_condition = Key(partition_key).eq(partition_value)
            
            if comparison == 'eq':
                key_condition = key_condition & Key(sort_key).eq(sort_value)
            elif comparison == 'lt':
                key_condition = key_condition & Key(sort_key).lt(sort_value)
            elif comparison == 'lte':
                key_condition = key_condition & Key(sort_key).lte(sort_value)
            elif comparison == 'gt':
                key_condition = key_condition & Key(sort_key).gt(sort_value)
            elif comparison == 'gte':
                key_condition = key_condition & Key(sort_key).gte(sort_value)
            elif comparison == 'begins_with':
                key_condition = key_condition & Key(sort_key).begins_with(str(sort_value))
            
            response = table.query(KeyConditionExpression=key_condition)
            
            items = response.get('Items', [])
            return {
                'success': True,
                'items': json.loads(json.dumps(items, cls=DecimalEncoder)),
                'count': len(items),
                'scanned_count': response.get('ScannedCount', 0)
            }
        except Exception as e:
            logger.error(f"Error querying table {table_name} with sort key: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def scan_with_filter(self, table_name: str, attribute_name: str, attribute_value: Union[str, int, float],
                        comparison: str = 'eq', limit: int = 100) -> Dict[str, Any]:
        """Scan table with filter expression"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Build filter expression
            if comparison == 'eq':
                filter_expression = Attr(attribute_name).eq(attribute_value)
            elif comparison == 'ne':
                filter_expression = Attr(attribute_name).ne(attribute_value)
            elif comparison == 'lt':
                filter_expression = Attr(attribute_name).lt(attribute_value)
            elif comparison == 'lte':
                filter_expression = Attr(attribute_name).lte(attribute_value)
            elif comparison == 'gt':
                filter_expression = Attr(attribute_name).gt(attribute_value)
            elif comparison == 'gte':
                filter_expression = Attr(attribute_name).gte(attribute_value)
            elif comparison == 'contains':
                filter_expression = Attr(attribute_name).contains(str(attribute_value))
            else:
                return {'success': False, 'error': f'Unsupported comparison: {comparison}'}
            
            response = table.scan(
                FilterExpression=filter_expression,
                Limit=limit
            )
            
            items = response.get('Items', [])
            return {
                'success': True,
                'items': json.loads(json.dumps(items, cls=DecimalEncoder)),
                'count': len(items),
                'scanned_count': response.get('ScannedCount', 0)
            }
        except Exception as e:
            logger.error(f"Error scanning table {table_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_item(self, table_name: str, key: Dict[str, Union[str, int, float]]) -> Dict[str, Any]:
        """Get single item by primary key"""
        try:
            table = self.dynamodb.Table(table_name)
            
            response = table.get_item(Key=key)
            
            item = response.get('Item')
            if item:
                return {
                    'success': True,
                    'item': json.loads(json.dumps(item, cls=DecimalEncoder)),
                    'found': True
                }
            else:
                return {
                    'success': True,
                    'item': None,
                    'found': False
                }
        except Exception as e:
            logger.error(f"Error getting item from table {table_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_query(self, table_name: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Main method to process DynamoDB queries based on operation type"""
        try:
            if operation == 'list_tables':
                return self.list_tables()
            
            elif operation == 'describe':
                return self.describe_table(table_name)
            
            elif operation == 'query':
                partition_key = kwargs.get('partition_key')
                partition_value = kwargs.get('partition_value')
                sort_key = kwargs.get('sort_key')
                sort_value = kwargs.get('sort_value')
                
                if not partition_key or partition_value is None:
                    return {'success': False, 'error': 'partition_key and partition_value are required'}
                
                if sort_key and sort_value is not None:
                    comparison = kwargs.get('comparison', 'eq')
                    return self.query_with_sort_key(table_name, partition_key, partition_value, 
                                                  sort_key, sort_value, comparison)
                else:
                    return self.query_by_partition_key(table_name, partition_key, partition_value)
            
            elif operation == 'scan':
                attribute_name = kwargs.get('attribute_name')
                attribute_value = kwargs.get('attribute_value')
                comparison = kwargs.get('comparison', 'eq')
                limit = kwargs.get('limit', 100)
                
                if not attribute_name or attribute_value is None:
                    return {'success': False, 'error': 'attribute_name and attribute_value are required for scan'}
                
                return self.scan_with_filter(table_name, attribute_name, attribute_value, comparison, limit)
            
            elif operation == 'get_item':
                key = kwargs.get('key')
                if not key:
                    return {'success': False, 'error': 'key is required for get_item operation'}
                
                return self.get_item(table_name, key)
            
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}'}
                
        except Exception as e:
            logger.error(f"Error processing DynamoDB query: {str(e)}")
            return {'success': False, 'error': str(e)}
