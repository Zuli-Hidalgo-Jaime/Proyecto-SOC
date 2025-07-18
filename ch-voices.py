# check_voices.py
from dotenv import load_dotenv
load_dotenv()

import os, httpx

API_URL = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

headers = {"xi-api-key": API_KEY}
resp = httpx.get(f"{API_URL}/v1/voices", headers=headers, timeout=10)

print("Status code:", resp.status_code)
print("Body:", resp.text)
