# SAL (Secure Analytics and Logging) Troubleshooting - Sample Prompts

## Overview
The SAL troubleshooting tool orchestrates a multi-step workflow to diagnose firewall device event streaming issues:
1. **Find devices** using SCC (Security Cloud Control) API
2. **Resolve stream ID** (from input, user prompt, or default environment variable)
3. **Query DynamoDB** last event tracking table using `tenant_id` (stream_id) + `device_uuid` (uidOnFmc)
4. **Analyze timestamps** and provide troubleshooting insights

## Configuration Required

### Environment Variables (.env file):
```bash
# SAL Configuration
SAL_STREAM_ID=your_default_sal_stream_id_here
LAST_EVENT_TRACKING_TABLE_PER_DEVICE=your_last_event_tracking_table_name_here

# SCC API (required for device lookup)
SCC_BEARER_TOKEN=your_scc_bearer_token_here

# AWS/DynamoDB (required for event tracking)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
DYNAMODB_REGION=us-east-2
```

## Sample Test Prompts

### 1. Single Device Troubleshooting
**Prompt:**
```
"Find the firewall device with name 'Paradise' and find if it is sending events to SAL or not"
```

**Expected Workflow:**
1. Search SCC for device named "Paradise"
2. Extract `uidOnFmc` from device info
3. Use default `SAL_STREAM_ID` from environment
4. Query DynamoDB: `tenant_id` = stream_id, `device_uuid` = uidOnFmc
5. Analyze `last_timestamp` (epoch) vs current time
6. Report if events are recent (< 15 minutes) or stale

**Direct Tool Call:**
```bash
python3 main.py call-tool sal_troubleshoot '{"operation": "troubleshoot_device", "device_criteria": "Paradise"}'
```

---

### 2. All Devices Health Check
**Prompt:**
```
"Check if all devices are sending events or not?"
```

**Expected Workflow:**
1. Get all firewall devices from SCC
2. For each device with `uidOnFmc`, check SAL event status
3. Generate summary statistics and health report
4. Provide recommendations for devices with issues

**Direct Tool Call:**
```bash
python3 main.py call-tool sal_troubleshoot '{"operation": "check_all_devices", "limit": 50}'
```

---

### 3. Specific Device Last Event Query
**Prompt:**
```
"Check when was last event sent for a specific device with name 'Hacks-Home'"
```

**Expected Workflow:**
1. Find device "Hacks-Home" in SCC
2. Get its `uidOnFmc` and stream information
3. Query last event timestamp from DynamoDB
4. Convert epoch timestamp to readable format
5. Calculate time elapsed since last event

**Direct Tool Call:**
```bash
python3 main.py call-tool sal_troubleshoot '{"operation": "troubleshoot_device", "device_criteria": "Hacks-Home"}'
```

---

### 4. With Custom Stream ID
**Prompt:**
```
"Check SAL event status for device 'Paradise' using stream ID 'custom-stream-123'"
```

**Direct Tool Call:**
```bash
python3 main.py call-tool sal_troubleshoot '{"operation": "troubleshoot_device", "device_criteria": "Paradise", "stream_id": "custom-stream-123"}'
```

---

### 5. Direct Device UUID Check
**Prompt:**
```
"Check last events for device with UUID '4f973622-192a-11ef-b86d-8386f7533b4a'"
```

**Direct Tool Call:**
```bash
python3 main.py call-tool sal_troubleshoot '{"operation": "check_device_events", "device_uuid": "4f973622-192a-11ef-b86d-8386f7533b4a"}'
```

## Multi-Step Workflow Details

### Step 1: SCC Device Lookup
- **Tool Used**: `scc_tool`
- **Operation**: `find` with device name criteria
- **Data Extracted**: `name`, `uid`, `uidOnFmc`, `deviceType`, `connectivityState`
- **Key Field**: `uidOnFmc` (used as `device_uuid` in DynamoDB)

### Step 2: Stream ID Resolution
- **Priority Order**:
  1. Explicitly provided in query
  2. User prompt (if missing, ask user)
  3. Default from `SAL_STREAM_ID` environment variable
- **Usage**: Becomes `tenant_id` in DynamoDB query

### Step 3: DynamoDB Query
- **Table**: Value from `LAST_EVENT_TRACKING_TABLE_PER_DEVICE`
- **Partition Key**: `tenant_id` (stream_id)
- **Sort Key**: `device_uuid` (uidOnFmc)
- **Target Field**: `last_timestamp` (epoch timestamp)

### Step 4: Analysis & Recommendations
- **Recent Events**: < 15 minutes old = Healthy
- **Stale Events**: > 15 minutes old = Potential issues
- **No Events**: No DDB record = Never sent events
- **Troubleshooting**: Actionable recommendations based on status

## Expected Response Formats

### Healthy Device Response
```
✅ Device "Paradise" is actively sending events to SAL
• Last Event: 2025-08-26 18:30:45 UTC (5 minutes ago)
• Status: HEALTHY - Events are being received recently
• Stream ID: your-stream-id
• Device UUID: 4f973622-192a-11ef-b86d-8386f7533b4a
```

### Stale Events Response
```
⚠️ Device "Paradise" has stale event data
• Last Event: 2025-08-26 17:15:22 UTC (75 minutes ago)
• Status: STALE - No recent events (threshold: 15 minutes)
• Troubleshooting: Device may be offline, misconfigured, or experiencing connectivity issues
• Recommendation: Check device connectivity and SAL forwarding configuration
```

### No Events Response
```
❌ Device "Paradise" has never sent events to SAL
• Status: NO EVENTS EVER
• Troubleshooting: Device may not be properly configured to send events to SAL or may have never been active
• Recommendation: Verify SAL configuration on the device and check device activation status
```

### All Devices Summary
```
📊 SAL Event Streaming Health Report
• Total Devices Checked: 5
• Devices with Recent Events: 3 (60%)
• Devices with Stale Events: 1 (20%)
• Devices with No Events: 1 (20%)
• Overall Status: ISSUES DETECTED

🔧 Recommendations:
• 1 device has never sent events - check SAL configuration
• 1 device has stale events - verify device connectivity
```

## Natural Language Usage

### Interactive Mode:
```bash
python3 main.py interactive
# Then ask: "Find firewall device Paradise and check if it's sending events to SAL"
```

### Single Request Processing:
```bash
python3 main.py process "Check if all devices are sending events or not"
```

## Integration Benefits

1. **🔄 Multi-Tool Orchestration**: Seamlessly combines SCC + DynamoDB + Analysis
2. **🧠 Intelligent Routing**: LLM automatically detects SAL troubleshooting intent
3. **⚡ Efficient Queries**: Uses DynamoDB partition+sort key for optimal performance
4. **📊 Comprehensive Analysis**: Time-based analysis with actionable recommendations
5. **🛡️ Error Handling**: Graceful handling of missing devices, tables, or data
6. **🎯 Flexible Input**: Supports device names, UUIDs, custom stream IDs

## Troubleshooting Common Issues

### "Device not found"
- Verify device name spelling
- Check if device exists in SCC
- Try broader search criteria

### "Stream ID required"
- Set `SAL_STREAM_ID` in `.env` file
- Or provide `stream_id` in query

### "Table not configured" 
- Set `LAST_EVENT_TRACKING_TABLE_PER_DEVICE` in `.env` file
- Verify table exists in configured AWS region

### "Unable to locate credentials"
- Configure AWS credentials for DynamoDB access
- Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

**🎉 Ready for SAL troubleshooting workflows!**
