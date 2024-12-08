# poc.py
import jwt
import time
import requests
import json


SECRET = 'secret'
ledger_id = 'sandbox'
base_url = 'http://127.0.0.1:7575'

package_id = 'bfa1981cda2e76d6b9726340c5bda0dae971dfb89af007db3a17a3be0d57fc18'
user_template_id = f'{package_id}:User:User'
alias_template_id = f'{package_id}:User:Alias'

alice_party_id = 'party-2d50054a-e7ee-46a0-a1f6-0fdf561071fa::your_namespace'

def generate_token(sub):
    payload = {
        "https://daml.com/ledger-api": {
            "ledgerId": ledger_id,
            "applicationId": "my-app",
        },
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "sub": sub,
    }
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def get_headers_no_party():
    token = generate_token("script-user")
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

def get_headers(party_id):
    token = generate_token(party_id)
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

def allocate_new_party(party_id, display_name):
    headers = get_headers(party_id)
    allocate_payload = {
        'identifierHint': display_name,
        'displayName': display_name,
    }
    response = requests.post(
        f'{base_url}/v1/parties/allocate',
        headers=headers,
        json=allocate_payload,
    )
    print(f"Allocate New Party Response Status Code: {response.status_code}")
    print(f"Allocate New Party Response Content: {response.text}")
    return format_response(response)

def list_known_parties(party_id):
    headers = get_headers(party_id)
    response = requests.get(
        f'{base_url}/v1/parties',
        headers=headers,
    )
    print(f"List Known Parties Response Status Code: {response.status_code}")
    print(f"List Known Parties Response Content: {response.text}")
    return format_response(response)

def list_known_packages():
    headers = get_headers_no_party()
    response = requests.get(
        f'{base_url}/v1/packages',
        headers=headers,
    )
    print(f"List Known Packages Response Status Code: {response.status_code}")
    print(f"List Known Packages Response Content: {response.text}")
    return format_response(response)

def format_response(response):
    """Helper to format response into a consistent dictionary structure."""
    try:
        data = response.json()
    except json.JSONDecodeError:
        data = response.text
    return {
        "status": response.status_code,
        "data": data
    }
