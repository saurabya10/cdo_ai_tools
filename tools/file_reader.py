"""
File reading tool for CSV and text files using MCP protocol
"""
import pandas as pd
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class FileReaderTool:
    """Tool for reading and processing CSV and text files"""
    
    def __init__(self):
        # Initialize supported file types
        self.supported_extensions = {'.csv', '.txt', '.tsv', '.json'}
    
    def read_csv_file(self, file_path: str, delimiter: str = ',', encoding: str = 'utf-8', limit: int = None) -> Dict[str, Any]:
        """Read CSV file and return structured data"""
        try:
            # Read CSV with optional row limit
            if limit:
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, nrows=limit)
            else:
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)
                
            return {
                'success': True,
                'data': df.to_dict('records'),
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'total_rows_read': len(df),
                'limited_to': limit if limit else 'all',
                'summary': df.describe().to_dict() if df.select_dtypes(include=['number']).shape[1] > 0 else None
            }
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def read_text_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read text file and return content with basic analysis"""
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
                lines = content.split('\n')
                
            return {
                'success': True,
                'content': content,
                'line_count': len(lines),
                'word_count': len(content.split()),
                'char_count': len(content),
                'preview': content[:500] + '...' if len(content) > 500 else content
            }
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def search_in_file(self, file_path: str, search_term: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search for specific terms in the file content"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
                # Search in all string columns
                matches = []
                for col in df.select_dtypes(include=['object']).columns:
                    if not case_sensitive:
                        mask = df[col].astype(str).str.contains(search_term, case=False, na=False)
                    else:
                        mask = df[col].astype(str).str.contains(search_term, na=False)
                    
                    matching_rows = df[mask]
                    if not matching_rows.empty:
                        matches.extend(matching_rows.to_dict('records'))
                
                return {
                    'success': True,
                    'matches': matches,
                    'match_count': len(matches),
                    'search_term': search_term
                }
            
            else:
                # Text file search
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    lines = content.split('\n')
                
                matching_lines = []
                for i, line in enumerate(lines):
                    if not case_sensitive:
                        if search_term.lower() in line.lower():
                            matching_lines.append({'line_number': i + 1, 'content': line.strip()})
                    else:
                        if search_term in line:
                            matching_lines.append({'line_number': i + 1, 'content': line.strip()})
                
                return {
                    'success': True,
                    'matches': matching_lines,
                    'match_count': len(matching_lines),
                    'search_term': search_term
                }
                
        except Exception as e:
            logger.error(f"Error searching in file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_time_interval(self, time_str: str) -> Optional[float]:
        """Parse time interval string with units (s, m, h) to seconds"""
        if not time_str or time_str in ['0.0', '0.00', '0']:
            return 0.0
        
        time_str = time_str.strip().lower()
        
        # Extract numeric part and unit
        if time_str.endswith('s'):
            # Seconds: "1.00s", "4.00s"
            numeric_part = time_str[:-1]
            multiplier = 1.0
        elif time_str.endswith('m'):
            # Minutes: "1.02m", "2.55m"  
            numeric_part = time_str[:-1]
            multiplier = 60.0
        elif time_str.endswith('h'):
            # Hours: "1.5h"
            numeric_part = time_str[:-1]
            multiplier = 3600.0
        else:
            # No unit, assume seconds
            numeric_part = time_str
            multiplier = 1.0
        
        try:
            return float(numeric_part) * multiplier
        except (ValueError, TypeError):
            return None
    
    def read_tenant_processing_csv(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read tenant processing CSV with horizontal format parsing and file name anonymization"""
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]
            
            if not lines:
                return {'success': False, 'error': 'File is empty'}
            
            # Parse header row to extract tenant information and column positions
            header_line = lines[0]
            header_parts = [part.strip() for part in header_line.split(',')]
            
            tenants = []
            tenant_positions = []
            
            # Find tenant headers (format: "TenantName - StreamID")
            i = 0
            tenant_counter = 0
            while i < len(header_parts):
                part = header_parts[i]
                if ' - ' in part and i + 3 < len(header_parts):
                    # Check if next parts are the expected headers
                    if ('Processing Time UTC' in header_parts[i+1] and 
                        'Time Interval' in header_parts[i+2] and 
                        ('Event Count' in header_parts[i+3] or 'Events' in header_parts[i+3])):
                        
                        tenant_counter += 1
                        
                        # Extract tenant name and stream ID
                        if ' - ' in part:
                            tenant_name, stream_id = part.split(' - ', 1)
                            tenant_name = tenant_name.strip()
                            stream_id = stream_id.strip()
                        else:
                            tenant_name = part
                            stream_id = 'unknown'
                        
                        tenant_info = {
                            'tenant_name': tenant_name,
                            'stream_id': stream_id,
                            'tenant_number': tenant_counter,
                            'column_start': i,  # Starting column index
                            'files': [],
                            'header_line': f"{part},{header_parts[i+1]},{header_parts[i+2]},{header_parts[i+3]}"
                        }
                        
                        tenants.append(tenant_info)
                        tenant_positions.append(i)
                        
                        # Skip to next potential tenant (typically 8 columns later: 4 data + 4 separators)
                        i += 8
                    else:
                        i += 1
                else:
                    i += 1
            
            # Process data rows
            file_counters = {tenant['tenant_number']: 1 for tenant in tenants}
            
            for row_idx in range(1, len(lines)):
                row_parts = [part.strip() for part in lines[row_idx].split(',')]
                
                # Process each tenant's data in this row
                for tenant in tenants:
                    col_start = tenant['column_start']
                    
                    # Check if this tenant has data in this row
                    if (col_start < len(row_parts) and 
                        row_parts[col_start] and 
                        col_start + 3 < len(row_parts)):
                        
                        original_file = row_parts[col_start]
                        processing_time = row_parts[col_start + 1]
                        time_interval = row_parts[col_start + 2]
                        events = row_parts[col_start + 3]
                        
                        # Skip empty rows for this tenant
                        if not original_file:
                            continue
                        
                        # Anonymize file name
                        tenant_num = tenant['tenant_number']
                        anonymized_file = f"t{tenant_num:02d}{file_counters[tenant_num]:02d}"
                        file_counters[tenant_num] += 1
                        
                        # Parse time interval to float for analysis
                        try:
                            time_interval_seconds = self._parse_time_interval(time_interval)
                        except (ValueError, AttributeError):
                            time_interval_seconds = None
                        
                        # Parse events count
                        try:
                            events_count = int(events) if events.isdigit() else None
                        except (ValueError, AttributeError):
                            events_count = None
                        
                        tenant['files'].append({
                            'original_file': original_file,
                            'anonymized_file': anonymized_file,
                            'processing_time': processing_time,
                            'time_interval': time_interval,
                            'time_interval_seconds': time_interval_seconds,
                            'events': events,
                            'events_count': events_count
                        })
            
            # Generate analysis summary
            total_files = sum(len(tenant['files']) for tenant in tenants)
            quick_processing_files = 0
            total_with_intervals = 0
            
            for tenant in tenants:
                for file_info in tenant['files']:
                    if file_info['time_interval_seconds'] is not None:
                        total_with_intervals += 1
                        if file_info['time_interval_seconds'] < 2.0:
                            quick_processing_files += 1
            
            quick_processing_percentage = (quick_processing_files / total_with_intervals * 100) if total_with_intervals > 0 else 0
            
            return {
                'success': True,
                'file_path': file_path,
                'total_tenants': len(tenants),
                'total_files': total_files,
                'tenants': tenants,
                'analysis': {
                    'total_files_with_intervals': total_with_intervals,
                    'quick_processing_files_under_2s': quick_processing_files,
                    'quick_processing_percentage': round(quick_processing_percentage, 2),
                    'average_processing_frequency': 'High' if quick_processing_percentage > 70 else 'Medium' if quick_processing_percentage > 30 else 'Low'
                },
                'file_type': 'tenant_processing_csv_horizontal'
            }
            
        except Exception as e:
            logger.error(f"Error reading tenant processing CSV {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_file(self, file_path: str, operation: str = 'read', **kwargs) -> Dict[str, Any]:
        """Main method to process file based on operation type"""
        if not Path(file_path).exists():
            return {'success': False, 'error': f'File {file_path} does not exist'}
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.supported_extensions:
            return {'success': False, 'error': f'Unsupported file type: {file_ext}'}
        
        if operation == 'read':
            if file_ext == '.csv':
                # Check if this is a tenant processing file (special format)
                if kwargs.get('tenant_format', False) or 'tenant' in os.path.basename(file_path).lower():
                    return self.read_tenant_processing_csv(file_path, encoding=kwargs.get('encoding', 'utf-8'))
                else:
                    # Only pass relevant parameters to read_csv_file
                    csv_kwargs = {k: v for k, v in kwargs.items() if k in ['delimiter', 'encoding', 'limit']}
                    return self.read_csv_file(file_path, **csv_kwargs)
            else:
                # Only pass relevant parameters to read_text_file
                text_kwargs = {k: v for k, v in kwargs.items() if k in ['encoding']}
                return self.read_text_file(file_path, **text_kwargs)
        
        elif operation == 'search':
            search_term = kwargs.get('search_term', '')
            if not search_term:
                return {'success': False, 'error': 'Search term is required'}
            return self.search_in_file(file_path, search_term, kwargs.get('case_sensitive', False))
        
        elif operation == 'tenant_analysis':
            # Special operation for tenant processing analysis
            if file_ext == '.csv':
                return self.read_tenant_processing_csv(file_path, encoding=kwargs.get('encoding', 'utf-8'))
            else:
                return {'success': False, 'error': 'Tenant analysis only supports CSV files'}
        
        else:
            return {'success': False, 'error': f'Unsupported operation: {operation}'}
