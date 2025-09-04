python main.py interactive          # Interactive mode
python main.py process "query"      # Single request
python main.py list-tools           # Show available tools


# Test file reading with sample data
python3 main.py call-tool file_reader '{"file_path": "eu-prod-tenant-file-intervals-2h-20250825_140239.csv", "operation": "read"}'

# List available tools  
python3 main.py list-tools

# Test DynamoDB (requires AWS credentials)
python3 main.py call-tool dynamodb_query '{"table_name": "", "operation": "list_tables"}'

# Interactive mode (requires LLM credentials)
python3 main.py interactive


# SCC Tool - Cisco Firewall Devices
python3 main.py call-tool scc_tool '{"operation": "list", "limit": 10}'
python3 main.py call-tool scc_tool '{"operation": "find", "search_term": "Paradise"}'

# REST API Tool - Any HTTP Endpoint  
python3 main.py call-tool rest_api '{"url": "https://api.github.com", "operation": "get"}'
python3 main.py call-tool rest_api '{"url": "https://jsonplaceholder.typicode.com/posts", "params": {"_limit": 5}}'

python3 main.py call-tool scc_tool '{"operation": "list", "limit": 5}'
python3 main.py call-tool scc_tool '{"operation": "find", "search_term": "Paradise"}'
python3 main.py call-tool scc_tool '{"operation": "all", "max_devices": 100}'
python3 main.py call-tool scc_tool '{"operation": "query", "lucene_query": "deviceType:CDFMC_MANAGED_FTD"}'

# Interactive Mode (with LLM credentials)
python3 main.py interactive
"List all firewall devices"
"Find device named Paradise"
"Call GitHub API to get repository information"
"Show me all ONLINE firewall devices with MALWARE_DEFENSE licenses"
"Compare sales data from CSV with device inventory from SCC"
"Call the monitoring API and analyze the response"


read first 10 records of tenant_file.csv file and 'Time Interval' field indicates the time difference between current file and previous processed file. Now do you think are we processing files very frequently and frequency between files are very quick (under 2 seconds) in most cases
read all records of tenant_file.csv file and 'Time Interval' field indicates the time difference between current file and previous processed file. Now do you think are we processing files very frequently and frequency between files are very quick (under 2 seconds) in most cases
Analyze the tenant processing patterns in tenant_reports/sample_tenant_processing.csv and compare which tenants have the most consistent processing intervals. Are there any tenants showing performance bottlenecks?
Read all records of tenant_reports/sample_tenant_processing.csv file and 'Time Interval' field indicates the time difference between current file and previous processed file. Now do you think are we processing files very frequently and frequency between files are very quick (under 2 seconds) in most cases?
From the tenant processing data in tenant_reports/eu-prod-tenant-file-intervals-3h-20250826_130808_fast_limited.csv, examine if there's a correlation between event count and processing time intervals. Do higher event volumes correlate with longer processing delays?
From the tenant processing data in tenant_reports/eu-prod-tenant-file-intervals-3h-20250826_131413_slow_limited.csv, examine if there's a correlation between event count and processing time intervals. Do higher event volumes correlate with longer processing delays?


python3 main.py call-tool file_reader '{"file_path": "tenant_reports/sample_tenant_processing.csv", "operation": "tenant_analysis"}'
python3 main.py process "Read all records of tenant_reports/sample_tenant_processing.csv file and analyze processing frequency patterns"

python3 main.py process "Find firewall device Paradise and check if it's sending events to SAL"
python3 main.py process "Check if all devices are sending events or not"  
python3 main.py process "When was last event sent for device Paradise" OR Is Paradise firewall device sending events now?

https://staging.manage.security.cisco.com/aegis/rest/v1/device/b6a2ef6f-1067-4257-8f68-fc252f9818fd/specific-device
https://staging.manage.security.cisco.com/aegis/rest/v1/device/b6a2ef6f-1067-4257-8f68-fc252f9818fd/specific-device

sqlite3 persistent_chat_history.db 
.tables
select count(*) from chat_messages;

response -

