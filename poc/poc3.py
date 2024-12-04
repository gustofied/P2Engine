import jwt
import time
import requests
import json

# Configuration
SECRET = 'secret'  # Use the same secret as your frontend
ledger_id = 'sandbox'  # Update if different
base_url = 'http://127.0.0.1:7575'  # JSON API endpoint

# Replace with your actual package ID
package_id = 'bfa1981cda2e76d6b9726340c5bda0dae971dfb89af007db3a17a3be0d57fc18'
user_template_id = f'{package_id}:User:User'

# Parties
alice_party_id = 'party-2d50054a-e7ee-46a0-a1f6-0fdf561071fa::your_namespace'
bob_party_id = 'party-43a02a67-25e1-40cd-ba95-925927449d92::your_namespace'

# Generate JWT token for a party
def generate_token(party_id):
    payload = {
        "https://daml.com/ledger-api": {
            "ledgerId": ledger_id,
            "applicationId": "my-app",
            "actAs": [party_id],
        },
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "sub": party_id,
    }
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

# Set up headers for a party
def get_headers(party_id):
    token = generate_token(party_id)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    return headers

# Query for a User contract for a party
def query_user_contract(party_id):
    headers = get_headers(party_id)
    query_payload = {
        'templateIds': [user_template_id],
        'query': {
            'username': party_id
        }
    }
    response = requests.post(
        f'{base_url}/v1/query',
        headers=headers,
        json=query_payload,
    )
    print(f"Query User Contract Response Status Code: {response.status_code}")
    print(f"Query User Contract Response Content: {response.text}")

    try:
        response_data = response.json()
        if 'result' in response_data:
            contracts = response_data['result']
            if contracts:
                contract = contracts[0]
                contract_id = contract['contractId']
                print(f"Found existing User Contract for {party_id}: {contract_id}")
                return contract_id
            else:
                print(f"No existing User Contract found for {party_id}")
                return None
        else:
            print("Unexpected response format:", response_data)
            return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response:", response.text)
        return None

# Create a User contract for a party if it doesn't exist
def get_or_create_user_contract(party_id):
    # First, try to query for an existing User contract
    contract_id = query_user_contract(party_id)
    if contract_id:
        return contract_id
    else:
        # If not found, create a new User contract
        headers = get_headers(party_id)
        create_payload = {
            'templateId': user_template_id,
            'payload': {
                'username': party_id,
                'following': [],
            },
        }
        response = requests.post(
            f'{base_url}/v1/create',
            headers=headers,
            json=create_payload,
        )
        print(f"Create User Response Status Code: {response.status_code}")
        print(f"Create User Response Content: {response.text}")

        try:
            response_data = response.json()
            if 'result' in response_data:
                contract = response_data['result']
                contract_id = contract['contractId']
                print(f"Created User Contract for {party_id}: {contract_id}")
                return contract_id
            else:
                print("Unexpected response format:", response_data)
                return None
        except json.JSONDecodeError:
            print("Failed to decode JSON response:", response.text)
            return None

# Exercise the Follow choice via /v1/exercise
def alice_follows_bob(alice_contract_id, alice_party_id, bob_party_id):
    headers = get_headers(alice_party_id)
    exercise_payload = {
        'templateId': user_template_id,
        'contractId': alice_contract_id,
        'choice': 'Follow',
        'argument': {
            'userToFollow': bob_party_id
        }
    }
    response = requests.post(
        f'{base_url}/v1/exercise',
        headers=headers,
        json=exercise_payload,
    )
    print(f"Exercise Follow Response Status Code: {response.status_code}")
    print(f"Exercise Follow Response Content: {response.text}")

    try:
        response_data = response.json()
        if 'result' in response_data:
            print(f"Alice successfully followed Bob.")
            return True
        else:
            print("Unexpected response format or error:", response_data)
            return False
    except json.JSONDecodeError:
        print("Failed to decode JSON response:", response.text)
        return False

# Query contracts for a party
def query_user_contracts(party_id):
    headers = get_headers(party_id)
    query_payload = {
        'templateIds': [user_template_id],
        'query': {
            'username': party_id
        }
    }
    response = requests.post(
        f'{base_url}/v1/query',
        headers=headers,
        json=query_payload,
    )
    print(f"Query Contracts Response Status Code: {response.status_code}")
    print(f"Query Contracts Response Content: {response.text}")

    try:
        response_data = response.json()
        if 'result' in response_data:
            contracts = response_data['result']
            print(f"Contracts for {party_id}:")
            print(json.dumps(contracts, indent=2))
            return contracts
        else:
            print("Unexpected response format:", response_data)
            return []
    except json.JSONDecodeError:
        print("Failed to decode JSON response:", response.text)
        return []

# Main function
def main():
    # Replace 'your_namespace' with your actual namespace
    alice_party_id_actual = 'party-2d50054a-e7ee-46a0-a1f6-0fdf561071fa::12205d5c2964224e4254b0121a069d6b3146b430561661910afc3f9759d611045ee8'
    bob_party_id_actual = 'party-43a02a67-25e1-40cd-ba95-925927449d92::12205d5c2964224e4254b0121a069d6b3146b430561661910afc3f9759d611045ee8'
    # Update the party IDs
    global alice_party_id, bob_party_id
    alice_party_id = alice_party_id_actual
    bob_party_id = bob_party_id_actual

    # Get or create User contracts for Alice and Bob
    print("Getting or creating User contracts for Alice and Bob...")
    alice_contract_id = get_or_create_user_contract(alice_party_id)
    bob_contract_id = get_or_create_user_contract(bob_party_id)

    if not alice_contract_id or not bob_contract_id:
        print("Failed to get or create User contracts for Alice or Bob.")
        return

    # Query Alice's User contract
    print("\nQuerying Alice's User contracts...")
    query_user_contracts(alice_party_id)

    # Have Alice follow Bob
    print("\nAlice is following Bob...")
    success = alice_follows_bob(alice_contract_id, alice_party_id, bob_party_id)

    if success:
        # Query Alice's User contract again to see the updated following list
        print("\nQuerying Alice's User contracts after following Bob...")
        query_user_contracts(alice_party_id)
    else:
        print("Failed to have Alice follow Bob.")

if __name__ == '__main__':
    main()
