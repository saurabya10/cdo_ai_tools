# Tenant Processing Analysis - Sample Prompts

## Overview
The enhanced file reader tool now supports specialized tenant processing CSV analysis with file name anonymization and processing frequency insights.

## Sample CSV Format (Horizontal Layout)
```csv
CompanyA - stream-001,Processing Time UTC,Time Interval,Event Count,,,,,TechCorp - stream-002,Processing Time UTC,Time Interval,Event Count,,,,,DataSolutions - stream-003,Processing Time UTC,Time Interval,Event Count
/data/logs/companyA/file1.csv,2024-01-15 10:05:23,0.0s,1245,,,,,/data/logs/techcorp/file1.csv,2024-01-15 14:56:12,0.0s,2134,,,,,/data/logs/datasolutions/file1.csv,2024-01-15 09:34:56,0.0s,3421
/data/logs/companyA/file2.csv,2024-01-15 10:05:25,2.1s,892,,,,,/data/logs/techcorp/file2.csv,2024-01-15 14:56:14,1.3s,1876,,,,,/data/logs/datasolutions/file2.csv,2024-01-15 09:34:58,2.4s,2987
```

**Format Details:**
- **Horizontal Layout**: Multiple tenants in columns, not rows
- **No Quotes**: No single quotes around tenant names or file paths
- **Column Pattern**: 4 data columns + 4 empty separator columns per tenant
- **Column Spacing**: Tenants at positions 0, 8, 16, 24, etc.

## Sample Test Prompts

### 1. Basic Tenant Processing Analysis
**Prompt:**
```
"Read all records from tenant_reports/sample_tenant_processing.csv file and analyze the Time Interval field which indicates the time difference between current file and previous processed file. Do you think we are processing files very frequently and is the frequency between files very quick (under 2 seconds) in most cases?"
```

**Expected Analysis:**
- File names anonymized (t0101, t0102, etc.)
- Processing frequency analysis
- Percentage of files processed under 2 seconds
- Tenant-specific insights

### 2. Tenant Comparison Analysis
**Prompt:**
```
"Analyze the tenant processing data in tenant_reports/sample_tenant_processing.csv and compare processing patterns between different tenants. Which tenant has the most consistent processing intervals and which one shows the highest processing frequency?"
```

**Expected Analysis:**
- Cross-tenant comparison
- Processing pattern identification
- Performance insights per tenant
- Recommendations for optimization

### 3. Event Volume and Processing Speed Correlation
**Prompt:**
```
"From tenant_reports/sample_tenant_processing.csv, examine if there's any correlation between the number of events processed and the time interval between files. Do tenants with higher event volumes take longer to process subsequent files?"
```

**Expected Analysis:**
- Event volume vs processing time correlation
- Performance bottleneck identification
- Tenant-specific processing capabilities
- Resource allocation recommendations

## Key Features Implemented

### ✅ File Name Anonymization
- Original: `/data/logs/companyA/2024/01/15/log_file_20240115_100523_detailed_events.csv`
- Anonymized: `t0101` (tenant 01, file 01)

### ✅ Tenant Parsing
- Automatic tenant detection from headers
- Stream ID extraction
- Tenant numbering for organization

### ✅ Processing Frequency Analysis
- Automatic calculation of files under 2s processing
- Processing frequency classification (High/Medium/Low)
- Statistical summary across all tenants

### ✅ Data Structure
```json
{
  "total_tenants": 4,
  "total_files": 22,
  "analysis": {
    "quick_processing_files_under_2s": 17,
    "quick_processing_percentage": 77.27,
    "average_processing_frequency": "High"
  },
  "tenants": [...]
}
```

## Usage Commands

### Direct Tool Call
```bash
python3 main.py call-tool file_reader '{"file_path": "tenant_reports/sample_tenant_processing.csv", "operation": "tenant_analysis"}'
```

### Natural Language Processing
```bash
python3 main.py process "Analyze tenant processing data from sample_tenant_processing.csv"
```

### Interactive Mode
```bash
python3 main.py interactive
# Then ask: "Read tenant processing data and analyze frequency patterns"
```

## Results Summary from Sample Data

- **4 Tenants Analyzed**: CompanyA, TechCorp, DataSolutions, GlobalTech
- **22 Total Files Processed**
- **77.27% High-Frequency Processing** (under 2 seconds)
- **Average Processing Pattern**: High frequency processing across all tenants
- **File Anonymization**: Successfully replaced long file paths with t01xx format

## Directory Structure
```
cursor_ai/
├── tenant_reports/
│   └── sample_tenant_processing.csv
├── tools/
│   └── file_reader.py (enhanced)
└── tenant_analysis_samples.md (this file)
```