"cloudEvents":[
   {
      "id":"c64d2a4c-a194-11e8-bad0-eb6719b10fdb",
      "type":"CloudEventsConfig",
      "links":{
         "self":"https://fmc-ace2.app.staging.cdo.cisco.com/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/integration/cloudeventsconfigs/c64d2a4c-a194-11e8-bad0-eb6719b10fdb"
      },
      "sendIntrusionEvents":true,
      "sendFileEvents":true,
      "sendConnectionEvents":false,
      "sendAllConnectionEvents":true,
      "sendPackets":true,
      "sendNetworkDiscoveryEvents":false,
      "sendAIDefenseEvents":false,
      "devicesExcludedFromSendingEvents":[
         
      ]
   }
]

{
    "tags": {},
    "tagKeys": [],
    "tagValues": [],
    "uid": "1bbd3d07-4e33-4c1a-b44f-db2acef8b544",
    "name": "",
    "namespace": "fmc",
    "type": "appliance",
    "version": 1,
    "createdDate": 1756351963949,
    "lastUpdatedDate": 1756725644135,
    "actionContext": null,
    "stateMachineContext": null,
    "stateDate": 1756725635696,
    "status": "IDLE",
    "stateMachineDetails": {
        "uid": "ceec334f-0205-40ad-8cba-cf737a413ec0",
        "priority": "SCHEDULED",
        "identifier": "scheduledFmcRavpnStateMachine",
        "startDate": 1756725634483,
        "endDate": 1756725635667,
        "lastActiveDate": 1756725635655,
        "stateMachineType": "RA_VPN_SESSIONS_READ",
        "lastStep": "com.cisco.lockhart.model.statemachine.hooks.TransactionGlobalAfterHook",
        "lastError": null,
        "currentDataRequirements": null,
        "stateMachineInstanceCondition": "DONE"
    },
    "scheduledStateMachineEnabledMap": {},
    "pendingStatesQueue": [],
    "createdTenantUid": null,
    "credentials": null,
    "model": false,
    "serverVersion": "10.0.0-build 7056",
    "geoVersion": null,
    "vdbVersion": "build 413 ( 2025-08-25 13:00:04 )",
    "sruVersion": "2025-08-27-001-vrt",
    "upgradeStarted": false,
    "certificate": null,
    "cloudEvents": [
        "{\"id\":\"c64d2a4c-a194-11e8-bad0-eb6719b10fdb\",\"type\":\"CloudEventsConfig\",\"links\":{\"self\":\"https://fmc-ace2.app.staging.cdo.cisco.com/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/integration/cloudeventsconfigs/c64d2a4c-a194-11e8-bad0-eb6719b10fdb\"},\"sendIntrusionEvents\":true,\"sendFileEvents\":true,\"sendConnectionEvents\":false,\"sendAllConnectionEvents\":true,\"sendPackets\":true,\"sendNetworkDiscoveryEvents\":false,\"sendAIDefenseEvents\":false,\"devicesExcludedFromSendingEvents\":[]}"
    ],
    "domainUid": "e276abec-e0f2-11e3-8169-6d9ed49b625f",
    "fmcUuid": "059225a5-ed8e-4f5e-ac11-d2339f845597",
    "smartLicenseStatus": {
        "registrationStatus": "EVALUATION",
        "registrationTimestamp": 0,
        "authorizationStatus": null,
        "authorizationTimeStamp": 0,
        "virtualAccount": null,
        "exportControl": false,
        "evaluationStartTime": 0,
        "evaluationRemainingDays": 85,
        "syncTimeStamp": 0
    },
    "primaryDeviceDetails": null,
    "secondaryDeviceDetails": null,
    "activeFmcPublicIPAddressOrFQDN": null,
    "activeFmcGuid": null,
    "s2SVpnPolicyInfoList": [],
    "accessPolicies": [],
    "domainReferences": [],
    "fmcSettings": {
        "discoverObjects": false,
        "manageNetworkObjects": false,
        "objectSyncMode": "MANUAL_SYNC"
    },
    "accessPolicyToLastModifiedTimeMap": {},
    "hasChildDomains": false,
    "workflowEnabled": false,
    "objectManagementToggledOff": false,
    "partOfHa": false,
    "state": "DONE",
    "triggerState": null,
    "queueTriggerState": null
}