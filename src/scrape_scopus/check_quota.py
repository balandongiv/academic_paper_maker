import requests
# Convert Epoch time to a readable format
from datetime import datetime
# Replace with your API endpoint
url = "https://api.elsevier.com"

# Replace with your API key if required
headers = {
    "Authorization": "Bearer 3f20dcce9b2e4bbb6b0356cffcf7741d"
}

response = requests.get(url, headers=headers)

# Extract quota details from response headers
quota_limit = response.headers.get("X-RateLimit-Limit")
quota_remaining = response.headers.get("X-RateLimit-Remaining")
quota_reset = response.headers.get("X-RateLimit-Reset")


if quota_reset:
    reset_time = datetime.utcfromtimestamp(int(quota_reset)).strftime('%Y-%m-%d %H:%M:%S UTC')
else:
    reset_time = "Unknown"

# Print quota details
print(f"API Quota Limit: {quota_limit}")
print(f"API Quota Remaining: {quota_remaining}")
print(f"API Quota Resets At: {reset_time}")
