#!/usr/bin/env python3
import requests

# Test the specific failing endpoint
BASE_URL = "https://quick-kirana-6.preview.emergentagent.com/api"
order_id = "697255b92b4abef7bd38a52b"

print("Testing order status update endpoint...")

try:
    # Test with requests library
    response = requests.put(f"{BASE_URL}/admin/orders/{order_id}/status?status=accepted")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Headers: {response.headers}")
    
    if response.status_code != 200:
        print("Error details:")
        print(f"Reason: {response.reason}")
        
except Exception as e:
    print(f"Exception: {str(e)}")