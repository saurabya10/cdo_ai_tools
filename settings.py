import base64
import requests
import json
import os
import certifi

from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("CLIENT_ID", "default_client_id")
client_secret = os.getenv("CLIENT_SECRET", "default_client_secret")
app_key = os.getenv("APP_KEY", "default_app_key")


llm_source = "bridgeIT"

llm_endpoint = "https://chat-ai.cisco.com"
llm_model = "gpt-4.1"
# available options for llm_model = gpt-4o-mini,gpt-4o,gpt-4.1
#api_version = "2024-07-01-preview"
#api_version = "2024-10-21"
api_version = "2025-04-01-preview"


def get_api_key():
    url = "https://id.cisco.com/oauth2/default/v1/token"

    payload = "grant_type=client_credentials"
    value = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode(
        "utf-8"
    )
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {value}",
    }

    token_response = requests.request(
        "POST", url, headers=headers, data=payload, verify=certifi.where()
    )

    return token_response.json()["access_token"]

