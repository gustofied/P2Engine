import os
from modules.api_calls import get_account_info, get_orders, get_nfts

os.environ["XRPSCAN_API_KEY"] = "your_actual_api_key"

test_address = "rL5NLhkffbFMbBzMz2NShfcF6nexrTzEjK"

print("Testing get_account_info:")
print(get_account_info(test_address))
print()

print("Testing get_orders:")
print(get_orders(test_address))
print()

print("Testing get_nfts:")
print(get_nfts(test_address))
print()