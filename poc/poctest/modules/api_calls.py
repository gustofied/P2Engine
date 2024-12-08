import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def make_api_call(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API call failed: {e}")
        return {"error": str(e)}

def get_account_info(address):
    url = f"https://api.xrpscan.com/api/v1/account/{address}"
    return make_api_call(url)

def get_orders(address):
    url = f"https://api.xrpscan.com/api/v1/account/{address}/orders"
    return make_api_call(url)

def get_nfts(address):
    url = f"https://api.xrpscan.com/api/v1/account/{address}/nfts"
    return make_api_call(url)
