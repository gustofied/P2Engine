import requests
import csv

# Replace these with the actual chainId and pairId you wish to query
chain_id = "xrpl"       # e.g., "xrpl"
pair_id = "your_pair_id" # e.g., "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"

# Construct the URL with the appropriate path parameters
url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_id}"

# Send the GET request to the API
response = requests.get(url)
if response.status_code != 200:
    print(f"Error: Received status code {response.status_code}")
    exit()

data = response.json()

# Extract the pairs list from the response
pairs = data.get("pairs", [])
if not pairs:
    print("No pair data found.")
    exit()

# Define the CSV file and the fields you want to store
csv_file = "pair_data.csv"
fieldnames = [
    "chainId", "dexId", "pairAddress", "priceNative", "priceUsd",
    "marketCap", "baseToken_name", "baseToken_symbol",
    "quoteToken_name", "quoteToken_symbol"
]

with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    # Loop through each pair (usually just one when querying by pair address)
    for pair in pairs:
        row = {
            "chainId": pair.get("chainId"),
            "dexId": pair.get("dexId"),
            "pairAddress": pair.get("pairAddress"),
            "priceNative": pair.get("priceNative"),
            "priceUsd": pair.get("priceUsd"),
            "marketCap": pair.get("marketCap"),
            "baseToken_name": pair.get("baseToken", {}).get("name"),
            "baseToken_symbol": pair.get("baseToken", {}).get("symbol"),
            "quoteToken_name": pair.get("quoteToken", {}).get("name"),
            "quoteToken_symbol": pair.get("quoteToken", {}).get("symbol")
        }
        writer.writerow(row)

print(f"Data saved to {csv_file}")
